# Chapter 1 · From one customer-support question to a controllable execution graph

The user says "hello" and the system should respond at once; the user asks "can a custom item still be returned" and the system needs to look up policy; the user says "cancel ORD100001 for me" and the system must verify identity, read the order, and stop before a write operation to wait for confirmation. All three sentences enter the same chat interface yet demand three different execution styles. This is the first design question of this project: **how do you let the model take part in decisions while keeping the business flow explainable and constrainable?**

This chapter follows one request through `ChatService` and LangGraph, explaining what intent, complexity, planning, and state are each responsible for. After reading it, you should be able to explain, without looking at a diagram: why a request enters a particular branch, when the model makes a decision, and where the code takes the decision power back.

> **Interview dimensions for this chapter**: architecture choices, applied AI engineering, Prompt and framework principles, resume grilling. For question-by-question follow-ups, see the [Chapter 1 question bank](01-langgraph-planning-intent.md).

## 1.1 Deriving the execution path from business differences

E-commerce support looks like Q&A but actually mixes three kinds of work: pure conversation, knowledge-grounded explanation, and reads/writes against business systems. If every question retrieved first, greetings would gain latency for nothing; if every question went to a free-looping agent, refunds and similar writes would take on unacceptable execution risk. Hence this project models "retrieve or not, call a tool or not" explicitly as a routing outcome.

```text
Request → Guardrail → Intent recognition → Complexity routing
                         ├─ DIRECT: greetings and the like, generate directly
                         ├─ SINGLE: one policy retrieval
                         ├─ MULTI: iteratively gather policy evidence
                         ├─ AGENT: plan and execute tools
                         └─ REFUSE: refuse when out of scope
```

The branches across these five strategies live in [`app/agents/graph.py`](../../app/agents/graph.py), and the complexity decision in [`app/retrieval/adaptive.py`](../../app/retrieval/adaptive.py). The guardrail sits before intent: a request judged as refusable is not handed to the later model classification at all. `SINGLE` and `MULTI` enter the same retrieval node but use different algorithms inside; only `AGENT` reaches the Planner and Executor. After generation, every non-refusal path passes a faithfulness check before the session is compressed.

**Design corollary**: "smart routing" is not finished by writing a few more `if`s. What matters is that every path has explicit inputs, outputs, and failure behavior. When the routing model is unavailable, a rule fallback still yields a conservative strategy from intent, order numbers, and complexity conditions; this keeps the service answering, but also means misclassification can steer later branches, so it needs separate measurement.

## 1.2 State is the shared language between nodes

LangGraph nodes do not call each other's internals; they read and update `AgentState`. The state carries the user question, intent, strategy, retrieved chunks, plan, tool results, the action awaiting confirmation, and the final answer. The benefit of this design: every step's result can be checked by the next step, and nodes can be tested in isolation.

The graph is built once in [`ChatService.__init__`](../../app/services/chat_service.py), not recompiled per request. At request start, `ChatService` does the rate limiting, loads the session, and initializes state; at request end, it writes the answer and summary back to the session store. Database connections live in request scope and tools access them via [`request_scope`](../../app/core/request_scope.py) — connection objects never go into the graph state. State holds business data and decision outcomes; it must not become a junk drawer for runtime resources.

> **Interview follow-up: does having a graph equal an autonomous agent?** No. Most paths in this graph are bounded workflow. Only the `AGENT` path contains model-driven planning of tool steps; tool observations do not flow back into the planner at every step for re-planning. The accurate name is "a support workflow with a planning branch".

## 1.3 Two model judgments: intent and complexity

Intent recognition answers "what does the user want to do"; complexity routing answers "which path does doing it need". These are close but cannot be merged. For instance, "how does the seven-day no-questions-asked return work" is a policy explanation, while "can this order still be returned under the seven-day policy" involves both policy and order data. The former can go through retrieval; the latter should prefer tools.

[`IntentClassifier`](../../app/agents/nodes/intent.py) uses structured model output, falling back to rules on failure; confusable phrases additionally pass through an override layer for correction. [`AdaptiveRouter`](../../app/retrieval/adaptive.py) estimates complexity from intent and query, outputting one of five strategies. JSON mode and low temperature only reduce output variance; the schema validation in [`json_parser.py`](../../app/providers/json_parser.py) is the boundary at which the program accepts a decision.

Here is a number that is easy to be caught out on: on 100 historically self-built samples, `intent_v3` plus the override layer reached 100%. This is not a pure model result, nor production-distribution accuracy. The [measured records](../../eval/MEASURED.md) list every baseline; in an interview, state the sample source, the override layer, and the extrapolation limits together.

## 1.4 The planner only proposes; the executor decides whether to act

Once a request enters the `AGENT` path, the [`Planner`](../../app/agents/nodes/planner.py) gives the model a restricted tool catalog according to intent and the matched Skill. The model returns a structured `AgentPlan`; the code drops unknown tools and truncates the plan to at most six steps. Even if the model writes out a tool that does not exist, it gains no execution ability out of thin air.

The [`Executor`](../../app/agents/nodes/executor.py) then executes the plan step by step, checking call counts and risk level. A failing read tool can fall back to a fixed substitute read-tool table; a write tool must pass human confirmation and idempotency verification. So the model's job is **to propose candidate steps**, while the program's job is **to verify and execute the allowed steps**. This division of labor explains the system's real boundary better than claiming "the model autonomously completes the refund".

When a plan includes a write and confirmation has not arrived, the Planner produces `pending_action`; the Executor runs no tool this round and the answering node returns confirmation copy. Only the next round, carrying the confirmation marker, enters the write path. Confirmation is not a please-be-careful sentence in a prompt — it is a checkable state condition before execution. Details in [Chapter 3](chapter3.md).

## 1.5 Seeing the architecture boundary from one request

Suppose the user types "cancel ORD100001 for me". The ideal path is: guardrail check → recognize the cancel-order intent → route to `AGENT` → Planner proposes steps such as read-order, cancel-order → the write action generates a pending proposal → the Executor performs it after the user confirms. The real outcome also depends on order status, permissions, and tool returns; you cannot say the order was cancelled just because `cancel_order` appeared in the plan.

This path also shows what this project has NOT implemented: no per-step ReAct re-planning, no multi-agent teams, no node-level LangGraph checkpointer. Session messages are persisted, but persistence is not the same as the execution graph resuming from any node. When interviewers ask about these capabilities, discuss applicability scenarios and the cost of adding them — do not count them as existing features.

## Chapter summary

- **Judgment layer**: intent decides the task type; complexity decides the execution strategy.
- **Orchestration layer**: LangGraph makes branches and node outputs explicit; `ChatService` owns the request lifecycle.
- **Execution layer**: the Planner proposes, the Executor validates, and writes wait for confirmation.
- **Evidence boundary**: offline intent scores include the override layer; a single-graph workflow must not be described as a multi-agent system.

**Continue reading**: [Chapter 2 · How knowledge becomes a verifiable answer](chapter2.md). If the interviewer drills line by line into graph nodes, JSON plans, and intent data, open the [question bank for this chapter](01-langgraph-planning-intent.md).
