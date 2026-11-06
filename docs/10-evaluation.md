# Evaluation and Regression

The English evaluation files are starter regression cases. They do not establish model quality. Any reported score must include the exact corpus, dataset, model, embedding dimensions, and run output used to produce it.

## Tasks

| Task | What it checks | What it does not prove |
|---|---|---|
| Intent | Whether a message maps to its expected support intent | That route selection is optimal |
| Retrieval | Whether expected policy documents appear in ranked results | That a generated answer is correct |
| Generation | Whether claims are supported by retrieved evidence | Human preference or production accuracy |
| End to end | Refusal, tool paths, confirmation, and response behavior | Load handling or multi-user security |

## Run the checks

```bash
pytest -q
python -m eval.runner --task intent
python -m eval.runner --task retrieval
```

Generation and end-to-end evaluation call a live model and require provider credentials:

```bash
python -m eval.runner --task generation --llm
python -m eval.runner --task e2e --llm
```

The runner writes reports to `eval/reports/`, which is ignored by Git. Keep the raw report for every result you intend to publish.

## Retrieval labels

Each row in `eval/dataset/rag_eval.jsonl` names the relevant policy document IDs. The runner measures Precision@1, Recall@3, Hit@k, and MRR for BM25, dense search, fusion, and any available reranker. Keep query wording representative of customer questions and confirm each expected document and answer phrase against `knowledge/`.

## Generation checks

The generation task compares answers without evidence, with retrieved evidence, and after self-correction. Faithfulness is judged by the configured model and can be optimistic because the generator and judge may share a model. Report keyword support and citation checks alongside model-judged faithfulness.

## Reporting rules

- Report scores only from runs against the current corpus, evaluation dataset, and model configuration.
- Record model/provider, embedding model and dimensions, reranker, corpus version, dataset version, date, and raw output.
- No English model-quality result has been measured yet; see `eval/MEASURED.md`.
- Do not interpret an empty or missing report as a score of zero.
