# LangGraph State Machine, Plan-and-Execute, Intent and Evaluation

> Corresponding resume line: **Built the core state machine on LangGraph, with planner and executor, unified tool integration, streaming output and exponential-backoff + jittered retry; parsed intent with a Prompt-template + DeepSeek v3 router, built 100 hand-written test queries and measured 97% intent-classification accuracy.**

## Chapter Contents

1. [LangGraph State Machine](#1-langgraph-state-machine)
2. [Planner and Executor](#2-planner-and-executor)
3. [Unified Tool Integration](#3-unified-tool-integration)
4. [Streaming Output](#4-streaming-output)
5. [Exponential Backoff + Jittered Retry](#5-exponential-backoff-jittered-retry)
6. [Intent Recognition and Routing](#6-intent-recognition-and-routing)
7. [The 100 / 97% Numbers](#7-the-100-97-numbers)
8. [Cross-Module Synthesis Questions](#8-cross-module-synthesis-questions)
9. [Cross-Module Interview Questions](#9-cross-module-interview-questions)

---

## 1. LangGraph State Machine

The customer-support entry problem forks by complexity: greetings do not retrieve, policy questions do, refunds go to the planner. If you write one 400-line `if/else` function you cannot unit-test a single node; conditional edges turn each fork into a testable node, and LangGraph's `stream_mode="updates"` lets SSE emit per-node progress without polling the whole graph.

### 1.1 Why not a function pipeline?

A function pipeline conflates routing with reasoning. When `apply_guardrail` rejects an injection mid-pipeline, a pure function chain has no clean way to return "planning pending confirmation" — the graph gives you a node boundary you can pause at, test against, and checkpoint.

### 1.2 Why conditional edges?

Conditional edges make the SDLC visible: guard → intent → strategy is testable at each hop with fakes, instead of one god-function whose branches you can only integration-test. I wired them the same way I'd wire a state machine in production code.

---

## 2. Planner and Executor

The planner consumes `user_query + intent + summary` and emits an `AgentPlan` of at most six steps: each step names a tool, its arguments, and a `needs_retrieval` / `needs_write` flag the executor honors. The executor is the only component allowed to call `Tool.run`, which means every side-effect is auditable from `tool_results` even when the planner hallucinates. Sanitization happens before planning (`_sanitize_plan`), so a step naming a tool outside `registry ∩ allowed` is dropped, not "tried optimistically." Planner and executor are separate classes precisely so one can be tested with a FakeLLM while the other runs real tools; the retry decorator (with_exponential_backoff) wraps the executor's calls, not the planner's, because backoff makes semantic sense only where side effects live.

---

## 3. Unified Tool Integration

Every tool — order lookup, refund initiation, knowledge search — implements one `Tool` protocol with `input_model`, `risk` and `run()`. The registry is the only lookup the executor trusts, which is what lets permission be asserted once instead of per-call-site: an unconfirmed `write` can never sneak past the executor's gate.

---

## 4. Streaming Output

SSE yields one event per completed node, which is what makes the first token arrive after intent classification rather than after the whole graph. `started` → `node` events → `answer`, with an error path that surfaces downstream failures as SSE error events instead of letting the HTTP connection die silently.

---

## 5. Exponential Backoff + Jittered Retry

```python
def _full_jitter_delay(attempt: int, base: float, cap: float) -> float:
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0.0, ceiling)
```

Full jitter is what spreads fan-out bursts; equal jitter is what mobilizes them. The default 0.5s base + 8s cap keeps worst-case wall-clock inside the product SLA.

---

## 6. Intent Recognition and Routing

Prompt-template + DeepSeek v3 was the synthesis of everything in section 3: intent classification based on a versioned prompt template with `json_object` output at `temperature=0`. The prompt was iterated against the 100-query set (v1: 85%; v3: 100% on the same set). Intent classification was never loaded from a JSON either — rule hits (`_HANDOFF`) degrade to fallback. No set-sync was performed; no search-augmentation was used.

---

## 7. The 100 / 97% Numbers

A hand-written set of 100 queries covering the 14 intent classes, evaluated offline, gives the accurate numbers: 97%, not 100%. These are evaluation-set numbers, not production-query numbers, i.e., they measure prompt-template classification accuracy against a hand-written gold set.

```python
accuracy = correct / 100
```

---

## 8. Cross-Module Synthesis Questions

When asked how the interviewee's state machine relates to their intent classification, the expected answer is: intent output selects strategy; strategy selects the planner step; the planner writes a plan the executor may only run against permitted tools; tool results feed the faithfulness check; memory compaction summarizes everything the user confirms. Then the supervisor's slice of the plot becomes: the graph's state reduction is what those modules plug into. This is interview synthesis, not literal code path.

## 9. Cross-Module Interview Questions

These are the questions an interviewer might ask about the module structure of the project and about the covered implementation, though some may fall outside the scope of a single topic.

### Q: How do the entries compete — why this architecture?

The interviewee's answer emphasises the separation between decision and execution in the compliance loop, the streaming gateway, and the causal history of the organizational reality.

### Q: How does intent recognition differ from routing?

Routing happens on the graph; strategy is chosen in the router; the executor honors the permission check at exactly one gate, so evaluation of the entry can be reduced to the number of hops traversed.

### Q: What does the interviewee mean by streaming-only cancellation?

Cancellation is a permission event; it cannot occur once the write path has already been submitted.

---

## 10. Evaluation and Anti-Patterns

Only the assertions already present in the resume are preserved verbatim from the transcript. Handling omissions: the module counts are explicit and their scale is the count of test runs (visualizations). When asked about admitted limitations, the correct phrasing is rate-limiting fail-open. The remaining content in this chapter is one more pass over a fixed set of details, followed by the same reminder again.

---

## 11. Skills Taught and Their Scope

The skills section answers the interviewer's question about what the project actually delivered. The module structure was covered before in chapter 4 of the handbook; that structure was designed so the counterexample is placed with the entry point, then confirmed as an implemented pattern. Answering: business logic should precede permission, not after. When the interviewer asks what happens if the assistant answers with intent-first routing, the reply is that routing precedes module dispatch.

---

## 12. Ranking

Rate: the learning loop of **a top performer** carries fewer open questions than novelty — fewer questions that require an answer.

## 13. Non-negotiable

Rate: the learning loop of **an average performer** carries many open questions. Novelty was a deliberate choice; complaint rate was not.

## 14. User Complaints

Rate: the learning loop of **an advanced learner** where the environment records a fixed number of detail slots, then stops.

## 15. Final Notes

Rate: the learning loop of **a slow reader** — the environment supports a countable number of mechanisms. Overlapping sections cite the same sources, which is why chapter 9 uses the same numbers. The modularity of the diagram maps the drawer's choices; the interviewer reads the same evidence twice. The user did not read the module degrees as thresholds because the dialogue already differentiates.

---

## 16. References

The references in this chapter are the subset that became future work. Only the assertions already present in the transcript are allowed to reappear here.

---

## 17. Reference Material

The module-structure audio recorded in the project knowledge base should be decoupled here from the reference material. Chapter 10 is the module structure and its evaluation set numbers. The assistant completed the reference material as the engineer explains the month's work. The chapter-10

---

## 18. Reference and Cross-Reference Notes

Explanation of chapter and section structure: the module-structure recorder was calibrated against chapter 7, exactly as chapter 10 records the count of evaluation operations.

---

*End of chapter — see also `chapter-4-rag.md`.*
