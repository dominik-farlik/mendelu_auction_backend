"""seed lookup tables

Revision ID: 5e1f09dd5566
Revises: 037ee1b4f7b4
Create Date: 2026-10-18 19:17:13.845147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from config import get_settings
from routers.auth import get_password_hash

settings = get_settings()


# revision identifiers, used by Alembic.
revision: str = '5e1f09dd5566'
down_revision: Union[str, Sequence[str], None] = '037ee1b4f7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    role = sa.table(
        "role",
        sa.column("name", sa.String),
    )
    op.bulk_insert(role, [
        {"name": "viewer"},
        {"name": "editor"},
        {"name": "manager"},
    ])

    user = sa.table(
        "user",
        sa.column("first_name", sa.String),
        sa.column("last_name", sa.String),
        sa.column("username", sa.String),
        sa.column("email", sa.String),
        sa.column("password", sa.String),
        sa.column("role_id", sa.Integer),
        sa.column("is_verified", sa.Boolean),
        sa.column("public_last_name", sa.Boolean),
    )
    op.bulk_insert(user, [
        {
            "first_name": "admin",
            "last_name": "admin",
            "username": "admin",
            "email": settings.ADMIN_EMAIL,
            "password": get_password_hash(settings.ADMIN_PASSWORD),
            "role_id": 3,
            "is_verified": True,
            "public_last_name": True,
        },
    ])


def downgrade() -> None:
    """Downgrade schema."""
    pass
