"""
core/workflow-engine/engine.py

The core ReAct agent graph built with LangGraph.

Architecture:
    This engine is the platform primitive. It defines the graph structure.
    Specific agents (planner, research, reviewer) are nodes in this graph.
    The graph is generic — what changes per use case is the node implementations.

ReAct Loop:
    planner → researcher → reflector → [loop | done]

Streaming:
    The engine yields events as they happen via astream_events().
    The API layer converts these to SSE for the frontend.
"""

import json
from typing import AsyncGenerator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.workflow_engine.state import AgentState
from core.model_router.router import get_llm_client
from core.tool_runtime.registry import ToolRegistry


class AgentEngine:
    """
    Builds and executes the ReAct agent graph.

    Usage:
        engine = AgentEngine(tool_registry)
        async for event in engine.stream(state):
            yield event
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("planner", self._planner_node)
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("reflector", self._reflector_node)

        # Entry point
        graph.set_entry_point("planner")

        # Edges
        graph.add_edge("planner", "researcher")
        graph.add_conditional_edges(
            "researcher",
            self._should_continue,
            {
                "reflect": "reflector",
                "done": END,
            }
        )
        graph.add_conditional_edges(
            "reflector",
            self._after_reflection,
            {
                "continue": "researcher",
                "done": END,
            }
        )

        return graph.compile(checkpointer=MemorySaver())

    # ── Nodes ──────────────────────────────────────────────────────────────────

    async def _planner_node(self, state: AgentState) -> dict:
        """
        THOUGHT step: Decompose the goal into a plan.
        The planner decides what needs to be done and in what order.
        """
        llm = get_llm_client(state["model"])

        system_prompt = """You are a strategic planner. Given a user's goal,
        create a clear, concise plan. Think step by step about what information
        or actions are needed to achieve this goal. Be specific."""

        messages = [
            {"role": "system", "content": system_prompt},
            *state.get("conversation_history", []),
            {"role": "user", "content": f"Goal: {state['goal']}\n\nCreate a plan to achieve this goal."},
        ]

        response = await llm.chat(messages)
        thought = response["content"]

        return {
            "thoughts": [thought],
            "iteration": state.get("iteration", 0) + 1,
        }

    async def _researcher_node(self, state: AgentState) -> dict:
        """
        ACTION + OBSERVATION step: Execute the plan.
        Calls tools when needed, collects observations.
        """
        llm = get_llm_client(state["model"])

        thoughts_so_far = "\n".join(state.get("thoughts", []))
        observations_so_far = "\n".join(state.get("observations", []))

        available_tools = self.tool_registry.get_tool_descriptions()

        system_prompt = f"""You are a research agent. Based on the plan below,
        take the next action. You have access to these tools:

        {json.dumps(available_tools, indent=2)}

        If you have enough information to answer, output:
        FINAL ANSWER: <your complete answer>

        If you need to use a tool, output:
        ACTION: <tool_name>
        INPUT: <tool input as JSON>"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Goal: {state['goal']}

Plan:
{thoughts_so_far}

Previous observations:
{observations_so_far}

What is your next action?"""},
        ]

        response = await llm.chat(messages)
        content = response["content"]

        # Parse response
        if "FINAL ANSWER:" in content:
            final = content.split("FINAL ANSWER:", 1)[1].strip()
            return {
                "final_answer": final,
                "is_done": True,
                "observations": [f"Final answer generated"],
            }

        if "ACTION:" in content:
            lines = content.strip().split("\n")
            action_line = next((l for l in lines if l.startswith("ACTION:")), "")
            input_line = next((l for l in lines if l.startswith("INPUT:")), "INPUT: {}")

            tool_name = action_line.replace("ACTION:", "").strip()
            tool_input_str = input_line.replace("INPUT:", "").strip()

            try:
                tool_input = json.loads(tool_input_str)
            except json.JSONDecodeError:
                tool_input = {"query": tool_input_str}

            # Execute tool
            observation = await self.tool_registry.execute(tool_name, tool_input)

            return {
                "actions": [{"tool": tool_name, "input": tool_input}],
                "observations": [observation],
                "is_done": False,
            }

        # No clear action — treat content as observation and continue
        return {
            "observations": [content],
            "is_done": False,
        }

    async def _reflector_node(self, state: AgentState) -> dict:
        """
        REFLECTION step: Verify the answer quality.
        Self-critique before finalizing.
        """
        llm = get_llm_client(state["model"])

        system_prompt = """You are a critical reviewer. Review the research progress
        and determine if the answer is complete, accurate, and addresses the original goal.

        Respond with one of:
        SATISFIED: <brief reason why the answer is complete>
        NEEDS_MORE: <specific gap or issue that needs to be addressed>"""

        latest_observation = state["observations"][-1] if state.get("observations") else ""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Goal: {state['goal']}
Latest finding: {latest_observation}
Is this sufficient to answer the goal completely?"""},
        ]

        response = await llm.chat(messages)
        content = response["content"]

        if "SATISFIED:" in content:
            return {"is_done": True, "should_reflect": False}
        else:
            return {"is_done": False, "should_reflect": False}

    # ── Routing ────────────────────────────────────────────────────────────────

    def _should_continue(self, state: AgentState) -> str:
        if state.get("is_done"):
            return "done"
        if state.get("iteration", 0) >= state.get("max_iterations", 5):
            return "done"
        return "reflect"

    def _after_reflection(self, state: AgentState) -> str:
        if state.get("is_done"):
            return "done"
        return "continue"

    # ── Execution ──────────────────────────────────────────────────────────────

    async def stream(self, state: AgentState) -> AsyncGenerator[dict, None]:
        """
        Stream agent execution events.
        Yields dicts with 'type' and 'data' fields.
        """
        config = {"configurable": {"thread_id": state["run_id"]}}

        async for event in self.graph.astream_events(state, config=config, version="v1"):
            event_type = event.get("event")

            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield {"type": "token", "data": chunk.content}

            elif event_type == "on_chain_end" and event.get("name") in ("planner", "researcher", "reflector"):
                yield {
                    "type": "step",
                    "data": {
                        "node": event["name"],
                        "output": event["data"].get("output", {}),
                    }
                }

        # Final state
        final_state = await self.graph.aget_state(config)
        if final_state and final_state.values:
            yield {
                "type": "done",
                "data": {
                    "final_answer": final_state.values.get("final_answer", ""),
                    "iterations": final_state.values.get("iteration", 0),
                }
            }
