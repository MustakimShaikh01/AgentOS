# 002 — Architecture

---

## The Three Stages

Architecture is not designed once. It **evolves under pressure**.

```
Stage 1                    Stage 2                    Stage 3
────────────────           ────────────────           ────────────────
Modular Monolith      →    Extracted Workers     →    Event-Driven
                                                       Distributed

Single FastAPI app         API + AI workers           API + Workers + Kafka
Single PostgreSQL          + Workflow engine           + Separate DBs
Single Redis               Clean boundaries            True microservices
LangGraph inline           Module contracts            Scale on evidence
```

---

## Stage 1 Architecture (Now)

### Diagram

```
Browser / Client
       │
       ▼
  Next.js Frontend (port 3000)
       │
       ▼
  FastAPI Backend (port 8000)
  ─────────────────────────────────
  │  modules/auth       │
  │  modules/chat       │
  │  modules/agent      │
  │  modules/workspace  │
  ─────────────────────────────────
  │  core/workflow-engine          │
  │  core/memory                   │
  │  core/model-router             │
  │  core/tool-runtime             │
  ─────────────────────────────────
       │               │
       ▼               ▼
  PostgreSQL         Redis
  (port 5432)        (port 6379)
                         │
                         ▼
                  LiteLLM Proxy (port 4000)
                      │        │       │
                   Gemini    GPT-4o  Ollama
```

### Key Design Decisions

**Single deployable unit (Stage 1)**  
Everything runs as one FastAPI process. Modules communicate via Python function calls, not HTTP. This eliminates the network latency, serialization overhead, and operational complexity of microservices — before you've even validated the product.

**Clean module boundaries (from Day 1)**  
Even though it's a monolith, modules do NOT import each other freely. Each module exposes a public interface. The `agent` module doesn't reach into `auth` internals — it calls `auth.get_current_user()`. This means Stage 2 extraction is just wrapping these boundaries in HTTP.

**LiteLLM from Day 1**  
Even in Stage 1, all LLM calls go through LiteLLM. This means you never hardcode `openai.chat.completions.create()`. When you swap models, nothing in your agent code changes. This is the model-agnostic principle enforced at the infrastructure level.

---

## Module Map

```
api/app/
├── main.py              ← FastAPI app, router registration, lifespan
├── config.py            ← Pydantic settings
├── dependencies.py      ← Shared FastAPI dependencies (get_db, get_current_user)
│
├── db/
│   ├── base.py          ← SQLAlchemy base + session factory
│   └── migrations/      ← Alembic versioned migrations
│
└── modules/
    ├── auth/
    │   ├── router.py    ← POST /auth/register, /login, /refresh, /logout
    │   ├── service.py   ← Business logic
    │   ├── models.py    ← SQLAlchemy: User, Organization, RefreshToken
    │   ├── schemas.py   ← Pydantic: request/response DTOs
    │   └── jwt.py       ← JWT issue + validate
    │
    ├── chat/
    │   ├── router.py    ← POST /chat, GET /conversations
    │   ├── service.py   ← Conversation management, history
    │   └── models.py    ← Conversation, Message
    │
    ├── agent/
    │   ├── router.py    ← POST /agent/run, GET /agent/runs/:id
    │   ├── service.py   ← Invoke agent runtime, track runs
    │   └── models.py    ← AgentRun, AgentStep
    │
    └── workspace/
        ├── router.py    ← Projects, tasks
        └── models.py    ← Project, Task
```

---

## Core Layer Map

```
core/
├── workflow-engine/
│   ├── engine.py         ← LangGraph StateGraph executor
│   ├── state.py          ← Shared workflow state schema
│   └── checkpointer.py   ← PostgreSQL-backed checkpointing
│
├── memory/
│   ├── short_term.py     ← Redis TTL cache (per-conversation)
│   ├── long_term.py      ← PostgreSQL conversation history
│   └── semantic.py       ← Vector search (Phase 2: pgvector)
│
├── tool-runtime/
│   ├── registry.py       ← Tool registration and lookup
│   ├── executor.py       ← Safe tool execution with timeout
│   └── mcp_adapter.py   ← MCP protocol adapter
│
├── model-router/
│   ├── router.py         ← LiteLLM wrapper with routing logic
│   ├── costs.py          ← Token cost table by model
│   └── fallback.py       ← Fallback chain logic
│
└── evaluation/
    ├── scorer.py          ← LLM-as-judge scoring
    └── metrics.py         ← Latency, token usage, success rate
```

---

## Data Layer

### PostgreSQL (Primary Store)

```
users               Organizations and authentication
conversations       Chat history metadata
messages            Individual messages with token counts
agent_runs          Agent execution records
agent_steps         Individual steps within a run (ReAct trace)
workflows           Workflow definitions
workflow_runs       Workflow execution history
projects            Workspace projects
tasks               Tasks within projects
```

### Redis

```
jwt:blacklist:{jti}         Revoked JWT IDs (TTL = token remaining life)
rate:{user_id}:{window}     Rate limiting counters
memory:short:{session_id}   Agent short-term memory (TTL = 30 min)
llm:cache:{prompt_hash}     LLM response cache (TTL = 1 hour)
```

---

## Agent Execution Model (ReAct)

```
User input
    │
    ▼
workflow-engine.execute(state)
    │
    ├─▶ Thought: What do I need to do?
    │
    ├─▶ Action: tool_registry.execute("search", query)
    │              ▲ tool_runtime handles this
    │
    ├─▶ Observation: parse result
    │
    ├─▶ Reflection: is this answer correct? (reflection agent)
    │
    └─▶ [loop or terminate]
            │
            ▼
         Final output + memory.save(state)
```

This loop is a **LangGraph StateGraph**. Each node is a Python function. The state is a TypedDict. LangGraph handles the graph traversal, checkpointing, and streaming.

---

## When to Move to Stage 2

Move when you have **evidence**, not assumption.

| Signal | Stage 2 Split |
|---|---|
| Agent runs slow down the API response | Extract AI workers as separate process |
| Workflow execution is blocking HTTP | Extract workflow engine |
| Memory queries are slow | Upgrade to pgvector + semantic search |
| Multiple teams need to deploy independently | Extract modules to services |

---

## What Stage 3 Adds (Future Reference)

When Stage 2 bottlenecks appear:

```
FastAPI API          ← stays thin, no agent logic
    │
    ▼ (Kafka)
Agent Worker Pool    ← scales independently
    │
    ├── Planner Worker
    ├── Research Worker
    └── Reviewer Worker
    │
    ▼ (Kafka)
Eval Service         ← consumes all run.completed events
Billing Service      ← consumes token usage events
Audit Service        ← fan-in consumer on all topics
```

Kafka appears here because now there is **actual async fan-out** justifying it. Not because the architecture diagram looks impressive.

---

## Principles

| Principle | Implementation |
|---|---|
| Single Responsibility | Each module owns one domain |
| Dependency Inversion | Modules depend on interfaces, not implementations |
| Ports and Adapters | core/ exposes ports, integrations/ are adapters |
| Fail Fast | Validate at the boundary, not deep inside |
| Observable | Every agent step is logged with correlation ID |
| Testable | Business logic has no framework dependencies |
