# 🧠 AgentOS — An Operating System for AI Workflows

> **Build one platform that proves everything.**

[![Stage](https://img.shields.io/badge/Stage-1%20Modular%20Monolith-blue)]()
[![Capability](https://img.shields.io/badge/Capability-1%20Agent%20Runtime-orange)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## The Idea

AgentOS is not an application. It is an **operating system for AI workflows**.

That one sentence changes every design decision:

| As an Application | As an Operating System |
|---|---|
| You build features | You build primitives |
| Agents are hardcoded | Agents are plugins |
| Tools are embedded | Tools are registered |
| Models are fixed | Models are interchangeable |
| Workflows are one thing | Workflows are composable |

Most AI projects die as demos. This one is designed to grow.

---

## Architecture Philosophy

This project follows a deliberate evolution, not a big-bang design.

```
Stage 1 (Now)          Stage 2 (Later)        Stage 3 (When needed)
─────────────          ──────────────          ──────────────────────
Modular Monolith   →   Split AI workers   →    Kafka + Distributed
Single FastAPI         Module boundaries        True microservices
PostgreSQL + Redis      per capability          Scale on evidence
Learn the domain        Clean interfaces        Not on assumption
```

**The rule:** Only introduce complexity when you feel the pain of not having it.

---

## Repository Structure

```
agentos/
│
├── core/                     # Platform primitives (framework-level)
│   ├── workflow-engine/      # DAG execution, state machines, checkpointing
│   ├── memory/               # Short-term, long-term, semantic memory
│   ├── tool-runtime/         # MCP-compatible tool registry + executor
│   ├── model-router/         # LiteLLM, cost routing, fallback chains
│   └── evaluation/           # LLM scoring, latency, accuracy tracking
│
├── agents/                   # Reusable agent definitions
│   ├── planner/              # Goal decomposition, subtask planning
│   ├── research/             # Web search, retrieval, synthesis
│   ├── reviewer/             # Output quality verification
│   └── reflection/           # Self-critique and correction loops
│
├── workflows/                # Workflow plugins (use core + agents)
│   ├── research/             # Deep research workflow
│   ├── repo-analyzer/        # GitHub repo analysis
│   └── code-review/          # Automated code review
│
├── integrations/             # External tool connectors
│   ├── github/               # GitHub API
│   ├── gmail/                # Gmail API
│   └── slack/                # Slack API
│
├── api/                      # FastAPI backend (monolith, clean modules)
│   └── app/
│       ├── modules/
│       │   ├── auth/         # Auth, JWT, users, orgs
│       │   ├── chat/         # Conversations, streaming
│       │   ├── agent/        # Agent runs, history
│       │   └── workspace/    # Projects, tasks, docs
│       └── db/               # SQLAlchemy models + Alembic migrations
│
├── frontend/                 # Next.js application
│
├── sdk/                      # pip install agentos-sdk
│
├── cli/                      # agentos init / run / deploy
│
├── docs/                     # Full project documentation
│   ├── 001-vision/
│   ├── 002-architecture/
│   ├── 003-domain-model/
│   ├── 004-api-spec/
│   ├── 005-adr/
│   ├── 006-sequence-diagrams/
│   ├── 007-threat-model/
│   ├── 008-deployment/
│   ├── 009-benchmarks/
│   ├── 010-evaluation/
│   └── 011-roadmap/
│
├── infra/
│   └── docker/
│
├── scripts/
└── docker-compose.yml
```

---

## Capability-Driven Roadmap

The architecture is built **capability by capability**, not feature by feature.  
Each capability teaches you something deep before you move to the next.

```
Capability 1: Agent Runtime          ← You are here
Capability 2: Memory
Capability 3: Workflow Engine
Capability 4: Tool Runtime
Capability 5: Model Runtime
Capability 6: Distributed Execution  ← Kafka comes here, not Day 1
```

See [docs/011-roadmap/ROADMAP.md](./docs/011-roadmap/ROADMAP.md) for the full breakdown.

---

## Stage 1 Stack (Right Now)

| Layer | Technology | Why |
|---|---|---|
| Backend | Python + FastAPI | LangGraph-native, async-first |
| Agent Framework | LangGraph | StateGraph, checkpointing, streaming |
| LLMs | LiteLLM | Model-agnostic from day one |
| Database | PostgreSQL | Single DB, clean schema, Alembic migrations |
| Cache | Redis | Session + short-term agent memory |
| Frontend | Next.js 14 | App Router, streaming-ready |
| Container | Docker Compose | Local dev, no Kubernetes yet |

**What is intentionally NOT in Stage 1:**
- ❌ Kafka (no async workers yet)
- ❌ Neo4j (no graph memory yet)
- ❌ Elasticsearch (no hybrid search yet)
- ❌ Kubernetes (no production scale yet)
- ❌ 11 microservices (learn the domain first)

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd agentos

# 2. Configure
cp .env.example .env
# Add your GEMINI_API_KEY or OPENAI_API_KEY

# 3. Start infrastructure
docker-compose up -d

# 4. Install Python dependencies
cd api && pip install -r requirements.txt

# 5. Run migrations
alembic upgrade head

# 6. Start backend
uvicorn app.main:app --reload --port 8000

# 7. Start frontend
cd ../frontend && npm install && npm run dev
```

---

## SDK Vision (Future)

```python
from agentos import Workflow, Agent

workflow = Workflow(name="research")
workflow.add_agent(Agent.from_preset("research"))
workflow.add_agent(Agent.from_preset("reviewer"))

result = await workflow.run("Summarize the state of LLM reasoning in 2025")
```

---

## CLI Vision (Future)

```bash
agentos init my-workflow
agentos agent add research
agentos run --task "analyze this repo"
agentos deploy --cloud gcp
```

---

## Documentation Index

| # | Document | Status |
|---|---|---|
| 001 | [Vision & Goals](./docs/001-vision/VISION.md) | ✅ Done |
| 002 | [Architecture](./docs/002-architecture/ARCHITECTURE.md) | ✅ Done |
| 003 | [Domain Model](./docs/003-domain-model/DOMAIN.md) | ✅ Done |
| 004 | [API Spec](./docs/004-api-spec/API.md) | 🔵 In Progress |
| 005 | [ADR Log](./docs/005-adr/) | ✅ Done |
| 006 | [Sequence Diagrams](./docs/006-sequence-diagrams/) | ✅ Done |
| 007 | [Threat Model](./docs/007-threat-model/THREATS.md) | ⚪ Pending |
| 008 | [Deployment Guide](./docs/008-deployment/DEPLOY.md) | ⚪ Pending |
| 009 | [Benchmarks](./docs/009-benchmarks/) | ⚪ Pending |
| 010 | [Evaluation](./docs/010-evaluation/EVAL.md) | ⚪ Pending |
| 011 | [Roadmap](./docs/011-roadmap/ROADMAP.md) | ✅ Done |

---

> **"Learn the domain before you distribute it."**
