from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import User
from models.user import UserResponse, UserUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def read_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    """Vrátí profil aktuálně přihlášeného uživatele"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    """Upraví údaje aktuálně přihlášeného uživatele"""
    current_user.username = user_update.username
    current_user.email = user_update.email
    current_user.first_name = user_update.first_name
    current_user.last_name = user_update.last_name

    db.commit()
    db.refresh(current_user)
    return current_user