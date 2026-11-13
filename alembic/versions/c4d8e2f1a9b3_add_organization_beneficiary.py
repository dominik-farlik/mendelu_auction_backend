"""add organization beneficiary and short description

Revision ID: c4d8e2f1a9b3
Revises: b7c2e4a91f30
Create Date: 2026-11-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e2f1a9b3'
down_revision: Union[str, Sequence[str], None] = 'b7c2e4a91f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Obě pole jsou volitelná, existující organizace zůstanou platné a texty se doplní v administraci.
    op.add_column('organization', sa.Column('beneficiary_name', sa.String(length=100), nullable=True))
    op.add_column('organization', sa.Column('short_description', sa.String(length=300), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organization', 'short_description')
    op.drop_column('organization', 'beneficiary_name')
