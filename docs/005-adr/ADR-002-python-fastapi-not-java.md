# ADR-002: Python + FastAPI as the Backend Language (Not Java)

**Date:** 2026-07-18  
**Status:** Accepted

---

## Context

The previous plan used Java Spring Boot for business services and Python FastAPI for AI services. This required two separate runtimes, two build systems, and two deployment artifacts.

---

## Decision

Use **Python + FastAPI** for the entire Stage 1 backend.

---

## Rationale

**1. LangGraph is Python-native**  
LangGraph, LangChain, LiteLLM, and all modern AI frameworks are first-class Python. Using Java forces translation layers, HTTP bridges, or incomplete port libraries.

**2. Single runtime reduces friction**  
One requirements.txt. One Dockerfile. One process. The agent code and the API code share the same data models, the same async event loop, and the same imports.

**3. Async is built-in**  
Python asyncio + FastAPI handles the concurrent LLM streaming that this project requires. `async def` on route handlers + `async for chunk in stream` on LLM responses is clean and natural.

**4. Java is not gone — it's deferred**  
In Stage 3, when workflow execution splits into its own service with heavy concurrency requirements, Java Spring Boot is the right choice for that service. The argument for Java strengthens when you need a battle-tested JVM runtime for a specific workload, not as the default for everything.

---

## Trade-offs

| Concern | Response |
|---|---|
| Python is slower than Java | LLM call latency (1–30s) completely dominates. Python's GIL overhead is irrelevant. |
| Type safety | Pydantic v2 provides runtime validation + type hints throughout. FastAPI enforces schemas at the boundary. |
| Java experience | Stage 1 is for learning AI engineering. Java expertise is applied in Stage 3 where it matters. |

---

## Alternatives Rejected

**Java Spring Boot for auth + FastAPI for AI**  
Two runtimes, HTTP bridge between them, two ORMs, two migration tools. All complexity, no benefit for Stage 1.

**Node.js**  
No first-class AI framework support. TypeScript AI libraries are thin wrappers. Rejected.
