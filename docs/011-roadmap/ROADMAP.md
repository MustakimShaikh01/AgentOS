# 011 — Roadmap

## Capability-Driven Development

The roadmap is organized by **capabilities**, not features.  
A capability is a deep concept you must fully understand before the next one makes sense.

```
Capability 1  →  Capability 2  →  Capability 3  →  Capability 4  →  Capability 5  →  Capability 6
Agent Runtime     Memory            Workflow          Tool Runtime      Model Runtime     Distributed
```

---

## Capability 1 — Agent Runtime

**Duration:** 2–3 weeks  
**You are here ← **

### What you learn
- LangGraph StateGraph internals
- ReAct loop: Think → Act → Observe → Reflect
- Streaming agent responses via SSE
- LangGraph checkpointing (pause and resume)
- State schema design (TypedDict)
- How to compose multiple agents into a pipeline

### What you build

```
User → API → Planner Agent → Research Agent → Verifier Agent → Response
```

A three-agent pipeline that:
1. Plans: decomposes the user's goal into subtasks
2. Researches: retrieves information per subtask
3. Verifies: checks the final answer for hallucinations

### Deliverables

- [ ] FastAPI `/agent/run` endpoint (streaming)
- [ ] LangGraph StateGraph with Planner → Research → Verifier
- [ ] `POST /auth/register` and `POST /auth/login` (needed for auth)
- [ ] PostgreSQL: `users`, `conversations`, `messages`, `agent_runs`, `agent_steps`
- [ ] Redis: JWT blacklist, rate limiting
- [ ] Next.js chat UI with real-time streaming
- [ ] `docker-compose up` starts everything

### Stack
```
FastAPI + LangGraph + LiteLLM + PostgreSQL + Redis + Next.js
```

---

## Capability 2 — Memory

**Duration:** 2–3 weeks

### What you learn
- Short-term memory: Redis TTL cache scoped to session
- Long-term memory: PostgreSQL conversation store with retrieval
- Semantic memory: vector embeddings + cosine similarity search
- Memory architecture: when to use each layer
- Retrieval strategies: recency vs relevance vs importance

### What you build

```
Agent ─→ Short-term (Redis TTL)
      ─→ Long-term (PostgreSQL, all history)
      ─→ Semantic  (pgvector, "what did we discuss about X?")
```

Agents that **remember across sessions** and can answer "What did we talk about last week?"

### Deliverables

- [ ] `core/memory/short_term.py` — Redis-backed session memory
- [ ] `core/memory/long_term.py` — PostgreSQL conversation retrieval
- [ ] `core/memory/semantic.py` — pgvector similarity search
- [ ] Enable pgvector extension in PostgreSQL
- [ ] Alembic migration: `embeddings` table
- [ ] Agent uses memory context in every prompt
- [ ] Memory management: summarization + pruning old memories

### New Stack Component
```
pgvector (PostgreSQL extension) — no separate vector DB yet
```

---

## Capability 3 — Workflow Engine

**Duration:** 3 weeks

### What you learn
- DAG (Directed Acyclic Graph) execution
- State machines with conditional routing
- Human-in-the-loop: pause and wait for approval
- LangGraph interrupts and `Command` objects
- Workflow versioning and replay
- Error handling and retry logic at the workflow level

### What you build

```
Workflow Definition (YAML/Code)
    │
    ▼
Workflow Engine (DAG executor)
    │
    ├── Task Node (agent step)
    ├── Decision Node (conditional routing)
    ├── Human Approval Node (interrupt + wait)
    └── Parallel Node (fan-out/fan-in)
```

A drag-and-drop (or code-first) workflow builder where agents and decisions are nodes.

### Deliverables

- [ ] `core/workflow-engine/engine.py` — LangGraph-based DAG executor
- [ ] `core/workflow-engine/state.py` — Workflow state schema
- [ ] `core/workflow-engine/checkpointer.py` — Pause/resume state
- [ ] Human approval: API endpoint + frontend modal
- [ ] Workflow history: every run is recorded with step-by-step trace
- [ ] First real workflow: `workflows/research/` — multi-step research report

---

## Capability 4 — Tool Runtime

**Duration:** 2–3 weeks

### What you learn
- MCP (Model Context Protocol) — the standard for LLM tools
- Tool registry: how tools are discovered and validated
- Permission model: which agent can use which tool
- Sandboxed execution: timeout, error containment
- Tool result parsing and normalization

