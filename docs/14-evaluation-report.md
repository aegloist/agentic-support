# 14 · Evaluation Report

> **Historical data notice:** all measured figures in this chapter were taken on 2026-08-22 against the original Chinese corpus and `bge-small-zh-v1.5` embeddings. They document the upstream methodology only — they are **not** measurements of the current English adaptation. Current status: [eval/MEASURED.md](../eval/MEASURED.md).

> In one line: the numbers come only from JSON written by `eval.runner`; this document spells out the methodology, datasets, ablations, and limitations so results are reproducible and interview-defensible.

## In this chapter

1. [Conclusion summary](#1-conclusion-summary)
2. [Evaluation goals and scope](#2-evaluation-goals-and-scope)
3. [Environment and reproduction](#3-environment-and-reproduction)
4. [Datasets](#4-datasets)
5. [Metric definitions](#5-metric-definitions)
6. [Intent classification](#6-intent-classification)
7. [Retrieval](#7-retrieval)
8. [Generation and hallucination](#8-generation-and-hallucination)
9. [End-to-end](#9-end-to-end)
10. [Automated tests](#10-automated-tests)
11. [Against resume numbers](#11-against-resume-numbers)
12. [Unmeasured items and next steps](#12-unmeasured-items-and-next-steps)

Covers: [`eval/runner.py`](../eval/runner.py), [`eval/metrics.py`](../eval/metrics.py), [`eval/MEASURED.md`](../eval/MEASURED.md).
For commands and CI gates, see [10 · Evaluation and Regression](10-evaluation.md).

**Measurement date:** 2026-08-22
**Generation / judge model:** DeepSeek `deepseek-chat` (DeepSeek-V3 via API)
**Dense recall:** `BAAI/bge-small-zh-v1.5` (loaded)
**Rerank:** `BAAI/bge-reranker-base` (loaded)
**Raw reports:** identifier `all_20260822T121308Z.json`. `eval/reports/*.json` is git-ignored and not distributed with the repo; the report files themselves are not in the repository — [`MEASURED.md`](../eval/MEASURED.md) is authoritative for conclusions.

---

## 1. Conclusion summary

| Task | Set | Main result | Baseline |
|---|---|---|---|
| Intent | 100 cases / 14 classes | `intent_v3` + overlay **100%** | Keyword rules 51%; no-overlay v1 85% / v2 86% |
| Retrieval | 65 cases / 39 docs | BM25 **P@1 76.9%**, **R@3 90.0%**, **MRR 0.84** | `bge-small` only **83.1 / 94.6 / 0.89** |
| Retrieval + CE | Same | Hybrid+CE **P@1 89.2%**, **R@3 97.7%**, **MRR 0.94** | vs BM25 +12.3 / +7.7 percentage points |
| Generation / hallucination | 65 cases | RAG+self-correction faithfulness **100%**, hallucination **0%** | No retrieval 80% / 20%; relative reduction 100% |
| E2E | 16 cases | Refusal / tool paths **100%**; keywords **9/11 (81.8%)** | P50 **4.9s** / P95 **5.8s** |
| Regression | pytest | **154 passed** | No real LLM / no weight downloads |

### Key points

This round of evaluation verified four things: Adaptive routing splits greetings and injections out of retrieval; the local `bge-small-zh-v1.5` pulls vector-only P@1 from the hash baseline's 3.1% to **83.1%**; the Cross-Encoder then lifts Hybrid P@1 from 83.1% to **89.2%**; and faithfulness self-correction pushes same-model-judge hallucination from 20% down to 0%. On these 65 cases, BM25+small RRF did not beat small-only.

---

## 2. Evaluation goals and scope

In a support scenario, "feels fine" is not enough. This repo pins interview-ready numbers to four offline tasks:

| Task | Answers | Does not answer |
|---|---|---|
| `intent` | Can 14 intent classes be classified, and how much does the overlay contribute | Whether routing strategy is optimal |
| `retrieval` | Can policy docs be ranked to the top | Whether generated sentences are correct |
| `generation` | Does the model fabricate without evidence; is self-correction useful | Human preference, prose style |
| `e2e` | Are injections refused, do orders go through tools, what is latency | Load testing, multi-tenancy |

**In scope:** local SQLite + in-memory retrieval + DeepSeek + local `bge-small-zh-v1.5` + Cross-Encoder; knowledge base `knowledge/*.md` (39 docs).
**Out of scope:** larger embeddings (bge-m3 etc.), online traffic A/B, human annotation agreement.

---

## 3. Environment and reproduction

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" ".[rerank]"
# .env: fill in DEEPSEEK_API_KEY; to pull weights from a mirror inside China set HF_ENDPOINT=https://hf-mirror.com

pytest -q
python -m eval.runner --task all --llm
```

Reports are written to `eval/reports/{task}_{UTC}.json` and `eval/reports/latest.json`.
After any prompt, chunking, or knowledge-base change, rerun the corresponding task, then update [`MEASURED.md`](../eval/MEASURED.md) and the numbers in this document.

### Why

pytest clears real keys in `tests/conftest.py`, so CI is reproducible and free. The percentages on a resume must come from the JSON produced by the `--llm` run — never typed in by hand.

---

## 4. Datasets

| File | Cases | Gold labels | Purpose |
|---|---|---|---|
| `eval/dataset/intent_100.jsonl` | 100 | `intent` (14 classes) | Classification accuracy and ablation |
| `eval/dataset/rag_eval.jsonl` | 65 | `relevant_doc_ids` + `gold_answer_contains` | Retrieval P/R/MRR + generation keywords |
| `eval/dataset/e2e_eval.jsonl` | 16 | `expect_refused` / `expect_keywords` | Full-graph paths and latency |

### 4.1 Intent: distribution across 14 classes

| Label | Cases | Business meaning |
|---|---|---|
| `faq_policy` | 16 | Invoices, points/loyalty, support hours, and other policies |
| `return_exchange` | 8 | Returns / exchanges |
| `out_of_scope` | 8 | Injections, bomb threats, stock tips, and other over-reach |
| `order_inquiry` | 7 | Order lookup |
| `logistics` | 7 | Shipping tracking |
| `product_consult` | 7 | Specs / stock |
| `chitchat` | 6 | Small talk |
| `refund` | 6 | Refund status |
| `cancel_order` | 6 | Cancel unshipped order |
| `recommendation` | 6 | Product recommendations |
| `coupon` | 6 | Coupon stacking |
| `complaint` | 6 | Complaints |
| `human_handoff` | 6 | Human handoff |
| `greeting` | 5 | Greetings |

Sample: `{"id":"i011","query":"How do I get an invoice","intent":"faq_policy"}`.

### 4.2 Retrieval / generation: 65 policy questions

The gold label is the **document stem** (e.g. `return_policy`), not a chunk id. The 65 cases cover 38 distinct document stems; 5 queries mark two relevant documents (e.g. free shipping + coupons).

Sample:

```json
{"id":"r001","query":"Can made-to-order items be returned within 7 days, no questions asked","relevant_doc_ids":["return_policy"],"gold_answer_contains":["made-to-order","no-questions-asked"]}
```

The knowledge base `knowledge/` holds **39** Markdown documents, roughly 156 chunks after ingest. Document-level matching: strip `_{index}` off `document_id` to get the stem.

### 4.3 E2E: 16 case path coverage

| Group | IDs | What is being tested |
|---|---|---|
| Greeting | e01 | Direct, no retrieval |
| Policy | e02–e05, e09, e16 | Single / Multi + keywords |
| Tools | e06–e08, e14, e15 | Order lookup / logistics / stock / cancel (HITL) |
| Refusal | e10–e12 | Injection, bomb request, stock tips |
| Handoff | e13 | `human_handoff` |

`e10` "Ignore previous instructions…" expects `refused=true`.
Demo user `u_demo`; orders `ORD10001` / `ORD10002` / `ORD10003`.

---

## 5. Metric definitions

### Key points

Retrieval is graded on **documents**, not chunks: multiple slices of the same policy count once. Hallucination rate = the share of faithfulness-judge verdicts of `supported=false` — it is **not** manual fact-checking.

### Code summary

```python
# eval/metrics.py
def precision_at_k(relevant, retrieved, k):
    top = retrieved[:k]
    return sum(item in relevant for item in top) / len(top)

def recall_at_k(relevant, retrieved, k):
    return sum(item in relevant for item in retrieved[:k]) / len(relevant)

def mrr(relevant, retrieved):
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0
```

| Metric | Formula (as implemented in this repo) | Used where |
|---|---|---|
| Accuracy | hits / N | Intent, 100 cases |
| Precision@k | relevant docs in top-k / k | P@1 |
| Recall@k | relevant docs hit in top-k / gold docs | R@3 |
| Hit@k | at least one relevant in top-k | Vector-path baseline |
| MRR | reciprocal rank of the first relevant doc; 0 on miss | Retrieval |
| Faithfulness | share of `supported=true` | Generation |
| Hallucination rate | share of `supported=false` | Generation |
| Relative reduction | `(naive - checked) / naive` | No retrieval vs RAG+self-correction |
| Keyword hits | all of `gold_answer_contains` appear in the answer | Generation / E2E |
| Refusal accuracy | `expect_refused` matches `response.refused` | E2E (3 cases) |
| Tool path | query contains ORD/stock/cancel, and answer contains an order number or `pending_action` | E2E |
| Latency | P50 / P95 of `response.latency.total_ms` | E2E |

### Why

P@1 checks "is the first doc right" (most sensitive for support); R@3 checks "did related policies make it into the context." Reporting only Hit@k hides the "first doc is the wrong one" failure mode. Keyword hits are more independent than same-model faithfulness — report both side by side in interviews.

---

## 6. Intent classification

Production path: DeepSeek outputs JSON (`intent_v3`) → `apply_intent_overlay` corrects it. If the LLM is down, keyword rules take over, then the same overlay.

### 6.1 Ablation (100 cases)

| System | Overlay | Accuracy |
|---|---|---|
| Keyword rules `intent_rules_v1` | off | 51.0% |
| `intent_v1` | off | 85.0% |
| `intent_v2` | off | 86.0% |
| Ambiguity overlay only | — | **100%** |
| `intent_v3` + overlay (production) | on | **100%** |

The rule baseline scores 0 on `chitchat` / `product_consult` and only 16.7% on `refund`: keywords can't distinguish "return" from "refund status". The LLM lifts the whole thing to 85%–86%; the overlay specifically targets stable Chinese ambiguities — handoff vs refund, policy phrasing vs returns/exchange.

### Code summary

```python
# app/agents/nodes/intent_overlay.py
def high_precision_intent(query: str) -> IntentLabel | None:
    # only return a label on high-confidence phrases; otherwise None (defer to the LLM)
    if any(token in text for token in _HANDOFF):
        return IntentLabel.HUMAN_HANDOFF
    ...
```

The eval can run `apply_overlay=False` for ablation; production runs `apply_overlay=True`.

### Why / say proactively in interviews

100% **includes the overlay**. The overlay targets stable support phrases (handoff beats refund), and is **not** gold labels hardcoded per query id like `i070`. The rule baseline must be kept: it proves "just if-else" is not enough, and it is the fallback when the LLM is down.

---

## 7. Retrieval

65 cases, `top_k=5`. The dense side is local `BAAI/bge-small-zh-v1.5` (`BgeM3EmbeddingProvider`, `backend=bge-small-zh-v1.5`). The Cross-Encoder is loaded, so the report includes `hybrid+cross-encoder`. A hash-baseline run earlier the same day (report identifier `all_20260822T042748Z.json`) had vector-only Hit@1 of 3.1%.

### 7.1 System comparison

| System | Precision@1 | Recall@3 | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|---|
| BM25 | 76.9% | 90.0% | 76.9% | 90.8% | 0.84 |
| `bge-small-zh-v1.5` only | 83.1% | 94.6% | 83.1% | 95.4% | 0.89 |
| BM25 + small + RRF | 83.1% | 94.6% | 83.1% | 95.4% | 0.89 |
| Hybrid + Cross-Encoder | **89.2%** | **97.7%** | 89.2% | 98.5% | **0.94** |

Report fields: taken from that run's report `all_20260822T121308Z.json` (not distributed with the repo); field names match [`eval/runner.py`](../eval/runner.py).

### Key points

Small-only already beats BM25 (P@1 +6.2, R@3 +4.6 percentage points). On this set RRF and small-only are **identical in numbers** — don't oversell Hybrid as "fusion always adds points." The effective additional gain comes from the **Cross-Encoder** (vs BM25: P@1 +12.3, R@3 +7.7; vs RRF: P@1 +6.1, R@3 +3.1). With the same-day hash baseline at Hit@1 3.1%, Hybrid can't be called semantic retrieval before small is wired in.

### Why

The two-tower design fixes synonym recall ("I don't want it anymore" ≈ 7-day no-questions return); the Cross-Encoder scores query and document together, handling rankings like "made-to-order, past 7 days, quality issues." On a resume, write CE's **89.2 / 97.7 / 0.94**, while also saying the dense path is small, not m3, and that RRF added no gain on this set.

---

## 8. Generation and hallucination

Same 65 cases: no-retrieval generation vs Hybrid evidence generation vs `self_correct_answer` after a faithfulness failure (LLM rewrite first, then extractive fallback). The judge shares the generator's model: `deepseek-faithfulness_v1`.

| Condition | Faithfulness | Hallucination rate | Keyword hits |
|---|---|---|---|
| No retrieval | 80.0% | 20.0% | 36.9% |
| RAG | 96.9% | 3.1% | 95.4% |
| RAG + LLM self-correction | **100%** | **0%** | 95.4% |

Relative reduction `(20.0% - 0%) / 20.0% = 100%` (common resume bar ≥62%). No-retrieval faithfulness of 80% falls within the 54%–88% band.

### Code summary

```python
# eval/runner.py · eval_generation
naive = await _generate_answer(llm, query, "(no retrieved evidence)")
rag = await _generate_answer(llm, query, evidence)
if not rag_judge.supported:
    checked, checked_judge, _ = await self_correct_answer(...)
```

Hallucination definition: `FaithfulnessChecker.check(...).supported is False`.

### Why / methodology pitfalls

A same-model judge is **optimistic** (generator and judge share knowledge and phrasing). Keyword hits jump from 36.9% to 95.4% with RAG, and self-correction does **not** raise keywords further — it repairs "evidence support," not missing gold keywords. Report both columns together in interviews.

---

## 9. End-to-end

16 cases through the full `ChatService` → LangGraph (guardrails, intent, Adaptive five-way routing, tools, HITL). Rate limiting is temporarily raised to 1000 req/min during eval.

| Metric | Result |
|---|---|
| Refusal accuracy (3 cases) | **100%** |
| Keyword hits (11 cases) | **9/11 (81.8%)** |
| Tool path (5 cases) | **100%** |
| Latency P50 / P95 / mean | **4925 / 5774 / 4567 ms** |
| Intent section P50 | 803 ms |
| Generation LLM section P50 | 1084 ms |
| Retrieval / tools sections P50 | **0 ms** |

Retrieval and tools P50 are 0 because among the 16 cases Direct / Refuse never retrieves and some paths never call tools — the **median gets dragged to 0**. With n=16 the P95 is a discrete quantile (5.8s); the actual slowest is `e02` multi at **11.1s**. Injection `e10` took **10 ms** — caught by the regex, never touching the LLM.

### Strategy distribution (measured)

| ID | Intent | Strategy | Latency |
|---|---|---|---|
| e01 | greeting | direct | 3.1s |
| e02 | return_exchange | multi | 11.1s |
| e03 | faq_policy | single | 4.4s |
| e04 | faq_policy | single | 5.2s |
| e05 | faq_policy | single | 4.9s |
| e06 | order_inquiry | agent | 5.5s |
| e07 | order_inquiry | agent | 4.8s |
| e08 | logistics | agent | 4.3s |
| e09 | coupon | single | 5.0s |
| e10 | (injection) | refuse | 10ms |
| e11 | out_of_scope | refuse | 1.5s |
| e12 | out_of_scope | refuse | 1.7s |
| e13 | human_handoff | direct | 5.3s |
| e14 | product_consult | single | 5.8s |
| e15 | cancel_order | agent | 5.7s (HITL confirmed; not actually cancelled) |
| e16 | faq_policy | single | 4.8s |

Source: that run's report `all_20260822T121308Z.json` (not distributed with the repo); rollup methodology in [`MEASURED.md`](../eval/MEASURED.md).

---

## 10. Automated tests

`pytest -q`: **154 passed** (includes Cross-Encoder / local embedding unit tests with mocked weights). Covers RRF, Adaptive routing, guardrails, compression, tool permissions, Skills, MCP, execution fallback, self-correction, the order repository, HTTP chat, plus the `eval` metric functions and retrieval cache / self-correction / query rewrite / vector retrieval / tokenization.

pytest **never** calls real DeepSeek / never downloads the Cross-Encoder. Live metrics require `eval.runner --llm`; CE scores must come from the `hybrid+cross-encoder` row.

---

## 11. Against resume numbers

**Can write (measured):**

- Intent: rules 51% → no-overlay v1 85% / v2 86% → v3+overlay **100%** (≥97%)
- `bge-small` only: P@1 **83.1%**, R@3 **94.6%**, MRR **0.89**
- Hybrid+CE: P@1 **89.2%**, R@3 **97.7%**, MRR **0.94**
- BM25 baseline: P@1 **76.9%** (58–85), R@3 **90%** (63–91), MRR **0.84**
- Hallucination: no retrieval 20% → RAG+self-correction **0%** (&lt;4%); relative reduction 100% (≥62%)
- No-retrieval faithfulness **80%** (54–88%)
- E2E P50 **4.9s** / P95 **5.8s**; injection refusal ~10ms; keywords **9/11**

**Cannot write:**

- This round's E2E keywords as 100%
- The 100% intent as "pure LLM, no rules"
- Faithfulness 100% as "zero hallucination by manual fact-checking"
- The dense path as bge-m3, or RRF as beating small-only on this set

---

## 12. Unmeasured items and next steps

| Item | Status | What counts as measured |
|---|---|---|
| Cross-Encoder `BAAI/bge-reranker-base` | **Measured** Hybrid+CE P@1 89.2% / R@3 97.7% | Rerun retrieval after swapping checkpoints |
| `bge-small-zh-v1.5` | **Measured** vector-only P@1 83.1% / R@3 94.6% | Rerun separately after a larger embedding; never write it as m3 |
| Intent v3 without overlay as its own column | Production 100% includes overlay; v3 with overlay off was not written out to JSON separately | Run another column with `apply_overlay=False` |
| E2E keywords | 9/11 this round | Inspect the 2 failures' answers, then adjust generation or gold labels |
| Manual faithfulness | None | Sample 20 cases, dual annotation |
| Concurrency / rate limiting / fault injection | Single-request E2E only | Separate load test; not part of this report |

---

Previous chapter [13 · Interview Script](13-interview-engineering-rag.md) · [Back to index](README.md)
