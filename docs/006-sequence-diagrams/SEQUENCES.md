# 006 — Sequence Diagrams

---

## 1. User Login + JWT Issuance

```
Client          API /auth        Auth Module      PostgreSQL       Redis
  │                │                  │               │              │
  │  POST /login   │                  │               │              │
  │───────────────▶│                  │               │              │
  │                │  login(email,pw) │               │              │
  │                │─────────────────▶│               │              │
  │                │                  │ SELECT user   │              │
  │                │                  │──────────────▶│              │
  │                │                  │◀──────────────│              │
  │                │                  │ verify bcrypt │              │
  │                │                  │ generate JWT  │              │
  │                │                  │ store refresh │              │
  │                │                  │──────────────▶│              │
  │                │  AuthResponse    │               │              │
  │◀───────────────│◀─────────────────│               │              │
  │ {access, refresh, user}           │               │              │
```

---

## 2. Chat Request → Streaming Agent Response

```
Client          API /chat        Chat Module    Workflow Engine    LiteLLM
  │                │                 │                │               │
  │  POST /chat    │                 │                │               │
  │ Authorization: │                 │                │               │
  │ Bearer <token> │                 │                │               │
  │───────────────▶│                 │                │               │
  │                │ verify JWT      │                │               │
  │                │ save message    │                │               │
  │                │────────────────▶│                │               │
  │                │                 │ load history   │               │
  │                │                 │ call agent     │               │
  │                │                 │───────────────▶│               │
  │                │                 │                │ build prompt  │
  │                │                 │                │──────────────▶│
  │                │                 │                │               │
  │◀───────────────│◀────────────────│◀───────────────│◀──────────────│
  │  SSE: delta    │                 │   stream       │  stream token │
  │  SSE: delta    │                 │                │               │
  │  SSE: [DONE]   │                 │                │               │
  │                │                 │ save response  │               │
  │                │                 │────────────────│               │
```

---

## 3. ReAct Agent Loop (Single Run)

```
workflow-engine         Planner Node      Tool Node        LiteLLM
      │                      │                │               │
      │  execute(state)      │                │               │
      │─────────────────────▶│               │               │
      │                      │  LLM call     │               │
      │                      │──────────────────────────────▶│
      │                      │◀──────────────────────────────│
      │                      │  Thought: "I need to search"  │
      │                      │  Action: search("LangGraph")  │
      │                      │               │               │
      │         route to Tool Node           │               │
      │─────────────────────────────────────▶│               │
      │                      │               │ execute tool  │
      │                      │               │───────────────│
      │                      │               │ Observation   │
      │◀─────────────────────│◀──────────────│               │
      │  state += observation │               │               │
      │                      │               │               │
      │  route to Reflection  │               │               │
      │─────────────────────▶│               │               │
      │                      │ LLM: "Is this correct?"       │
      │                      │──────────────────────────────▶│
      │                      │◀──────────────────────────────│
      │                      │  "Yes, answer is confident"   │
      │  route to END         │               │               │
      │─────────────────────▶│               │               │
      │  return final output  │               │               │
```

---

## 4. Token Refresh Flow

```
Client          API /auth/refresh    Auth Module    PostgreSQL    Redis
  │                    │                  │              │            │
  │  POST /refresh     │                  │              │            │
  │  {refreshToken}    │                  │              │            │
  │───────────────────▶│                  │              │            │
  │                    │ refresh(token)   │              │            │
  │                    │─────────────────▶│              │            │
  │                    │                  │ hash token   │            │
  │                    │                  │ SELECT where │            │
  │                    │                  │ token_hash=? │            │
  │                    │                  │─────────────▶│            │
  │                    │                  │◀─────────────│            │
  │                    │                  │ check valid, │            │
  │                    │                  │ not revoked  │            │
  │                    │                  │ issue new JWT│            │
  │◀───────────────────│◀─────────────────│              │            │
  │  {accessToken}     │                  │              │            │
```

---

## 5. Logout + Blacklist Flow

```
Client          API /auth/logout    Auth Module    Redis
  │                   │                  │           │
  │  POST /logout     │                  │           │
  │  Authorization:   │                  │           │
  │  Bearer <token>   │                  │           │
  │──────────────────▶│                  │           │
  │                   │ logout(token)    │           │
  │                   │─────────────────▶│           │
  │                   │                  │ extract jti│
  │                   │                  │ calc TTL   │
  │                   │                  │ SET jwt:blacklist:{jti}
  │                   │                  │───────────▶│
  │                   │                  │ revoke all │
  │                   │                  │ refresh    │
  │                   │                  │ tokens     │
  │◀──────────────────│◀─────────────────│            │
  │  200 OK           │                  │            │
```
