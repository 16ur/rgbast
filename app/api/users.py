from fastapi import APIRouter
from app.controllers.user import UserController
from app.core.database import SessionDep
from app.schemas.user import UserCreate, UserCreateResponse

router = APIRouter()


@router.post("/users", response_model=UserCreateResponse, status_code=201)
def create_user_handler(user: UserCreate, session: SessionDep):
    return UserController.create_user_control(user, session)


@router.get("/users", status_code=201)
def get_user_from_username_handler(username: str, session: SessionDep):
    return UserController.get_user_from_username_control(username, session)
