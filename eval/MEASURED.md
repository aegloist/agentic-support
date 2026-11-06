# Evaluation status

The inherited Chinese evaluation results do not measure this English adaptation and are intentionally not reported here. No English model-quality results have been measured yet.

Use the English cases in `eval/dataset/e2e_eval.jsonl` as a starter regression set. Add English retrieval questions with expected source document IDs before comparing retrievers. Run `python -m eval.runner --task retrieval` for the offline retrieval checks and configure the selected model before running generation or end-to-end evaluation.

Record the model/provider, embedding model and dimensions, corpus version, dataset version, run date, and raw report with every result.
