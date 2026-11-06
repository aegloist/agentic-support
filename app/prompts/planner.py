"""English tool planning prompt."""
PLANNER_SYSTEM = """Plan the fewest steps needed for this support request. Return JSON only. Available tools: {tools}
Current skill: {skill_context}
Use at most six steps. Follow the skill's tool order. Place every write or destructive tool in a separate proposed step; execution requires explicit customer confirmation. Never guess an order number. Set needs_retrieval=true for policy questions.
"""
PLANNER_USER = """Customer request: {query}
Intent: {intent}
Conversation summary: {summary}
Return JSON only: {{\"rationale\":\"...\",\"steps\":[{{\"step_id\":1,\"goal\":\"...\",\"tool_name\":\"...\",\"arguments\":{{}},\"needs_retrieval\":false}}]}}
"""
