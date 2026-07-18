# 003 — Domain Model

---

## Core Concepts

### Platform Layer (stable — changes rarely)

```
Organization
    │
    ├─ has many Users
    ├─ has many AgentDefinitions
    ├─ has many WorkflowDefinitions
    └─ has many Integrations

User
    │
    ├─ has many Conversations
    ├─ has many AgentRuns
    └─ belongs to Organization

AgentDefinition
    │ What an agent IS (config, prompt template, tools)
    ├─ name: string
    ├─ description: string
    ├─ system_prompt: string
    ├─ tools: list[ToolName]
    ├─ model: string
    └─ belongs to Organization
```

---

### Execution Layer (changes per run)

```
Conversation
    │ A chat session
    ├─ belongs to User
    ├─ has many Messages
    └─ has optional AgentRun

AgentRun
    │ A single execution of an agent
    ├─ belongs to User
    ├─ references AgentDefinition
    ├─ status: PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    ├─ goal: string (what was asked)
    ├─ result: string (final output)
    ├─ has many AgentSteps
    └─ total_tokens: int

AgentStep
    │ A single step within a ReAct loop
    ├─ belongs to AgentRun
    ├─ step_type: THOUGHT | ACTION | OBSERVATION | REFLECTION | FINAL
    ├─ content: string
    ├─ tool_name: string? (if ACTION)
    ├─ tool_input: json?
    ├─ tool_output: string?
    └─ tokens_used: int
```

---

### Memory Layer

```
Memory
    │
    ├─ ShortTermMemory (Redis, TTL-scoped per session)
    │   └─ key: session:{session_id}:memory
    │
    ├─ ConversationMemory (PostgreSQL, permanent)
    │   └─ Stored as Messages in a Conversation
    │
    └─ SemanticMemory (pgvector, Phase 2)
        └─ Embedding vectors for retrieval by similarity
```

---

### Workflow Layer (Capability 3)

```
WorkflowDefinition
    │ The blueprint
    ├─ name: string
    ├─ description: string
    ├─ nodes: list[WorkflowNode]
    └─ edges: list[WorkflowEdge]

WorkflowNode
    ├─ node_type: AGENT | TOOL | DECISION | HUMAN_APPROVAL | START | END
    ├─ agent_definition_id: UUID? (if AGENT)
    └─ config: json

WorkflowRun
    │ A single execution of a WorkflowDefinition
    ├─ status: PENDING | RUNNING | WAITING_APPROVAL | COMPLETED | FAILED
    ├─ checkpoint: json (current state, for resume)
    └─ has many WorkflowRunSteps
```

---

## Entity Relationship Diagram

```
Organization ──< User >── Conversation ──< Message
      │                        │
      │                        └──< AgentRun ──< AgentStep
      │
      └──< AgentDefinition >── AgentRun
      │
      └──< WorkflowDefinition ──< WorkflowRun ──< WorkflowRunStep
      │
      └──< Integration
```

---

## Ubiquitous Language

These terms have precise meanings. Use them consistently everywhere: code, comments, APIs, docs.

| Term | Meaning |
|---|---|
| **Agent** | An AI entity with a goal, tools, and a prompt. Defined by `AgentDefinition`. |
| **Agent Run** | A single execution of an Agent for a specific goal. |
| **Step** | One node traversal in the ReAct loop: THOUGHT, ACTION, OBSERVATION, REFLECTION. |
| **Workflow** | A DAG of agents, tools, and decisions. |
| **Workflow Run** | A single execution of a Workflow. |
| **Tool** | A callable function an agent can use (GitHub, Gmail, web search). |
| **Memory** | Stored context an agent can read in future sessions. |
| **Conversation** | A user-facing chat session, may trigger one or more Agent Runs. |
| **Organization** | A tenant. All resources are scoped to an Organization. |
| **Checkpoint** | Serialized agent/workflow state that allows pause + resume. |
| **Integration** | A connection to an external system (GitHub credentials, Gmail OAuth). |
