# ADR-001: Start as a Modular Monolith, Not Microservices

**Date:** 2026-07-18  
**Status:** Accepted  
**Author:** Mustakimshaikh

---

## Context

AgentOS needs to handle multiple concerns: authentication, agent orchestration, memory management, tool execution, and LLM routing. The instinctive architectural response is to assign each concern its own microservice.

However, this is the first version. The domain is not fully understood. The team size is one. The traffic volume is zero.

---

## Decision

Start with a **modular monolith**:
- Single FastAPI application
- Modules are Python packages with clear internal APIs
- Modules communicate via function calls, not HTTP
- Single PostgreSQL database
- Single Redis instance
- One `docker-compose up` command to start everything

---

## Rationale

### What we gain

**1. Speed of development**  
Function calls are faster to write than HTTP clients. No serialization, no network errors, no service discovery to configure.

**2. Easier debugging**  
A single stack trace shows the full call chain. No distributed trace tooling required at this stage.

**3. Atomic transactions**  
A single database means you can wrap agent execution + conversation save + memory update in one transaction. With microservices, this becomes a Saga pattern.

**4. Clean boundaries without distribution costs**  
Python module imports with explicit public interfaces (no cross-module private access) enforce the same boundary discipline as HTTP services — without the operational overhead.

**5. Learning the domain first**  
You cannot design good service boundaries without understanding the domain deeply. Premature decomposition produces the wrong services.

---

## Trade-offs

| Concern | Mitigation |
|---|---|
| "Won't this be hard to split later?" | Module boundaries are enforced from Day 1. Stage 2 extraction is wrapping the boundary in HTTP. |
| "What about scaling?" | The bottleneck in an AI system is LLM call latency, not CPU. Vertical scaling + async handles Stage 1. |
| "Team size might grow" | Module boundaries + clear interfaces support multiple developers without requiring separate deployments. |

---

## Alternatives Rejected

**11 microservices from Day 1**  
Rejected. The operational overhead (service discovery, network configuration, distributed tracing, Kafka setup, separate CI/CD per service) dominates development time before any feature is built. This is enterprise architecture cargo-culting applied to a one-person project with no users.

**2–3 microservices (auth + agent + gateway)**  
Rejected for Stage 1. Even three services require a gateway, three Docker networks, three databases or shared schema management, and three separate debugging contexts. The monolith with module separation achieves the same code organization with none of the operational complexity.

---

## Trigger for Revisiting

Extract a module to a separate service when **one of these is true**:

1. The module needs to be deployed on a different release cycle than the rest
2. The module needs different scaling characteristics (e.g., agent workers need GPU, API does not)
3. The module needs a different language runtime (e.g., a Go service for performance)
4. Multiple teams need to own different modules independently

None of these apply in Stage 1.
