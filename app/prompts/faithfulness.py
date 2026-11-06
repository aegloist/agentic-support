"""Faithfulness grading and correction prompts."""

FAITHFULNESS_SYSTEM = "Check whether every factual claim in the support answer is supported by supplied evidence or tool results. Return JSON only. `supported` is a boolean and `hallucinated_spans` lists unsupported phrases."
FAITHFULNESS_USER = """Question: {query}
Answer: {answer}
Evidence:
{evidence}
Tool results:
{tool_results}
Return JSON only: {{\"supported\":true,\"hallucinated_spans\":[],\"rationale\":\"...\"}}
"""
SELF_CORRECT_SYSTEM = "Rewrite the answer using only supplied evidence and tool results. Remove unsupported claims and do not invent facts. Return JSON only."
SELF_CORRECT_USER = """Question: {query}
Original answer: {answer}
Reviewer feedback: {critique}
Evidence:
{evidence}
Tool results:
{tool_results}
Return JSON only: {{\"answer\":\"...\",\"citation_chunk_ids\":[]}}
"""
