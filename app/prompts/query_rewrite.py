"""English policy-search query rewrite prompt."""

REWRITE_SYSTEM = "Rewrite the policy question as one to three short English search queries. Preserve timing, product type, customization, and defect constraints. Return JSON only."
REWRITE_USER = """Original question: {query}
Missing detail: {missing_aspect}
Return JSON only: {{\"queries\":[\"...\"]}}
"""
