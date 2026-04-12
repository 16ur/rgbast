from fastapi import FastAPI
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.database import SessionDep

def create_user(userSchema: UserCreate, session: SessionDep) :
    newUser = User(**userSchema.model_dump())
    session.add(newUser)
    session.commit()
    session.refresh(newUser)
    return newUser
