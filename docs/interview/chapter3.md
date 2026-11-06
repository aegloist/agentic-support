# Chapter 3 · When the system starts acting: tools, memory, and reliability

Explaining a return policy and actually cancelling an order differ not in how fluent the answer is, but in that the latter changes the external world. A tool call with wrong parameters, a missed permission check, or a blind double retry after a timeout cannot be fixed with prettier prompt wording. This chapter discusses the constraints the runtime must carry as a support system moves from "being able to answer" to "being able to act".

We start from one order operation and walk through tool contracts, human confirmation, idempotency, degradation, memory compression, and evaluation in turn. Finally we put these mechanisms back into the interview context: explaining failure boundaries clearly is more persuasive than stacking framework names.

> **Interview dimensions for this chapter**: tool management, fault tolerance and robustness, memory and context, engineering pitfalls, Agent Infra. For question-by-question follow-ups, see the [Chapter 3 question bank](03-rerank-memory-skill-mcp.md) and the [Chapter 1 question bank](01-langgraph-planning-intent.md).

## 3.1 Tools are action interfaces with contracts

A tool is first of all an explicit input/output contract. [`Tool`](../../app/tools/base.py) validates parameters with `input_model` and converts exceptions into tool errors the system can handle; [`ToolRegistry`](../../app/tools/registry.py) maintains the name-to-implementation mapping and exposes the Function Calling schema. The model may propose `get_order` or `cancel_order`, but whether the tool exists and whether the parameters are legal are finally checked by the program.

A bigger tool catalog is not always better. When the user asks about returns, they only need to see return-related abilities; when asking about logistics, order tracking should come first. [`skills/definitions`](../../app/skills/definitions/) stores return, tracking, and recommendation flows, and [`match_skill`](../../app/skills/loader.py) selects one Skill by trigger words or intent; the Planner uses it to narrow the visible tools. A Skill is a task specification plus a tool scope; the Tool is the actual execution interface.

MCP sits at another layer: [`app/mcp/adapter.py`](../../app/mcp/adapter.py) adapts an MCP endpoint into the local Tool interface, keeping the registration and invocation paths uniform. Function Calling is the model-side structured invocation form, MCP is the tool-access protocol, and Skill is process knowledge. The three can be combined but must not be treated as one concept. This project has no generic hundred-scale tool search or A2A multi-agent protocol.

## 3.2 Human confirmation must land in execution conditions

Risk is tiered in [`app/tools/permissions.py`](../../app/tools/permissions.py). Read operations execute directly; write or destructive actions require explicit confirmation. When the Planner scans the plan and finds a tool that needs confirmation while the current request carries no `confirm_action_id`, it produces `pending_action`. Seeing an unconfirmed proposal, the Executor will not execute the plan's write actions this round; the generation node returns an explanation that confirmation is pending.

```text
User requests a write → Planner proposes → pause execution → user confirms
                                                   ↓
                                      Executor permission check → tool executes
```

This turns "please have the user confirm" into a checkable state transition. Relying on a prompt alone to make the model say "shall I confirm?" is not enough: as long as the executor can still call the write tool, the model's output can drift from the actual action. Conversely, a confirmation marker is not unlimited authorization; the tool name, parameters, and user scope still need validation at execution time.

## 3.3 Idempotency handles duplicate actions caused by retries

The hardest part of write operations is ambiguous failure: the request was sent and timed out, and the caller does not know whether the action succeeded. Retrying mechanically could turn one refund into two. [`executor.py`](../../app/agents/nodes/executor.py) builds a fingerprint from the tool name and parameters for write tools, and uses the confirmation marker or an idempotency key to query the [`IdempotencyRepository`](../../app/repositories/idempotency.py). When the same key and fingerprint hit, the previous result is reused; when the key matches but the action differs, a conflict is reported.

This layer prevents the duplicate submissions common within this service, but it still has boundaries: external payment or refund services must also provide reliable idempotent interfaces, and between database transactions and external systems there can still be a partially-successful failure window. When answering "how do you guarantee the refund happens exactly once", explain local deduplication and cross-system consistency separately.

