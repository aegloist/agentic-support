import json

import httpx
import pytest

from app.config.settings import Settings
from app.providers.deepseek import DeepSeekProvider


def test_generic_model_settings_override_legacy_environment(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "new-provider-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "chosen-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-key")
    settings = Settings()
    assert settings.llm_configured
    assert settings.deepseek_api_key.get_secret_value() == "new-provider-key"
    assert settings.deepseek_base_url == "https://example.test/v1"
    assert settings.deepseek_model == "chosen-model"


@pytest.mark.asyncio
async def test_configured_endpoint_preserves_json_mode_and_model() -> None:
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer":"Supported policy answer"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    settings = Settings(
        LLM_API_KEY="test-key", LLM_BASE_URL="https://example.test/v1", LLM_MODEL="chosen-model"
    )
    async with httpx.AsyncClient(
        base_url=settings.deepseek_base_url, transport=httpx.MockTransport(respond)
    ) as client:
        provider = DeepSeekProvider(settings, client=client)
        result = await provider.generate(
            [{"role": "user", "content": "Return JSON describing the policy"}],
            response_format={"type": "json_object"},
        )
    assert str(seen[0].url) == "https://example.test/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer test-key"
    assert json.loads(seen[0].content)["model"] == result.model == "chosen-model"
    assert json.loads(seen[0].content)["response_format"] == {"type": "json_object"}
    assert result.usage.total_tokens == 15
