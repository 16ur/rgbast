from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.controllers.auth import AuthController
from app.core.database import SessionDep
from app.schemas.auth import Login, LoginResponse

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse, status_code=200)
def login_handler(login: Login, session: SessionDep):
    return AuthController.login_control(login, session)


@router.post("/check-auth", status_code=200)
def check_auth_handler(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Inject it here
):
    # credentials.credentials contains just the raw JWT string (without "Bearer ")
    token = credentials.credentials
    return AuthController.check_auth_control(token, session)
