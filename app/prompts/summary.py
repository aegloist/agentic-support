"""English support conversation summary prompt."""
SUMMARY_SYSTEM = "Summarize the support conversation briefly, retaining the customer request, order numbers, verified status, and any action awaiting confirmation. Return JSON only."
SUMMARY_USER = """Conversation:
{history}
Return JSON only: {{\"summary\":\"...\"}}
"""
