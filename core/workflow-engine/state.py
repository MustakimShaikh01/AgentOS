"""
core/workflow-engine/state.py

Defines the shared state schema that flows through every LangGraph graph.

Design Note:
    State is a TypedDict. Every node receives the full state and returns
    a partial update. LangGraph merges updates automatically.
    Keeping state explicit and typed makes it easy to debug, checkpoint,
    and serialize to PostgreSQL.
"""

from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    """
    The state that flows through the ReAct agent graph.

    Fields are merged by LangGraph after each node:
    - Scalar fields: last writer wins
    - List fields with Annotated[list, operator.add]: accumulate (append)
    """

    # Input
    goal: str                                          # The user's original request
    conversation_history: list[dict]                  # Prior messages for context

    # ReAct loop fields
    thoughts: Annotated[list[str], operator.add]      # Accumulated THOUGHT steps
    actions: Annotated[list[dict], operator.add]      # Accumulated ACTION steps
    observations: Annotated[list[str], operator.add]  # Accumulated OBSERVATION steps

    # Control
    iteration: int                                     # Current loop count
    max_iterations: int                                # Safety limit
    should_reflect: bool                               # Trigger reflection step
    is_done: bool                                      # Signal termination

    # Output
    final_answer: str                                  # Completed answer
    error: str | None                                  # If something failed

    # Metadata
    run_id: str                                        # AgentRun.id for tracing
    user_id: str                                       # User who triggered this
    model: str                                         # LLM model to use
