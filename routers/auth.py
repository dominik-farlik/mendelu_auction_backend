from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, BackgroundTasks

from pydantic import BaseModel
from sqlalchemy import select
from starlette import status
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse

import config
from config import get_settings
from database import get_db
from models import User
from models.user import UserResponse, UserCreate
from utils.email_verification import create_verification_token, send_verification_email

router = APIRouter(prefix="/auth", tags=["Auth"])

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user(db, email)
    if not user:
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(
        data: dict,
        settings: config.Settings,
        expires_delta: timedelta | None = None
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.PASSWORD_ALGORITHM)
    return encoded_jwt


async def get_current_user(
        access_token: Annotated[str | None, Cookie()] = None,
        db: Session = Depends(get_db),
        settings: config.Settings = Depends(get_settings)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    if not access_token:
        raise credentials_exception

    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.PASSWORD_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

    user = get_user(db, token_data.email)
    if user is None:
        raise credentials_exception
    return user


@router.post("/login")
async def login(
        response: Response,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Session = Depends(get_db),
        settings: config.Settings = Depends(get_settings),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not getattr(user, 'is_verified', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Před přihlášením si prosím ověřte svůj e-mail.",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
        settings=settings
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return {"message": "Přihlášení bylo úspěšné."}


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
        user_data: UserCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        settings: config.Settings = Depends(get_settings)
):
    existing_user = get_user(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_verification_token(new_user.email, settings)
    # V produkci použit doménu z konfigurace (např. settings.FRONTEND_URL)
    verification_link = f"http://localhost:8000/api/auth/verify-email?token={token}"

    background_tasks.add_task(send_verification_email, new_user.email, verification_link)

    return new_user


@router.get("/verify-email")
async def verify_email(
        token: str,
        db: Session = Depends(get_db),
        settings: config.Settings = Depends(get_settings)
):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.PASSWORD_ALGORITHM])

        if payload.get("type") != "email_verification":
            raise InvalidTokenError()

        email = payload.get("sub")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatný nebo expirovaný odkaz."
        )

    user = get_user(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uživatel nenalezen.")

    if user.is_verified:
        return {"message": "Tento e-mail už byl dříve ověřen."}

    user.is_verified = True
    db.commit()

    return RedirectResponse(url="http://localhost:5173/login?verified=true")


@router.get("/me/", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}