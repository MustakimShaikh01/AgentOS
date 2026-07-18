# ADR-003: Defer Kafka Until Capability 6

**Date:** 2026-07-18  
**Status:** Accepted

---

## Context

The original architecture included Kafka from Day 1. The rationale was to build an event-driven system from the start for loose coupling and scalability.

---

## Decision

**Kafka is not introduced until Capability 6 (Distributed Execution).**

Stage 1–5 use synchronous function calls and async Python within a single process.

---

## Rationale

**1. Kafka solves a problem we don't have yet**  
Kafka is a solution for: fan-out consumers, decoupled async processing, replay-able event logs, and consumer group scaling. None of these problems exist in Stage 1. We have zero users.

**2. Kafka adds significant operational overhead**  
Kafka requires: ZooKeeper or KRaft, topic creation, partition configuration, consumer group management, schema registry (for Avro), offset tracking, dead letter queue handling, and monitoring. This is 2+ weeks of setup that produces zero user-visible features.

**3. The code structure doesn't change**  
When Kafka is introduced in Stage 6, the change is:
```python
# Stage 1–5
await agent_service.run(run_id, goal)

# Stage 6
await kafka.produce("agent.run.requested", {"run_id": run_id, "goal": goal})
```
The business logic is identical. Only the invocation mechanism changes. We don't lose any architectural value by deferring this.

**4. Learning Kafka meaningfully requires context**  
You learn Kafka best when you feel the pain of not having it: the API is slow because agent runs block it, workers can't scale independently, you need multiple consumers for evaluation + billing + audit. In Stage 6, Kafka is the obvious answer. In Stage 1, it's configuration theater.

---

## Trigger for Introduction

Kafka is introduced when **all three** are true:
1. Agent runs are visibly blocking API response time
2. At least two downstream consumers need the same event (e.g., eval + billing)
3. We need independent scaling of the agent worker pool

---

## Alternatives

**Redis Streams (intermediate step)**  
Redis Streams provides lighter-weight pub-sub before committing to Kafka's full operational complexity. This is a valid Stage 4–5 intermediate step if the need arises before Stage 6.
