from fastapi import APIRouter
from app.controllers.auth import AuthController
from app.core.database import SessionDep
from app.schemas.auth import Login, LoginResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse, status_code=200)
def login_handler(login: Login, session: SessionDep):
    return AuthController.login_control(login, session)
