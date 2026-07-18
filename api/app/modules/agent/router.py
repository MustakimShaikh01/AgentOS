"""
modules/agent/router.py — Capability 1

Agent run endpoints: trigger agent runs and stream results.
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import AgentRun, AgentStep, User
from app.dependencies import get_current_user
from core.workflow_engine.engine import AgentEngine
from core.workflow_engine.state import AgentState
from core.tool_runtime.registry import registry as tool_registry

router = APIRouter(prefix="/agent", tags=["agent"])
engine = AgentEngine(tool_registry=tool_registry)


class RunRequest(BaseModel):
    goal: str
    model: str = "gemini-pro"
    conversation_id: str | None = None
    max_iterations: int = 5


@router.post("/run")
async def run_agent(
    request: RunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an agent run and stream the results via SSE.

    The agent runs a ReAct loop (Plan → Research → Reflect) and streams
    each step and token to the client in real time.
    """
    # Create the run record
    run = AgentRun(
        user_id=current_user.id,
        conversation_id=uuid.UUID(request.conversation_id) if request.conversation_id else None,
        goal=request.goal,
        model=request.model,
        status="RUNNING",
    )
    db.add(run)
    await db.flush()
    run_id = str(run.id)

    initial_state: AgentState = {
        "goal": request.goal,
        "conversation_history": [],
        "thoughts": [],
        "actions": [],
        "observations": [],
        "iteration": 0,
        "max_iterations": request.max_iterations,
        "should_reflect": False,
        "is_done": False,
        "final_answer": "",
        "error": None,
        "run_id": run_id,
        "user_id": str(current_user.id),
        "model": request.model,
    }

    async def event_generator():
        try:
            async for event in engine.stream(initial_state):
                yield f"data: {json.dumps(event)}\n\n"

            # Mark run complete
            async with db.begin():
                run.status = "COMPLETED"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
            async with db.begin():
                run.status = "FAILED"
                run.result = str(e)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs")
async def list_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all agent runs for the current user."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "goal": r.goal,
            "status": r.status,
            "model": r.model,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of an agent run including all steps."""
    run = await db.get(AgentRun, uuid.UUID(run_id))
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Run not found")

    result = await db.execute(
        select(AgentStep)
        .where(AgentStep.run_id == run.id)
        .order_by(AgentStep.created_at)
    )
    steps = result.scalars().all()

    return {
        "id": str(run.id),
        "goal": run.goal,
        "result": run.result,
        "status": run.status,
        "model": run.model,
        "total_tokens": run.total_tokens,
        "created_at": run.created_at.isoformat(),
        "steps": [
            {
                "id": str(s.id),
                "step_type": s.step_type,
                "content": s.content,
                "tool_name": s.tool_name,
                "created_at": s.created_at.isoformat(),
            }
            for s in steps
        ],
    }
