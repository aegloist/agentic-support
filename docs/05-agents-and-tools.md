# 05 · Agents, Tools and HITL

> In one sentence: the intent LLM + overlay trims the tool catalog on demand; write operations go through HITL + idempotency; read tools get fallbacks and the Planner can only call tools in the shrunk catalog; MCP and local tools share the same Function Calling interface.

## Chapter Contents

1. [Node Split](#node-split)
2. [Intent Classification](#intent-classification)
3. [On-Demand Skill Loading](#on-demand-skill-loading)
4. [Planner](#planner)
5. [Executor and Fallback](#executor-and-fallback)
7. [HITL and Idempotency](#hitl-and-idempotency)
8. [Faithfulness Self-Correction](#faithfulness-self-correction)
9. [Memory Compression](#memory-compression)

Covers: `app/agents/`, `app/tools/`, `app/skills/`, `app/mcp/`, `app/memory/`.

## Node Split

Intent, routing, retrieval, planning, execution, generation, faithfulness, and compression each get their own node so they can be mocked individually, capped in steps, and streamed progressively over SSE. Step cap: `MAX_AGENT_STEPS=8`, `MAX_TOOL_CALLS=6`.

## Intent Classification

### Key Points

Production path: DeepSeek outputs JSON → `intent_v3` prompt → a **high-confidence overlay** corrects confusable labels. If the LLM is down, fall back to keyword rules, then the same overlay.

Classification quality must be measured on the current intent dataset; no accuracy result is published yet.

### Code Summary

```python
# app/agents/nodes/intent.py
async def classify(self, query: str) -> IntentResult:
    fallback = rule_based_intent(query)
    try:
        parsed = parse_model(response.content, IntentResult)
        return self._maybe_overlay(query, parsed)
    except (LLMProviderError, LLMOutputError):
        return self._maybe_overlay(query, fallback)

def _maybe_overlay(self, query, parsed):
    label, overlay_note = apply_intent_overlay(query, parsed.label)
    if overlay_note:
        parsed.label = label
        parsed.rationale = f"{parsed.rationale};{overlay_note}"
    return parsed
```

The overlay takes priority for: injection/privilege-escalation → human handoff (overriding refund/complaint) → policy "how is it calculated" vs "can this item be returned" and the like. Implementation: `app/agents/nodes/intent_overlay.py`. Prompts: `app/prompts/intent.py`. Labels: `IntentLabel`.

Evaluation can disable the overlay: `IntentClassifier(..., apply_overlay=False)`, used to compare against the pure prompt.

### Why

A request such as "please have a human review this refund" requires human handoff even though it mentions a refund. The overlay prioritizes explicit support phrases; evaluate classification with and without the overlay to measure its contribution.

## On-Demand Skill Loading

### Key Points

Three JSON files: `return_handling`, `order_tracking`, `product_recommend`. The Planner first matches trigger phrases, then maps by intent. After a match it **only exposes that Skill's tools** + `search_knowledge` + `escalate_to_human`.

### Code Summary

```python
# app/skills/loader.py
INTENT_TO_SKILL = {
    "return_exchange": "return_handling",
    "refund": "return_handling",
    "logistics": "order_tracking",
    "order_inquiry": "order_tracking",
    "recommendation": "product_recommend",
    ...
}

def match_skill(query: str, intent_label: str = "") -> dict | None:
    for skill in load_skills():
        if any(trigger in query for trigger in skill.get("triggers", [])):
            return skill
    return skill_by_name(INTENT_TO_SKILL.get(intent_label))
```

```json
# app/skills/definitions/return_handling.json
{
  "name": "return_handling",
  "triggers": ["return", "exchange", "7 days no-reason return"],
  "tools": ["get_order", "get_order_items", "search_knowledge", "create_return_request"]
}
```

### Why

Cramming all 15 tools into the Planner prompt makes the model call things like `cancel_order` recklessly. On-demand loading keeps the catalog shorter and the step order more stable. It's not "read the JSON only when the LLM fails".

## Planner

### Key Points

The LLM breaks the question into ≤6 steps; tool names must be in the shrunk catalog. On failure, `skill_to_plan` (extracting `ORD\d+` from the query), then falls back again to `search_knowledge`.

Write/destructive tools that haven't been confirmed yet: generate an `ActionProposal`; the executor won't run writes this turn.

### Code Summary

```python
# app/agents/nodes/planner.py
async def create_plan(self, query, intent_label, summary):
    skill = match_skill(query, intent_label)
    allowed = _allowed_tools(skill, self._registry)
    try:
        plan = parse_model(response.content, AgentPlan)
        plan = _sanitize_plan(plan, self._registry, allowed)
        if plan.steps:
            return plan
    except (LLMOutputError, LLMProviderError):
        pass
    if skill:
        return skill_to_plan(skill, query, self._registry)
    return _knowledge_fallback(query, self._registry)
```

This is the **decomposition-layer fallback** mentioned in the résumé.

## Executor and Fallback

### Key Points

On read-tool failure, switchtools per the fallback table (`get_order` → `search_knowledge`).

**Permission denials and writes do not go through this table**, preventing unconfirmed refunds from being executed via a "tool swap".

### Code Summary

```python
# app/agents/nodes/executor.py
READ_FALLBACKS = {
    "get_order": ["search_knowledge"],
    "track_shipment": ["get_order", "search_knowledge"],
    "mcp_store_hours": ["search_knowledge"],
    ...
}

async def execute_with_fallback(tool, step, context, registry, query):
    try:
        result = await tool.run(step.arguments, context)
        if result.success:
            return result
        raise ToolExecutionError(...)
    except ToolPermissionError:
        raise
    except (AppError, InvalidRequestError) as exc:
        for fallback_name in READ_FALLBACKS.get(tool.name, []):
            fb_result = await registry.get(fallback_name).run(...)
            if fb_result.success:
                return fb_result.model_copy(update={"output": {..., "fallback_from": tool.name}})
        raise
```

The tool entrypoint uniformly uses `Tool.run`: first validate `input_model`, then call `execute`. This is the **execution-layer fallback**.

Unit tests: `tests/unit/test_executor_fallback.py`.

## HITL and Idempotency

### Key Points

`write` / `destructive` without `confirm_action_id` → `ToolPermissionError`.

The Planner returns `pending_action` first; the client then sends `confirm_action_id`.

The same `action_id`/`idempotency_key` plus an arguments fingerprint: the second call returns the first call's result. A differing fingerprint → `IDEMPOTENCY_CONFLICT`.

### Code Summary

```python
# app/tools/permissions.py
WRITE_RISKS = {ToolRisk.WRITE, ToolRisk.DESTRUCTIVE}

def assert_permitted(tool: Tool, *, confirmed: bool) -> None:
    if tool.risk in WRITE_RISKS and not confirmed:
        raise ToolPermissionError(
            f"{tool.name} is {tool.risk.value} and requires explicit user confirmation"
        )
```

The executor handles write tools via `IdempotencyRepository.get_if_matches(key, sha256(tool+args))`.

## Faithfulness Self-Correction

### Key Points

After generation, a judge grades `supported`. On failure, first rewrite with the LLM constrained to the evidence, then fall back to extractive composition.

### Code Summary

```python
# app/agents/nodes/faithfulness.py
result = await checker.check(query=..., answer=..., chunks=..., tool_results_text=...)
if result.supported:
    return {"final_answer": answer}
corrected = await self_correct_answer(query, chunks, result)
return {"final_answer": corrected}
```

Measure evidence support and correction behavior with the current generation dataset before claiming a reduction in unsupported answers.

## Memory Compression

### Key Points

Token budget `TOKEN_BUDGET=128000` uses a character-count heuristic, not an official provider tokenizer.

| Utilization | Level | Behavior |
|---|---|---|
| <50% | none | no compression |
| 50%-70% | soft | truncate tool results to 400 characters |
| 70%-85% | hard | 160 characters + sliding window |
| >85% | auto-compact | last 4 turns + summary |
