from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import RoleChecker
from models import User, Product, Bid, Watchlist
from models.product import ProductResponse
from models.role import RoleEnum, Role, RoleUpdate
from models.user import UserResponse, UserUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

allow_only_manager = RoleChecker([RoleEnum.MANAGER])


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
    current_user.public_last_name = user_update.public_last_name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
        user_id: int,
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    return user


@router.get("/", response_model=list[UserResponse], dependencies=[Depends(allow_only_manager)])
async def read_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()

    return users


@router.put("/{user_id}/role", response_model=UserResponse, dependencies=[Depends(allow_only_manager)])
async def update_user_role(user_id: int, role_data: RoleUpdate, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uživatel nebyl nalezen"
        )

    role = db.scalar(select(Role).where(Role.name == role_data.name))

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role nebyla nalezena."
        )

    user.role_id = role.id
    db.commit()
    db.refresh(user)

    return user


@router.get("/me/followed-products", response_model=list[ProductResponse], status_code=status.HTTP_200_OK)
async def get_followed_products(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    products = (
        db.query(Product)
        .join(Watchlist, Watchlist.product_id == Product.id)
        .filter(Watchlist.follower_id == current_user.id)
        .all()
    )

    for product in products:
        setattr(product, "is_followed", True)

    return products


@router.get("/me/bidded-products", response_model=list[ProductResponse], status_code=status.HTTP_200_OK)
async def get_bidded_products(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    products = (
        db.query(Product)
        .join(Bid, Bid.product_id == Product.id)
        .filter(Bid.bidder_id == current_user.id)
        .distinct()
        .all()
    )

    return products
