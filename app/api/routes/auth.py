"""Access-token authentication for a private support demonstration."""

import hmac

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_container
from app.core.exceptions import UnauthorizedError
from app.services.container import AppContainer

router = APIRouter(tags=["auth"])


def require_user(request: Request, container: AppContainer = Depends(get_container)) -> str:
    scheme, _, provided = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and provided:
        for user_id, token in container.settings.auth_tokens.items():
            if hmac.compare_digest(provided.encode(), token.get_secret_value().encode()):
                return user_id
    raise UnauthorizedError("A valid support access token is required")


@router.get("/auth/me")
def current_user(user_id: str = Depends(require_user)) -> dict[str, str]:
    return {"user_id": user_id}
