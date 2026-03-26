from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

COOKIE_NAME = "replay_session"
_SESSION_SIGNING_SECRET = secrets.token_bytes(32)
_ACTIVE_SESSION_TOKENS: set[str] = set()


def _sign_session_token(token: str) -> str:
    return hmac.new(
        _SESSION_SIGNING_SECRET,
        token.encode(),
        hashlib.sha256,
    ).hexdigest()


def build_session_value() -> str:
    token = secrets.token_urlsafe(32)
    _ACTIVE_SESSION_TOKENS.add(token)
    return f"{token}.{_sign_session_token(token)}"


def _extract_session_token(raw_cookie: str | None) -> str | None:
    if not raw_cookie:
        return None

    token, separator, signature = raw_cookie.partition(".")
    if not token or separator != "." or not signature:
        return None

    expected = _sign_session_token(token)
    if not hmac.compare_digest(signature, expected):
        return None

    return token


def is_authenticated(request: Request) -> bool:
    raw_cookie = request.cookies.get(COOKIE_NAME)
    token = _extract_session_token(raw_cookie)
    return token is not None and token in _ACTIVE_SESSION_TOKENS


def revoke_session(raw_cookie: str | None) -> None:
    token = _extract_session_token(raw_cookie)
    if token is None:
        return
    _ACTIVE_SESSION_TOKENS.discard(token)


def require_authenticated(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="unauthorized")
