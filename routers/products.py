import json
from datetime import datetime, UTC
from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import RoleChecker, get_current_user_optional
from models import ProductImage, Bid
from models.product import Product, ProductResponse, ProductCreate, Status, ProductBid
from models.group import Group
from models.role import RoleEnum
from models.user import User
from routers.auth import get_current_user
from utils import save_upload_file

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

allow_only_manager = RoleChecker([RoleEnum.MANAGER])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
        product_data: str = Form(..., description="JSON řetězec odpovídající ProductCreate"),
        cover_image: Optional[UploadFile] = File(None, description="Hlavní úvodní obrázek"),
        additional_images: List[UploadFile] = File([], description="Seznam dalších obrázků"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Vytvoření nového produktu včetně nahrání hlavního obrázku a galerie.
    """
    try:
        product_in = ProductCreate(**json.loads(product_data))
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Neplatný formát JSON dat v poli product_data.")

    group_result = db.execute(select(Group).where(Group.id == product_in.group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {product_in.group_id} neexistuje."
        )

    # TODO: ověřit, zda je current user v dané skupině

    new_product = Product(
        **product_in.model_dump(
            exclude={"cover_image"}),
            cover_image=save_upload_file(cover_image),
            created_by_id=current_user.id,
    )

    db.add(new_product)
    db.flush()

    for img_file in additional_images:
        if img_file.filename:
            img_path = save_upload_file(img_file)
            product_image = ProductImage(
                product_id=new_product.id,
                filename=img_path
            )
            db.add(product_image)

    db.commit()
    db.refresh(new_product)

    return new_product


@router.patch("/{product_id}/approve", response_model=ProductResponse)
async def approve_product(
        product_id: int,
        current_user: User = Depends(allow_only_manager),
        db: Session = Depends(get_db),
):
    """
    Schválení produktu manažerem (změna stavu na aktivní).
    """
    result = db.execute(select(Product).where(Product.id == product_id))
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
    db.commit()
    db.refresh(product)

    return product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
        skip: int = 0,
        limit: int = 10,
        only_active: bool = True,
        db: Session = Depends(get_db)
):
    """Získání seznamu produktů"""
    now = datetime.now(UTC)
    query = select(Product)

    if only_active:
        query = query.where(
            Product.status == Status.APPROVED,
            Product.starts_at <= now,
            Product.ends_at >= now
        )

    result = db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/group/{group_id}", response_model=List[ProductResponse])
async def get_products_by_group(
        group_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
):
    """Získá všechny produkty patřící do specifikované skupiny."""

    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {group_id} nebyla nalezena."
        )

    return group.products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: int,
        current_user: Annotated[User, Depends(get_current_user_optional)],
        db: Session = Depends(get_db)
):
    """Získání detailu konkrétního produktu."""
    result = db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    is_followed = False
    if current_user:
        is_followed = any(follow.follower_id == current_user.id for follow in product.followers)

    setattr(product, "is_followed", is_followed)

    return product


@router.get("/{product_id}/bids", response_model=List[ProductBid])
async def get_product_bids(
        product_id: int,
        db: Session = Depends(get_db)
):
    """Získání příhozů produktu"""
    result = db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    bids_result = db.execute(
        select(Bid)
        .where(Bid.product_id == product_id)
        .order_by(Bid.amount.desc())
    )
    bids = bids_result.scalars().all()

    return bids
