"""Query complexity classification prompt."""
COMPLEXITY_SYSTEM = """Classify the retail-support query. Return JSON only. `complexity` must be simple, single_hop, multi_hop, tool_required, or out_of_scope. `strategy` must be direct, single, multi, agent, or refuse. Route greetings to direct, one-policy questions to single, questions combining multiple policy conditions to multi, account-specific order or product operations to agent, and unrelated requests to refuse.
"""
COMPLEXITY_USER = """prompt_version={prompt_version}
Intent: {intent}
Customer question: {query}

Return JSON only: {{\"complexity\":\"...\",\"strategy\":\"...\",\"confidence\":0.0,\"rationale\":\"...\"}}
"""
