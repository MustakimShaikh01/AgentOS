"""
modules/chat/router.py — Capability 1

Handles conversations and streaming chat responses.
Chat is the primary user-facing interface.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Conversation, Message, User
from app.dependencies import get_current_user
from core.model_router.router import get_llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    title: str | None = None
    model: str = "gemini-pro"


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    model: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str | None
    model: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tokens_used: int | None
    created_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new conversation."""
    conv = Conversation(
        user_id=current_user.id,
        title=request.title,
        model=request.model,
    )
    db.add(conv)
    await db.flush()
    return ConversationOut(
        id=str(conv.id),
        title=conv.title,
        model=conv.model,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        ConversationOut(
            id=str(c.id), title=c.title, model=c.model,
            created_at=c.created_at, updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    conv = await db.get(Conversation, uuid.UUID(conversation_id))
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    msgs = result.scalars().all()
    return [
        MessageOut(
            id=str(m.id), role=m.role, content=m.content,
            tokens_used=m.tokens_used, created_at=m.created_at,
        )
        for m in msgs
    ]


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and receive a streaming LLM response.
    Returns: Server-Sent Events (SSE) stream.

    System Design Note:
        Streaming is implemented via SSE (Server-Sent Events).
        The frontend receives token-by-token output, giving instant feedback.
        The full response is saved to PostgreSQL only after the stream completes.
    """
    conv = await db.get(Conversation, uuid.UUID(request.conversation_id))
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.flush()

    # Load conversation history for context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()
    messages = [{"role": m.role, "content": m.content} for m in history]

    model = request.model or conv.model
    llm = get_llm_client(model)

    async def event_generator():
        full_response = ""
        total_tokens = 0

        try:
            async for chunk in llm.stream(messages):
                full_response += chunk
                data = json.dumps({"delta": chunk, "done": False})
                yield f"data: {data}\n\n"

            # Save assistant response
            async with db.begin():
                assistant_msg = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=full_response,
                    model=model,
                )
                db.add(assistant_msg)

            yield f"data: {json.dumps({'delta': '', 'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
