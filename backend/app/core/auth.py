import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

COOKIE_NAME = "replay_session"
_SESSION_SIGNING_SECRET = secrets.token_bytes(32)


def _sign_session_token(token: str) -> str:
    return hmac.new(
        _SESSION_SIGNING_SECRET,
        token.encode(),
        hashlib.sha256,
    ).hexdigest()


def build_session_value() -> str:
    token = secrets.token_urlsafe(32)
    return f"{token}.{_sign_session_token(token)}"


def is_authenticated(request: Request) -> bool:
    raw_cookie = request.cookies.get(COOKIE_NAME)
    if not raw_cookie:
        return False

    token, separator, signature = raw_cookie.partition(".")
    if not token or separator != "." or not signature:
        return False

    expected = _sign_session_token(token)
    return hmac.compare_digest(signature, expected)


def require_authenticated(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="unauthorized")
