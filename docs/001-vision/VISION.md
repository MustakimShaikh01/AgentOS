# 001 — Vision & Goals

**AgentOS: An Operating System for AI Workflows**

---

## The Core Insight

Most AI projects fail not because the AI is bad, but because the **infrastructure around the AI is bad**.

Prompts are hardcoded.  
Models can't be swapped.  
Memory disappears between sessions.  
Tools require custom integration each time.  
Workflows can't be reused or composed.

AgentOS fixes the infrastructure.

---

## What AgentOS Is

AgentOS is a **platform**, not a product.

A platform provides primitives that other things are built on top of.

```
The Platform              What Gets Built On It
───────────               ──────────────────────
Workflow Engine     →     Research workflow
Memory System       →     Agent memory per user
Tool Runtime        →     GitHub integration
Model Router        →     Cost-aware LLM selection
Evaluation Engine   →     Quality scoring pipeline
```

The platform is generic. The workflows and agents are domain-specific.

---

## Why This Architecture?

### Reference Systems

Every reference system started focused, then expanded:

| System | Started as | Became |
|---|---|---|
| LangGraph | A focused runtime | Full agent framework |
| Dify | Single Flask app | Enterprise AI platform |
| Flowise | Visual workflow builder | Multi-agent system |
| OpenHands | Simple code agent | Full dev environment |

None of them started with 11 microservices.

### The Evolution Rule

```
Understand → Abstract → Distribute
```

1. **Understand:** Build the feature in the simplest possible way.
2. **Abstract:** Extract reusable primitives once patterns emerge.
3. **Distribute:** Split services only when you hit scaling or deployment limits.

---

## Goals

### Engineering Goals

- Build a production-quality modular monolith as Stage 1
- Introduce distribution only when there is a concrete reason
- Document every architectural decision in ADRs
- Maintain clean module boundaries from Day 1
- Write an SDK and CLI once the core is stable

### Learning Goals

**Capability 1 — Agent Runtime**  
LangGraph internals, StateGraph, checkpointing, streaming, state management

**Capability 2 — Memory**  
Redis short-term memory, PostgreSQL conversation store, vector semantic memory

**Capability 3 — Workflow Engine**  
DAG execution, state machines, conditional routing, human-in-the-loop interrupts

**Capability 4 — Tool Runtime**  
MCP protocol, tool registry, permission model, sandboxed execution

**Capability 5 — Model Runtime**  
LiteLLM routing, cost optimization, fallback chains, model benchmarking

**Capability 6 — Distributed Execution**  
Kafka event bus, async workers, scaling under load, observability

### Portfolio Goals

This project demonstrates:
- Senior-level AI engineering (agents, RAG, memory, evaluation)
- Backend architecture (layered monolith → service extraction)
- Distributed systems (event-driven, CQRS, Saga — Phase 3+)
- System design thinking (documented in ADRs + architecture docs)
- Open-source project discipline (docs, SDK, CLI, plugin system)

---

## Non-Goals (Stage 1)

- ❌ Multi-tenant SaaS billing
- ❌ Kubernetes deployment
- ❌ Neo4j knowledge graph
- ❌ Elasticsearch full-text search
- ❌ Real-time collaborative editing
- ❌ Mobile application

These may appear in later stages. They are not needed to validate the core.

---

## Success Criteria per Stage

### Stage 1 (Modular Monolith)
- A user can register, log in, and start a conversation
- An agent can execute a ReAct loop with tools
- Memory persists between sessions
- The LLM is swappable via config
- Everything runs with `docker-compose up`

### Stage 2 (Workflow Engine)
- Workflows are defined as DAGs and execute reliably
- Human approval gates work correctly
- Workflow state is checkpointed and resumable

### Stage 3 (Distributed)
- Kafka replaces synchronous agent calls
- Workers scale independently
- System handles 100 concurrent agent runs
