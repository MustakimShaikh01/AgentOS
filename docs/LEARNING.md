# 📚 AgentOS Learning Curriculum

> **Every concept you learn here maps directly to code you've already written.**
> This is not a list of YouTube videos. This is a structured path from zero to senior.

---

## How to Use This Guide

1. Study the concept (links provided)
2. Find it in your own code (file links provided)
3. Modify it to prove you understand it
4. Move to the next topic

**Rule:** Don't move to the next topic until you can explain the current one out loud in plain English.

---

## 🗺️ The Full Learning Map

```
FOUNDATION LAYER
    ↓
Python Async → FastAPI → SQLAlchemy → PostgreSQL → Redis → JWT

AI LAYER
    ↓
LLMs → Prompt Engineering → LangGraph → ReAct → Tool Calling → Memory → RAG

SYSTEM DESIGN LAYER
    ↓
API Design → Auth Patterns → Streaming → Caching → Microservices → Kafka → Kubernetes

PLATFORM LAYER
    ↓
Plugin Systems → SDK Design → CLI Tools → Observability → Evaluation
```

---

---

# 🟢 FOUNDATION — Week 1–2

---

## F1. Python Async/Await

**Why it matters:**  
Every LLM call takes 1–30 seconds. Async lets you handle 1000 users without 1000 threads.

