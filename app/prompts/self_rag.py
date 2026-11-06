"""Evidence sufficiency grading prompt."""
GRADE_SYSTEM = "Decide whether retrieved evidence can answer the question without guessing. Return JSON only. `relevant` means at least one source applies; `sufficient` means a complete accurate answer is supported. Identify what is missing."
GRADE_USER = """Question: {query}
Evidence:
{evidence}
Return JSON only: {{\"relevant\":true,\"sufficient\":true,\"missing_aspect\":\"\",\"rationale\":\"...\"}}
"""