## 3.4 Degradation must move along the direction of risk

A failing read tool can try another read path — for example, if the order query fails, switch to retrieving generic policy so the user at least gets a usable explanation. [`READ_FALLBACKS`](../../app/agents/nodes/executor.py) writes this substitution relationship as a fixed table. Permission denials never enter the degradation table, and a write tool is never swapped for a different write action after a failure. The essence of this rule: **when availability drops, permissions must not automatically expand.**

Transient errors of the model service are handled by [`retry.py`](../../app/core/retry.py): timeouts and retryable HTTP statuses get exponential backoff with full jitter so multiple instances do not retry in lockstep; authentication and invalid-request errors are not solved by retries. The retry function addresses transient faults; it does not replace tool idempotency, and it does not mean all streaming output can be replayed invisibly.

Query boundaries, injection detection, and answer faithfulness handle different risks: the first two act on input and before tool calls, the last checks output against evidence. See [`app/guardrails/`](../../app/guardrails/) and the [security handbook](../09-security.md). Guardrails can falsely kill and can miss; therefore permission checks must remain in the tool-execution layer.

## 3.5 Memory is budget management, not unlimited storage

Sessions must continue, but feeding all history, tool outputs, and document chunks to the model without limit every turn raises cost and pollutes the context. [`budget.py`](../../app/memory/budget.py) estimates tokens from character length — this is not an official tokenizer; [`compression.py`](../../app/memory/compression.py) compresses by configured thresholds: around 50% it starts tightening tool results, at 70% it shrinks old turns, and at 85% it auto-summarizes, keeping the most recent four turns.

Compression loses information. If entities such as order numbers, sizes, and times are deleted from old turns, the next turn may go wrong. So what a memory system needs is not just a compression ratio but regression tests on "can key entities be preserved". What the repo currently implements is session storage and summary compression; there is no cross-session long-term vector memory and no entity-fidelity evaluation.

## 3.6 How to prove the system is more reliable

[`eval/runner.py`](../../eval/runner.py) splits offline evaluation into intent, retrieval, generation, and E2E; [`tests/`](../../tests/) includes unit, integration, and end-to-end tests. They answer different questions: unit tests check branches and contracts, the retrieval set checks evidence ordering, the generation set checks answer quality, and only E2E approximates the user path. The historical E2E set has only 16 items; its latency percentiles cannot serve as a production SLA.

The project already has trace, logs, metrics, and rate limiting — see [`app/observability/`](../../app/observability/); but there is no LangGraph node-level checkpointer, generic sandbox, Kubernetes scheduling, model fine-tuning, or GPU inference platform. Session persistence cannot replace breakpoint recovery of the execution graph either. These questions can be discussed as future designs; they must not be written up as completed engineering work.

## How to string the three chapters into one paragraph in an interview

> We first split support requests into paths — direct answer, policy retrieval, tool operation, and refusal; the retrieval path provides evidence through chunking, two-channel recall, fusion, and reranking, with an extra hop for complex questions; the tool path lets the model propose a plan, but the executor verifies parameters, permissions, and confirmation state, and applies idempotency to write operations. After generation, the answer is checked against the evidence for consistency. Offline evaluation shows retrieval and generation improved, but sample size and the judging method limit how far those numbers extrapolate.

The order of this narrative matches the system's true execution order. At every layer you can point to code, failure examples, and evaluation methods, so when the interviewer keeps probing, there is somewhere to land.

## Chapter summary

- Tool, Skill, and MCP sit at different layers: execution contract, task specification, and access protocol.
- Write operations are confirmed and deduplicated in the executor; only read operations may degrade via the fixed table.
- Context compression saves budget but can lose key entities.
- Tests and offline evaluation provide evidence, but do not automatically become production SLAs.

**Back to the table of contents**: [Project Interview Book](README.md). For detailed rerank, memory, Skill/MCP, and guardrail follow-ups, see the [question bank for this chapter](03-rerank-memory-skill-mcp.md).
