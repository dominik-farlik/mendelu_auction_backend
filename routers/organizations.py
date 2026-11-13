from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from dependencies import RoleChecker
from models import Organization
from models.organization import OrganizationResponse
from models.role import RoleEnum
from utils.save_file import save_upload_file, delete_files

router = APIRouter(prefix="/organizations", tags=["Organizations"])

allow_only_manager = RoleChecker([RoleEnum.MANAGER])


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


def empty_to_none(value: str) -> str | None:
    value = value.strip()
    return value or None


@router.get("/", response_model=List[OrganizationResponse])
async def get_organizations(db: Session = Depends(get_db)):
    """Vrátí seznam všech organizací."""
    return db.scalars(select(Organization).order_by(Organization.name)).all()


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(organization_id: int, db: Session = Depends(get_db)):
    """Vrátí detail organizace podle ID (veřejné, pro stránku organizace)."""
    return get_organization_or_404(db, organization_id)


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_only_manager)]
)
async def create_organization(
        name: str = Form(..., min_length=1, max_length=100),
        beneficiary_name: str = Form("", max_length=100),
        short_description: str = Form("", max_length=300),
        description: str = Form("", max_length=5000),
        logo: Optional[UploadFile] = File(None, description="Logo organizace"),
        db: Session = Depends(get_db),
):
    """Vytvoří novou organizaci (volitelně s logem)."""
    ensure_unique_name(db, name)

    logo_path = None
    if logo and logo.filename:
        logo_path = save_upload_file(logo, get_settings().ORGANIZATION_UPLOAD_DIR)

    organization = Organization(
        name=name,
        beneficiary_name=empty_to_none(beneficiary_name),
        short_description=empty_to_none(short_description),
        description=description,
        logo=logo_path,
    )
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
        beneficiary_name: str = Form("", max_length=100),
        short_description: str = Form("", max_length=300),
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
    organization.beneficiary_name = empty_to_none(beneficiary_name)
    organization.short_description = empty_to_none(short_description)
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
