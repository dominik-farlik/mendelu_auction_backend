from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status, Cookie
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

import config
from config import get_settings
from database import get_db
from models import User
from models.role import RoleEnum
from routers.auth import get_current_user, TokenData, get_user


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]):
        if not current_user.role or current_user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nemáte dostatečná oprávnění pro tuto akci."
            )
        return current_user


async def get_current_user_optional(
        access_token: Annotated[str | None, Cookie()] = None,
        db: Session = Depends(get_db),
        settings: config.Settings = Depends(get_settings)
):
    if not access_token:
        return None

    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.PASSWORD_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        token_data = TokenData(email=email)
    except InvalidTokenError:
        return None

    user = get_user(db, token_data.email)
    if user is None:
        return None
    return user