**Concepts to understand:**
- `async def` vs `def`
- `await` — what it actually does (suspends, doesn't block)
- `asyncio` event loop
- `async for` — async generators (used in SSE streaming)
- `asyncio.gather()` — run multiple things concurrently

**In your code:**
```python
# api/app/modules/chat/router.py
async def event_generator():          ← async generator
    async for chunk in llm.stream():  ← async for
        yield f"data: {chunk}\n\n"

# api/app/db/base.py
async def get_db() -> AsyncSession:   ← async dependency
    async with AsyncSessionFactory() as session:
        yield session
```

**Learn:**
- [Python asyncio docs](https://docs.python.org/3/library/asyncio.html)
- Practice: write a function that fetches 5 URLs concurrently with `asyncio.gather()`

**Prove you understand it:**  
Explain why `await llm.chat(messages)` doesn't freeze the server when it takes 10 seconds.

---

## F2. FastAPI Deep Dive

**Why it matters:**  
FastAPI is the entire API layer. Understanding it means understanding how every request flows.

**Concepts to understand:**
- Route decorators (`@router.post`, `@router.get`)
- Dependency Injection (`Depends()`) — how `get_db`, `get_current_user` work
- Pydantic models for request/response validation
- Path params, query params, body
- Response models + status codes
- Middleware
- Lifespan context manager (startup/shutdown)
- StreamingResponse + SSE

**In your code:**
```python
# api/app/modules/auth/router.py
@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    request: RegisterRequest,       ← Pydantic validates this
    db: AsyncSession = Depends(get_db),  ← injected dependency
):
```

**Learn:**
- [FastAPI official docs](https://fastapi.tiangolo.com/) — read all of it, it's short
- [FastAPI dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/)

**Prove you understand it:**  
Add a new endpoint `GET /api/auth/me` that returns the current user's info.

---

## F3. SQLAlchemy Async + PostgreSQL

**Why it matters:**  
All persistent data (users, conversations, agent runs) lives in PostgreSQL via SQLAlchemy.

**Concepts to understand:**
- ORM vs raw SQL — what SQLAlchemy abstracts
- `DeclarativeBase` + `Mapped` + `mapped_column` — modern SQLAlchemy 2.x style
- Relationships: `relationship()`, `ForeignKey`, lazy vs eager loading
- Async sessions: `AsyncSession`, `async with`
- Query patterns: `select()`, `where()`, `scalars()`, `execute()`
- Transactions: `db.flush()`, `db.commit()`, `db.rollback()`
- Alembic: versioned schema migrations

**In your code:**
```python
# api/app/db/models.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    organization: Mapped["Organization"] = relationship(...)

# api/app/modules/auth/service.py
user = await db.scalar(select(User).where(User.email == email))
db.add(new_user)
await db.flush()  # write to DB, but don't commit yet
```

**Learn:**
- [SQLAlchemy 2.0 ORM docs](https://docs.sqlalchemy.org/en/20/orm/)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

**Prove you understand it:**  
Write an Alembic migration that adds a `bio` column to the `users` table.

---

## F4. Redis — Caching & Ephemeral Storage

**Why it matters:**  
Redis is used for 4 critical things: JWT blacklist, rate limiting, short-term agent memory, LLM response cache.

**Concepts to understand:**
- Redis data structures: Strings, Hashes, Lists, Sets, Sorted Sets
- `SET` with TTL (time-to-live) — key expires automatically
- `EXISTS`, `GET`, `SETEX`
- Redis as a cache vs Redis as a database
- Connection pools
- Async Redis (`redis.asyncio`)

**In your code:**
```python
# api/app/modules/auth/service.py
# JWT blacklist: token expires in exactly as long as the JWT would
await redis.setex(f"jwt:blacklist:{jti}", ttl_seconds, "1")

# Check if token is blacklisted
exists = await redis.exists(f"jwt:blacklist:{jti}")
```

**Learn:**
- [Redis data types](https://redis.io/docs/data-types/)
- [redis-py async docs](https://redis-py.readthedocs.io/en/stable/connections.html#async-client)

**Prove you understand it:**  
Implement rate limiting: max 10 chat requests per user per minute using Redis.

---

## F5. JWT Authentication — Deep Understanding

**Why it matters:**  
JWTs are the auth backbone. Understanding them prevents security bugs.

**Concepts to understand:**
- JWT structure: Header.Payload.Signature
- What's in the payload (claims): `sub`, `exp`, `iat`, `jti`, custom claims
- Why `jti` exists (JWT ID for blacklisting)
- Access token vs Refresh token — why two tokens?
- HMAC-SHA256 signing — why the signature can't be faked
- Token blacklisting pattern with Redis
- Why you hash refresh tokens before storing them (SHA-256)

**In your code:**
```python
# api/app/modules/auth/jwt.py
payload = {
    "sub": user_id,           ← who this token belongs to
    "org": org_id,            ← which organization
    "role": role,             ← what they can do
    "jti": str(uuid.uuid4()), ← unique ID for blacklisting
    "exp": now + timedelta(minutes=15),  ← expires in 15 min
}

# api/app/modules/auth/service.py
token_hash = hash_token(refresh_token_value)  ← never store plaintext
```

**System Design Concept:**  
Why 15 minutes for access token? If stolen, it expires soon.  
Why store refresh token hashed? If DB is breached, attacker can't use the tokens.

**Learn:**
- [JWT.io — visual debugger](https://jwt.io/)
- [OWASP JWT Security](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)

**Prove you understand it:**  
Decode a JWT manually without a library using base64.

---

---

# 🟡 AI LAYER — Week 3–6

---

## A1. How LLMs Actually Work

**Why it matters:**  
You can't build on something you don't understand. Most people use LLMs as a black box.

**Concepts to understand:**
- Transformer architecture (high level) — attention is all you need
- Tokens: what they are, why they matter for cost
- Context window: what goes in, what the LLM "sees"
- Temperature, top-p: how randomness is controlled
- System prompts vs user prompts
- Instruction-tuned vs base models
- Why LLMs hallucinate (they predict tokens, not truth)

**Key numbers to know:**
| Model | Context | Cost per 1M tokens |
|---|---|---|
| Gemini 1.5 Flash | 1M tokens | ~$0.075 |
| GPT-4o | 128K tokens | ~$5 |
| Claude 3.5 Sonnet | 200K tokens | ~$3 |
| Llama 3 8B (local) | 8K tokens | $0 |

**Learn:**
- [3Blue1Brown: Transformers explained visually](https://youtu.be/wjZofJX0v4M)
- [Andrej Karpathy: Let's build GPT](https://youtu.be/kCc8FmEb1nY)
- [Token counter tool](https://platform.openai.com/tokenizer)

---

## A2. Prompt Engineering

**Why it matters:**  
The quality of agent output is 80% prompt quality.

**Concepts to understand:**
- System prompts — set the agent's role and constraints
- Few-shot examples — show the model what good output looks like
- Chain-of-Thought (CoT) — "think step by step"
- Output format control — "respond only as JSON"
- Prompt injection — how attackers break your agent
- Role-playing prompts — persona assignment

**In your code:**
```python
# core/workflow-engine/engine.py
system_prompt = """You are a strategic planner. Given a user's goal,
create a clear, concise plan. Think step by step about what information
or actions are needed to achieve this goal. Be specific."""
```

**Practice:**  
Write 5 different system prompts for the planner node. Measure which gives better output.

**Learn:**
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)

---

## A3. LangGraph — The Core Framework

**Why it matters:**  
LangGraph is the engine of AgentOS. Every agent run goes through it.

**Concepts to understand in order:**

### Level 1: Basic Graph
```python
graph = StateGraph(MyState)
graph.add_node("node_a", function_a)
graph.add_node("node_b", function_b)
graph.add_edge("node_a", "node_b")
graph.set_entry_point("node_a")
compiled = graph.compile()
```

### Level 2: State
- State is a `TypedDict` — typed, explicit
- Nodes receive the FULL state and return PARTIAL updates
- `Annotated[list, operator.add]` — list fields accumulate instead of overwrite

### Level 3: Conditional Routing
```python
graph.add_conditional_edges(
    "researcher",
    routing_function,      ← returns a string key
    {"reflect": "reflector", "done": END}
)
```

### Level 4: Streaming
```python
async for event in graph.astream_events(state, config, version="v1"):
    event_type = event["event"]  # on_chat_model_stream, on_chain_end, etc.
```

### Level 5: Checkpointing
- `MemorySaver()` — in-memory (Stage 1)
- `AsyncPostgresCheckpointer` — persistent (Stage 3+)
- Thread ID: `config = {"configurable": {"thread_id": "run-123"}}`
- Resume: run the same graph with the same thread_id

**In your code:**
```
core/workflow-engine/engine.py   ← Full LangGraph implementation
core/workflow-engine/state.py    ← AgentState TypedDict
```

**Learn:**
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [LangGraph tutorial: ReAct from scratch](https://langchain-ai.github.io/langgraph/tutorials/introduction/)

**Prove you understand it:**  
Add a 4th node called `summarizer` that runs after `reflector` and condenses the final answer.

---

## A4. ReAct Pattern — Reason + Act

**Why it matters:**  
ReAct is the algorithm behind almost every AI agent. It's how agents decide what to do.

**The loop:**
```
[THOUGHT]  → What do I know? What do I need?
[ACTION]   → Call a tool
[OBSERVATION] → What did the tool return?
[THOUGHT]  → What does this mean? Is it enough?
[ACTION]   → Call another tool or...
[FINAL]    → I have enough information to answer
```

**Key insight:**  
The LLM doesn't "call tools" — it *generates text* that looks like a tool call. Your code parses that text and executes the real function. The observation is fed back into the next LLM call.

**In your code:**
```python
# core/workflow-engine/engine.py — _researcher_node
if "ACTION:" in content:
    # Parse LLM output as a tool call
    tool_name = ...
    tool_input = ...
    observation = await self.tool_registry.execute(tool_name, tool_input)
    # Observation goes back into the state, next iteration reads it
```

**Learn:**
- [ReAct paper (original)](https://arxiv.org/abs/2210.03629)
- [LangChain ReAct agent](https://python.langchain.com/docs/modules/agents/agent_types/react)

---

## A5. Tool Calling / Function Calling

**Why it matters:**  
Tools turn LLMs from text generators into agents that can take real actions.

**Concepts to understand:**
- Tool registry pattern — central catalogue, no hardcoding
- Tool schema — name, description, input type
- JSON parsing of tool calls — why this is fragile
- Modern function calling (OpenAI-style) vs ReAct text parsing
- Tool errors and recovery — what happens when a tool fails
- Sandboxing — why you don't let agents run arbitrary code

**In your code:**
```python
# core/tool-runtime/registry.py
class ToolRegistry:
    def register(self, name, description):
        def decorator(fn):
            self._tools[name] = Tool(name, description, fn)
            return fn
        return decorator

    async def execute(self, tool_name, tool_input):
        tool = self._tools.get(tool_name)
        result = await tool.fn(**tool_input)
        return str(result)

# Usage
@registry.register("web_search", "Search the web. Input: {'query': str}")
async def web_search(query: str) -> str:
    ...
```

**Prove you understand it:**  
Register a new tool `get_current_time` and make the agent use it when asked "What time is it?".

---

## A6. Memory Systems

**Why it matters:**  
Without memory, every conversation starts from zero. Memory is what makes agents feel intelligent.

**The 4 memory types:**

| Type | Storage | Lifespan | Use case |
|---|---|---|---|
| Working memory | In LangGraph state | One run | Current task context |
| Short-term | Redis (TTL) | 30 min | Current session |
| Long-term | PostgreSQL | Forever | Conversation history |
| Semantic | pgvector | Forever | "What did we discuss about X?" |

**In your code (Stage 1):**
```python
# core/workflow-engine/state.py
thoughts: Annotated[list[str], operator.add]   ← working memory
observations: Annotated[list[str], operator.add] ← working memory

# api/app/modules/chat/router.py
history = result.scalars().all()               ← long-term (PostgreSQL)
messages = [{"role": m.role, "content": m.content} for m in history]
# This becomes the conversation_history in the agent state
```

**Coming in Capability 2:**
```python
# core/memory/semantic.py
embedding = embed(user_query)
similar_memories = vector_search(embedding, top_k=5)
```

---

## A7. RAG — Retrieval-Augmented Generation

**Why it matters:**  
LLMs have a knowledge cutoff and hallucinate. RAG grounds them in real data.

**The pipeline:**
```
1. Ingest: PDF/DOCX → text chunks → embeddings → store in vector DB
2. Retrieve: user query → embed query → cosine similarity → top-k chunks
3. Generate: chunks + query → LLM prompt → grounded answer
```

**Key concepts:**
- **Chunking strategy** — fixed size (512 tokens) vs sentence-aware vs semantic
- **Embedding models** — text → vector (OpenAI ada-002, Gemini text-embedding, nomic-embed)
- **Vector similarity** — cosine similarity, dot product
- **Hybrid search** — vector search + BM25 keyword search (better together)
- **Reranking** — cross-encoder rerank the top-k results for quality

**This is Capability 2 in the roadmap.**

**Learn:**
- [RAG from scratch (LangChain)](https://github.com/langchain-ai/rag-from-scratch)
- [pgvector docs](https://github.com/pgvector/pgvector)

---

---

# 🔵 SYSTEM DESIGN LAYER — Week 7–12

---

## S1. API Design Principles

**Concepts:**
- REST vs RPC — when to use each
- Resource naming (`/users`, `/conversations`, `/agent/runs`)
- HTTP verbs — GET/POST/PUT/PATCH/DELETE and when to use each
- Status codes — 200, 201, 400, 401, 403, 404, 409, 422, 500
- Idempotency — why `PUT` is idempotent but `POST` is not
- Versioning — `/api/v1/` in the URL vs `Accept-Version` header
- Rate limiting headers — `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- RFC 9457 Problem Detail — standard error response format

**In your code:**
```python
# api/app/modules/auth/router.py
@router.post("/register", response_model=AuthResponse, status_code=201)
#                                                              ↑ 201 Created, not 200
raise HTTPException(status_code=409, detail="Email already registered")
#                             ↑ 409 Conflict, not 400 Bad Request
```

**Practice:**  
Design the full API for Capability 2 (memory endpoints) before writing any code.

---

## S2. Streaming — SSE vs WebSockets

**Why it matters:**  
LLM responses take 10–30 seconds. Streaming makes it feel instant.

**SSE (Server-Sent Events) — what you use:**
```
Client ──── HTTP GET ────▶ Server
       ◀─── text/event-stream ─────
       ◀─── data: {"delta":"Hello"} ──
       ◀─── data: {"delta":" World"} ─
       ◀─── data: {"done":true} ──────
```

**WebSockets — for bidirectional:**
```
Client ◀──── ws:// ────▶ Server
       ↕ messages in both directions
```

**When to use which:**
- SSE: one-way server push (chat responses, agent progress) ✅
- WebSockets: two-way real-time (multiplayer, live collaboration)

**In your code:**
```python
# api/app/modules/chat/router.py
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
)

async def event_generator():
    async for chunk in llm.stream(messages):
        yield f"data: {json.dumps({'delta': chunk})}\n\n"
```

---

## S3. Caching Strategies

**Concepts:**
- Cache-aside (lazy loading) — check cache, miss → load from DB, store in cache
- Write-through — write to cache AND DB simultaneously
- TTL — when should the cache expire?
- Cache invalidation — the hardest problem in CS
- Semantic caching — cache LLM responses by meaning, not exact text

**In your code (Stage 1):**
```python
# Redis as JWT blacklist — a cache of REVOKED tokens
await redis.setex(f"jwt:blacklist:{jti}", ttl, "1")
```

**Coming in Stage 5:**
```python
# LLM response caching
cache_key = hash(prompt)
cached = await redis.get(f"llm:cache:{cache_key}")
if cached:
    return cached
response = await llm.chat(prompt)
await redis.setex(f"llm:cache:{cache_key}", 3600, response)
```

---

## S4. Event-Driven Architecture + Kafka

**Why:** This is Capability 6. You'll feel the need for it by then.

**Concepts to understand now (theory):**
- Producer → Topic → Consumer
- Consumer groups — multiple instances of the same service
- Offset — where a consumer is in the topic
- Partitions — parallelism
- At-least-once delivery — may get duplicate messages (design for idempotency)
- Dead letter queue — failed messages go here

**Why you're NOT using it yet:**  
You haven't felt the pain. When you have 100 concurrent agent runs blocking the API, you'll understand exactly why Kafka is needed.

**Learn:**
- [Kafka in 100 seconds (Fireship)](https://youtu.be/uvb00oaa3k8)
- [Confluent Kafka fundamentals](https://developer.confluent.io/courses/kafka-fundamentals/intro/)

---

## S5. Microservices vs Monolith — The Real Trade-off

**The question isn't "which is better?" It's "when does each make sense?"**

| Factor | Monolith | Microservices |
|---|---|---|
| Team size | 1–5 | 10+ |
| Deploy frequency | Monthly | Multiple times/day per service |
| Domain clarity | Still learning | Well understood |
| Operational maturity | Low | High |
| Complexity | Low | High |

**The evolution you will go through:**
```
Stage 1: Monolith — learn the domain
Stage 2: Modular monolith — clean boundaries
Stage 3: Extract ONE service — learn the coordination cost
Stage 4: Add Kafka — learn async messaging
Stage 5: Full distributed — because you now understand why
```

**The trap:** Most developers skip to Stage 5 because it looks impressive. You're starting at Stage 1 because you're building an understanding, not a resume line.

---

## S6. Database Design Patterns

**Concepts:**
- Primary keys: UUID vs auto-increment (and why UUID for distributed systems)
- Indexes: when to add one, when not to
- Foreign keys and cascade deletes
- Soft deletes (`is_deleted` column vs actual DELETE)
- Timestamps: always store in UTC with timezone
- Database migrations: never edit, always append (Alembic)
- Connection pooling (PgBouncer)
- N+1 query problem and how to avoid it

**In your code:**
```sql
-- V1__init.sql (Alembic migration — to be created)
CREATE INDEX idx_users_email ON users(email);
-- ↑ Without this, every login scans the entire users table

-- UUID primary keys
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
-- ↑ Safe to use across distributed systems, not guessable
```

---

## S7. System Design Concepts — The Complete List

These map directly to what you'll implement in Capabilities 3–6:

| Concept | When You Learn It | Applies To |
|---|---|---|
| API Gateway | Capability 1 (now) | All external requests |
| Rate Limiting | Capability 1 | Redis counters |
| JWT Blacklist | Capability 1 | Redis + TTL |
| SSE Streaming | Capability 1 | Chat + Agent runs |
| Circuit Breaker | Capability 5 | LLM calls |
| Retry + Backoff | Capability 5 | Transient failures |
| CQRS | Capability 6 | Agent run history |
| Saga Pattern | Capability 6 | Distributed transactions |
| Idempotency | Capability 6 | Kafka consumers |
| Event Sourcing | Capability 6 | Audit log |
| Horizontal Scaling | Capability 6 | Kubernetes HPA |
| Distributed Tracing | Capability 6 | Jaeger + correlation IDs |

---

---

# 🟣 PLATFORM LAYER — Week 13–18

---

## P1. Plugin System Design

**Goal:** Anyone can add a new agent or tool without touching core code.

**Pattern:**
```python
# Anyone can write:
from agentos.core import AgentBase

class MyCustomAgent(AgentBase):
    name = "my-agent"

    async def execute(self, state):
        ...
        return {"thoughts": ["I found the answer"]}

# And register it:
registry.register_agent(MyCustomAgent)
```

**Concepts:**
- Abstract base classes
- Dynamic loading (importlib)
- Discovery patterns (scan packages for subclasses)

---

## P2. SDK Design

**Goal:** `pip install agentos` → developers build on your platform.

**Principles:**
- Simple common case, complex cases possible
- Errors should be helpful, not cryptic
- Typed — use Python type hints throughout
- Async-first

```python
from agentos import Workflow, Agent

w = Workflow()
w.add(Agent.research())
w.add(Agent.reviewer())
result = await w.run("Summarize quantum computing in 2025")
print(result.final_answer)
```

---

## P3. Observability

**The 3 pillars:**

| Pillar | Tool | What |
|---|---|---|
| Logs | structlog → JSON | Every event with context |
| Metrics | Prometheus + Grafana | Counts, rates, latencies |
| Traces | OpenTelemetry | Full request path across services |

**Correlation ID pattern:**
```python
# Every request gets a unique ID
# Every log line includes it
# Every downstream call propagates it
# When something fails, grep logs by correlation_id
```

**In your code:**
```python
# api/app/main.py
import structlog
log = structlog.get_logger()
log.info("AgentOS API starting", version=settings.version)
```

---

---

# 📅 Suggested Weekly Schedule

| Week | Focus | Code Work |
|---|---|---|
| 1 | Python async, FastAPI, PostgreSQL basics | Get `docker-compose up` working, test auth endpoints |
| 2 | JWT deep dive, Redis, Alembic migrations | Write migration, test full auth flow |
| 3 | LLMs, tokens, prompts, LiteLLM | Get streaming chat working end-to-end |
| 4 | LangGraph basics, StateGraph, streaming | Run your first LangGraph agent |
| 5 | ReAct pattern, tool calling | Add a real web search tool (Serper API) |
| 6 | Memory systems, conversation context | Make agents remember past sessions |
| 7 | API design, REST principles | Design Capability 2 API |
| 8 | RAG pipeline, embeddings, pgvector | Ingest a PDF, retrieve relevant chunks |
| 9 | System design: caching, streaming, auth | Review all your code through this lens |
| 10 | Workflow engine, DAGs, state machines | Build a real research workflow |
| 11 | Tool integrations (GitHub API) | Connect to a real external service |
| 12 | Evaluation: LLM-as-judge, metrics | Score your agent's output quality |
| 13–18 | Kafka, Kubernetes, production deployment | Capability 6 |

---

# 🔑 Key Questions to Ask Yourself

After each week, answer these:

1. What concept did I learn this week?
2. Where exactly in the codebase does it appear?
3. What would break if I removed it?
4. Can I explain it in one paragraph to someone who's never heard of it?
5. What's the trade-off? (Every design decision has one)

---

# 📖 Essential Reading List

| Book/Resource | What You Learn | When |
|---|---|---|
| [FastAPI docs](https://fastapi.tiangolo.com/) | Everything about FastAPI | Week 1 |
| [SQLAlchemy 2.0 ORM docs](https://docs.sqlalchemy.org/en/20/orm/) | Modern SQLAlchemy | Week 1 |
| [LangGraph docs](https://langchain-ai.github.io/langgraph/) | Agent orchestration | Week 3 |
| [Designing Data-Intensive Applications](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/) | Distributed systems bible | Month 2+ |
| [System Design Interview Vol 1 & 2](https://www.amazon.com/System-Design-Interview-insiders-Second/dp/B08CMF2CQF) | System design patterns | Month 2+ |
| [ReAct paper](https://arxiv.org/abs/2210.03629) | Original ReAct algorithm | Week 4 |
| [Attention is All You Need](https://arxiv.org/abs/1706.03762) | How transformers work | Week 3 |

---

> **"The goal isn't to learn everything at once. The goal is to always know what you're building and why."**
