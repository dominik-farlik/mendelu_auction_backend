from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import RoleChecker
from models.product import Product, ProductResponse, ProductCreate, Status
from models.group import Group
from models.role import RoleEnum
from models.user import User
from routers.auth import get_current_user

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

allow_only_manager = RoleChecker([RoleEnum.MANAGER])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
        product_in: ProductCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Vytvoření nového produktu.
    Produkt je přiřazen ke skupině a ve výchozím stavu čeká na schválení (is_active = False).
    """
    group_result = await db.execute(select(Group).where(Group.id == product_in.group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {product_in.group_id} neexistuje."
        )

    # TODO: ověřit, zde je current user v dané skupině

    new_product = Product(
        **product_in.model_dump(),
        created_by_id=current_user.id,
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return new_product


@router.patch("/{product_id}/approve", response_model=ProductResponse)
async def approve_product(
        product_id: int,
        current_user: User = Depends(allow_only_manager),
        db: AsyncSession = Depends(get_db),
):
    """
    Schválení produktu manažerem (změna stavu na aktivní).
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    # TODO: Ověření, zda je přihlášený uživatel manažerem skupiny, kam produkt patří
    # Např. porovnat current_user.id s product.group.manager_id

    if product.status == Status.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Produkt již je schválen."
        )

    product.status = Status.APPROVED
    await db.commit()
    await db.refresh(product)

    return product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
        skip: int = 0,
        limit: int = 10,
        only_active: bool = True,
        db: AsyncSession = Depends(get_db)
):
    """Získání seznamu produktů, které aktuálně probíhají."""
    now = datetime.utcnow()
    query = select(Product)

    if only_active:
        query = query.where(
            Product.status == Status.APPROVED,
            Product.starts_at <= now,
            Product.ends_at >= now
        )

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Získání detailu konkrétního produktu."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )
    return product