### What you build

```
Tool Registry
    │
    ├── github_tool.py     ← list PRs, create issues, read files
    ├── gmail_tool.py      ← read/send emails
    ├── slack_tool.py      ← send messages, read channels
    ├── browser_tool.py    ← web search, page scraping
    └── code_exec_tool.py  ← sandboxed Python execution
```

Agents can call real external services through a consistent, safe interface.

### Deliverables

- [ ] `core/tool-runtime/registry.py` — register, discover, validate tools
- [ ] `core/tool-runtime/executor.py` — execute with timeout + error handling
- [ ] `integrations/github/` — GitHub tool implementation
- [ ] `integrations/gmail/` — Gmail tool implementation
- [ ] Tool permission system: org-level and agent-level controls
- [ ] MCP-compatible interface for future extensibility

---

## Capability 5 — Model Runtime

**Duration:** 2 weeks

### What you learn
- LiteLLM: unified interface to all LLM providers
- Cost routing: route by task type to cheapest model that can do it
- Fallback chains: if Model A fails, try Model B
- Context window management: truncation, summarization strategies
- Prompt caching: reduce cost on repeated patterns
- Model benchmarking: latency, quality, cost per task type

### What you build

```
Task comes in
    │
    ▼
Model Router
    ├── task_type == "classify"  → gemini-flash (cheap)
    ├── task_type == "reason"    → gpt-4o (capable)
    ├── task_type == "code"      → claude-sonnet (best for code)
    └── task_type == "sensitive" → llama3-local (never leaves server)
```

### Deliverables

- [ ] `core/model-router/router.py` — LiteLLM wrapper with routing rules
- [ ] `core/model-router/costs.py` — cost table per model per token
- [ ] `core/model-router/fallback.py` — fallback chain with circuit breaker
- [ ] Cost dashboard: daily/weekly spend per model
- [ ] Model benchmark runner: compare models on same tasks
- [ ] Prompt cache layer in Redis

---

## Capability 6 — Distributed Execution

**Duration:** 3–4 weeks  
**This is where Kafka, Kubernetes, and distributed systems come in.**

### What you learn

You will now feel exactly why these things are needed:
- Message queues (Kafka) — agent runs block the API
- Consumer groups — parallel worker pools
- Idempotency — retries without duplicate work
- Distributed tracing — where did the request go?
- Kubernetes HPA — scale workers under load
- CQRS — read/write separation for run history
- Event sourcing — the run history IS the events

### What you build

```
FastAPI API (thin)
    │ kafka.produce("agent.run.requested")
    ▼
Kafka Topic: agent.run.requested
    │
    ▼
Agent Worker Pool (K8s Deployment, HPA)
    │
    ├── kafka.produce("agent.run.completed")
    ├── kafka.produce("agent.step.completed")
    └── kafka.produce("tool.called")
    │
    ▼
Fan-out consumers:
    ├── eval-service   (score the run)
    ├── billing-worker (count tokens)
    └── audit-worker   (immutable log)
```

### Why this order matters

If you had built Kafka on Day 1, you would have spent 2 weeks configuring topics, consumer groups, and serialization — without understanding **what the events mean** or **why they need to be async**.

By Capability 6, you have already built the agents, memory, workflows, and tools. You know exactly which operations are slow, which need to scale, and which need fan-out. Now Kafka is an obvious solution, not a cargo-cult addition.

---

## Milestone Summary

| Capability | Duration | Key Output | System Design Concept |
|---|---|---|---|
| 1: Agent Runtime | 2–3 weeks | Working AI agent + chat UI | ReAct, JWT, SSE Streaming |
| 2: Memory | 2–3 weeks | Persistent cross-session memory | Vector search, caching layers |
| 3: Workflow Engine | 3 weeks | DAG workflows + human approval | State machines, checkpointing |
| 4: Tool Runtime | 2–3 weeks | GitHub + Gmail + Slack tools | MCP, permission model |
| 5: Model Runtime | 2 weeks | Cost-optimized model routing | Circuit breaker, fallback |
| 6: Distributed | 3–4 weeks | Kafka workers + Kubernetes | Event-driven, CQRS, scaling |

**Total: ~15–18 weeks of focused work**
