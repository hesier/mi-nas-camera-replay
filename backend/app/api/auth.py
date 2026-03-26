from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.auth import COOKIE_NAME, build_session_value, is_authenticated
from app.core.config import Settings, get_settings
from app.schemas.auth import AuthStatusResponse, LoginRequest

router = APIRouter()


@router.post("/api/auth/login", response_model=AuthStatusResponse)
def login(
    payload: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> AuthStatusResponse:
    if payload.password != settings.app_password:
        raise HTTPException(status_code=401, detail="invalid password")

    response.set_cookie(
        key=COOKIE_NAME,
        value=build_session_value(),
        httponly=True,
        samesite="Lax",
    )
    return AuthStatusResponse(authenticated=True)


@router.post("/api/auth/logout", response_model=AuthStatusResponse)
def logout(response: Response) -> AuthStatusResponse:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        samesite="Lax",
    )
    return AuthStatusResponse(authenticated=False)


@router.get("/api/auth/status", response_model=AuthStatusResponse)
def auth_status(
    authenticated: bool = Depends(is_authenticated),
) -> AuthStatusResponse:
    return AuthStatusResponse(authenticated=authenticated)
