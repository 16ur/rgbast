from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
import jwt
from sqlmodel import select

from app.models.user import User
from app.schemas.auth import Login, LoginResponse
from app.core.database import SessionDep
from pwdlib import PasswordHash

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    def login(loginSchema: Login, session: SessionDep) -> LoginResponse:
        hasher = PasswordHash.recommended()
        if "@" in loginSchema.username:
            query = select(User).where(User.email == loginSchema.username)
        else:
            query = select(User).where(User.username == loginSchema.username)

        # Team tout à la fois ou vérifications séparées ? A vos claviers !
        result = session.exec(query).first()
        if result and hasher.verify(loginSchema.password, result.password):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = AuthService.create_access_token(
                data={"sub": result.username + result.email},
                expires_delta=access_token_expires,
            )
            return LoginResponse(
                jwt=token,
                username=result.username,
                firstname=result.firstname,
                lastname=result.lastname,
                email=result.email,
            )
        return None

    def check_auth(token: str):
        load_dotenv()
        secret_key = os.getenv("SECRET_KEY", "key_and_peele")
        decoded_token = jwt.decode(token, secret_key)
        return decoded_token

    def create_access_token(data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})

        load_dotenv()
        secret_key = os.getenv("SECRET_KEY", "key_and_peele")
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
        return encoded_jwt
