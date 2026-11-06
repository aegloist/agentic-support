import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config.settings import Settings, clear_settings_cache
from app.main import create_app

DEMO_TOKEN = "demo-test-token-000000000000000000000"


@pytest.mark.parametrize("path", ["/api/v1/chat", "/api/v1/chat/stream"])
@pytest.mark.parametrize("token", ["", "wrong-token"])
def test_chat_rejects_unverified_identity(path, token) -> None:
    clear_settings_cache()
    with TestClient(create_app()) as client:
        response = client.post(
            path,
            json={"message": "hello", "user_id": "u_demo"},
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )
        assert response.status_code == 401


def test_chat_uses_authenticated_user_instead_of_body() -> None:
    clear_settings_cache()
    with TestClient(create_app()) as client:
        headers = {"Authorization": f"Bearer {DEMO_TOKEN}"}
        assert client.get("/api/v1/auth/me", headers=headers).json() == {"user_id": "u_demo"}
        response = client.post(
            "/api/v1/chat",
            json={"message": "hello", "user_id": "other"},
            headers=headers,
        )
        assert response.status_code == 200
        import asyncio

        from app.repositories.models import SessionRow

        async def owner():
            async with client.app.state.container.session_factory() as session:
                row = await session.get(SessionRow, response.json()["session_id"])
                return row.user_id

        assert asyncio.run(owner()) == "u_demo"


def test_unconfigured_auth_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_TOKENS", "{}")
    clear_settings_cache()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {DEMO_TOKEN}"})
        assert response.status_code == 401
    clear_settings_cache()


def test_auth_tokens_must_be_long_and_unique() -> None:
    with pytest.raises(ValidationError):
        Settings(auth_tokens={"u_demo": "short"})
    with pytest.raises(ValidationError):
        Settings(auth_tokens={"u_demo": DEMO_TOKEN, "other": DEMO_TOKEN})
