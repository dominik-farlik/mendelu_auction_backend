from datetime import datetime, UTC
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from dependencies import RoleChecker
from models import Organization, Group, Product, Order, User
from models.order import OrderStatus
from models.organization import OrganizationResponse, OrganizationPublicResponse
from models.product import ProductResponse, Status
from models.role import RoleEnum
from utils.save_file import save_upload_file, delete_files

router = APIRouter(prefix="/organizations", tags=["Organizations"])

allow_only_manager = RoleChecker([RoleEnum.MANAGER])
allow_editor_or_manager = RoleChecker([RoleEnum.EDITOR, RoleEnum.MANAGER])


def get_organization_or_404(db: Session, organization_id: int) -> Organization:
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizace nenalezena"
        )
    return organization


def ensure_unique_name(db: Session, name: str, organization_id: int | None = None) -> None:
    existing = db.scalar(select(Organization).where(Organization.name == name))
    if existing and existing.id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organizace s tímto názvem již existuje"
        )


@router.get("/", response_model=List[OrganizationResponse])
async def get_organizations(db: Session = Depends(get_db)):
    """Vrátí seznam všech organizací."""
    return db.scalars(select(Organization).order_by(Organization.name)).all()


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(organization_id: int, db: Session = Depends(get_db)):
    """Vrátí detail organizace podle ID."""
    return get_organization_or_404(db, organization_id)


@router.get(
    "/{organization_id}/public",
    response_model=OrganizationPublicResponse,
    dependencies=[Depends(allow_editor_or_manager)]
)
async def get_organization_public_profile(organization_id: int, db: Session = Depends(get_db)):
    """
    Vrátí profil organizace se statistikami aukcí jejích skupin (jen pro editory a manažery).
    Výtěžek se dělí rovným dílem mezi všechny organizace, statistiky jsou tedy jen informativní.
    """
    organization = get_organization_or_404(db, organization_id)
    now = datetime.now(UTC)

    in_organization = Product.group_id.in_(
        select(Group.id).where(Group.organization_id == organization_id)
    )

    total_raised = db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0))
        .join(Product, Product.id == Order.product_id)
        .where(in_organization, Order.status == OrderStatus.PAID)
    )
    finished_auctions_count = db.scalar(
        select(func.count(Product.id)).where(in_organization, Product.status == Status.FINISHED)
    )
    active_auctions_count = db.scalar(
        select(func.count(Product.id)).where(
            in_organization,
            Product.status == Status.APPROVED,
            Product.starts_at <= now,
            Product.ends_at >= now,
        )
    )

    return OrganizationPublicResponse(
        id=organization.id,
        name=organization.name,
        description=organization.description,
        logo=organization.logo,
        total_raised=total_raised,
        finished_auctions_count=finished_auctions_count,
        active_auctions_count=active_auctions_count,
    )


@router.get("/{organization_id}/products", response_model=List[ProductResponse])
async def get_organization_products(
        organization_id: int,
        current_user: Annotated[User, Depends(allow_editor_or_manager)],
        db: Session = Depends(get_db),
):
    """Vrátí právě probíhající schválené aukce skupin přiřazených k organizaci (jen pro editory a manažery)."""
    get_organization_or_404(db, organization_id)
    now = datetime.now(UTC)

    products = db.scalars(
        select(Product)
        .join(Group, Group.id == Product.group_id)
        .where(
            Group.organization_id == organization_id,
            Product.status == Status.APPROVED,
            Product.starts_at <= now,
            Product.ends_at >= now,
        )
        .order_by(Product.ends_at)
    ).all()

    for product in products:
        is_followed = any(
            follow.follower_id == current_user.id for follow in product.followers
        )
        setattr(product, "is_followed", is_followed)

    return products


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_only_manager)]
)
async def create_organization(
        name: str = Form(..., min_length=1, max_length=100),
        description: str = Form("", max_length=5000),
        logo: Optional[UploadFile] = File(None, description="Logo organizace"),
        db: Session = Depends(get_db),
):
    """Vytvoří novou organizaci (volitelně s logem)."""
    ensure_unique_name(db, name)

    logo_path = None
    if logo and logo.filename:
        logo_path = save_upload_file(logo, get_settings().ORGANIZATION_UPLOAD_DIR)

    organization = Organization(name=name, description=description, logo=logo_path)
    try:
        db.add(organization)
        db.commit()
    except Exception:
        db.rollback()
        delete_files([logo_path])
        raise

    db.refresh(organization)
    return organization


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(allow_only_manager)]
)
async def update_organization(
        organization_id: int,
        name: str = Form(..., min_length=1, max_length=100),
        description: str = Form("", max_length=5000),
        logo: Optional[UploadFile] = File(None, description="Nové logo organizace"),
        remove_logo: bool = Form(False, description="Smaže stávající logo"),
        db: Session = Depends(get_db),
):
    """
    Upraví organizaci.
    Pokud je poskytnuto nové logo, nahradí staré. S remove_logo=true se logo odstraní.
    """
    organization = get_organization_or_404(db, organization_id)
    ensure_unique_name(db, name, organization_id)

    organization.name = name
    organization.description = description

    new_logo = None
    files_to_delete: list[str] = []
    if logo and logo.filename:
        new_logo = save_upload_file(logo, get_settings().ORGANIZATION_UPLOAD_DIR)
    if (new_logo or remove_logo) and organization.logo:
        files_to_delete.append(organization.logo)
    if new_logo or remove_logo:
        organization.logo = new_logo

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_files([new_logo])
        raise

    delete_files(files_to_delete)
    db.refresh(organization)
    return organization


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(allow_only_manager)]
)
async def delete_organization(organization_id: int, db: Session = Depends(get_db)):
    """Smaže organizaci. Nelze smazat organizaci, pod kterou ještě patří nějaká skupina."""
    organization = get_organization_or_404(db, organization_id)

    if organization.groups:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organizaci nelze smazat, protože pod ni patří skupiny."
        )

    logo = organization.logo
    db.delete(organization)
    db.commit()

    delete_files([logo])
    return None
