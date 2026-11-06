import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config.settings import clear_settings_cache
from app.main import create_app
from app.repositories.models import MessageRow

OWNER = {"Authorization": "Bearer demo-test-token-000000000000000000000"}
OTHER = {"Authorization": "Bearer other-test-token-00000000000000000000"}


@pytest.mark.parametrize("path", ["/api/v1/chat", "/api/v1/chat/stream"])
def test_foreign_conversation_cannot_be_read_or_modified(path) -> None:
    clear_settings_cache()
    with TestClient(create_app()) as client:
        first = client.post("/api/v1/chat", json={"message": "hello"}, headers=OWNER)
        assert first.status_code == 200
        session_id = first.json()["session_id"]
        body = {
            "message": "show the previous message",
            "session_id": session_id,
            "user_id": "u_demo",
        }
        response = client.post(path, json=body, headers=OTHER)
        missing = client.post(path, json={**body, "session_id": "nonexistent"}, headers=OTHER)
        assert response.status_code == missing.status_code == 404
        assert response.json()["message"] == missing.json()["message"] == "Conversation not found"

        async def message_count():
            async with client.app.state.container.session_factory() as db:
                return await db.scalar(
                    select(func.count())
                    .select_from(MessageRow)
                    .where(MessageRow.session_id == session_id)
                )

        assert asyncio.run(message_count()) == 2
        assert (
            client.post(
                "/api/v1/chat", json={"message": "hello", "session_id": session_id}, headers=OWNER
            ).status_code
            == 200
        )
