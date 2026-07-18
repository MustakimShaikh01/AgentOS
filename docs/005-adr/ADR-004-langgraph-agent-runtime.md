# ADR-004: LangGraph as the Agent Runtime

**Date:** 2026-07-18  
**Status:** Accepted

---

## Context

Choosing the agent orchestration framework is the most important architectural decision in this project. The options are: LangGraph, CrewAI, AutoGen, pure Python, or a custom implementation.

---

## Decision

Use **LangGraph** as the primary agent orchestration framework.

---

## Rationale

**1. StateGraph model is the right abstraction**  
LangGraph models agent execution as a directed graph of nodes. Each node is a Python function. The state is a typed schema that flows through the graph. This matches how agent execution actually works: structured state, conditional routing, loops.

**2. First-class checkpointing**  
LangGraph's `MemorySaver` and `AsyncPostgresCheckpointer` allow agent runs to be paused, persisted, and resumed. This is essential for:
- Human-in-the-loop approval gates (Capability 3)
- Long-running workflows that exceed a single HTTP request
- Recovering from failures mid-run

**3. Streaming is built-in**  
`graph.astream_events()` produces a stream of typed events (node start, node end, LLM token, tool call). This powers the chat UI's streaming output without custom implementation.

**4. Production-grade**  
LangGraph is maintained by LangChain Inc., powers LangGraph Cloud, and is used in production by real companies. It is not a research toy.

**5. Composable with the rest of LangChain**  
LangChain's tool interfaces, memory classes, and document loaders integrate directly with LangGraph nodes. We don't reimplement these.

---

## Trade-offs

| Concern | Response |
|---|---|
| LangGraph has a learning curve | Capability 1 is specifically about learning LangGraph internals |
| Vendor lock-in | The business logic (agent prompts, tools, state schema) is pure Python. LangGraph is the executor. Replacing it is possible. |
| CrewAI is simpler to start | CrewAI abstracts too much. You don't learn how agents work; you learn how CrewAI works. |

---

## Alternatives Rejected

**CrewAI**  
Higher-level abstraction that hides the graph structure. Faster to get a demo but harder to customize. Doesn't teach the underlying model.

**AutoGen**  
Microsoft's framework. Different programming model (actor-based). Less mature checkpointing and streaming story.

**Pure Python (custom)**  
Viable for learning, but re-inventing the wheel. LangGraph has solved checkpointing, streaming, and parallel node execution correctly. Using it lets us focus on the domain.
