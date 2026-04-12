from fastapi import APIRouter
from app.core.database import SessionDep, get_session
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import create_user


router = APIRouter()

@router.post('/users/', response_model=User)
def create_user_handler (user: UserCreate, session: SessionDep) :
    return create_user(user, session)