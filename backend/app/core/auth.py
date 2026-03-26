import hashlib
import hmac

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings

COOKIE_NAME = "replay_session"


def build_session_value(password: str) -> str:
    return hmac.new(password.encode(), b"authenticated", hashlib.sha256).hexdigest()


def is_authenticated(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> bool:
    cookie_value = request.cookies.get(COOKIE_NAME)
    if not cookie_value:
        return False

    expected = build_session_value(settings.app_password)
    return hmac.compare_digest(cookie_value, expected)


def require_authenticated(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    if not is_authenticated(request=request, settings=settings):
        raise HTTPException(status_code=401, detail="unauthorized")
