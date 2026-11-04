"""move organization to own table

Revision ID: b7c2e4a91f30
Revises: 5e1f09dd5566
Create Date: 2026-11-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c2e4a91f30'
down_revision: Union[str, Sequence[str], None] = '5e1f09dd5566'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('organization',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('logo', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_name'), 'organization', ['name'], unique=True)

    op.add_column('group', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_group_organization_id'), 'group', ['organization_id'], unique=False)
    op.create_foreign_key(
        'fk_group_organization_id_organization', 'group', 'organization',
        ['organization_id'], ['id'], ondelete='SET NULL'
    )

    # Převod existujících textových hodnot na záznamy v nové tabulce.
    op.execute("""
        INSERT INTO organization (name, description)
        SELECT DISTINCT TRIM(organization), ''
        FROM "group"
        WHERE organization IS NOT NULL AND TRIM(organization) <> ''
    """)
    op.execute("""
        UPDATE "group" AS g
        SET organization_id = o.id
        FROM organization AS o
        WHERE TRIM(g.organization) = o.name
    """)

    op.drop_column('group', 'organization')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('group', sa.Column('organization', sa.String(length=50), nullable=True))
    op.execute("""
        UPDATE "group" AS g
        SET organization = LEFT(o.name, 50)
        FROM organization AS o
        WHERE g.organization_id = o.id
    """)

    op.drop_constraint('fk_group_organization_id_organization', 'group', type_='foreignkey')
    op.drop_index(op.f('ix_group_organization_id'), table_name='group')
    op.drop_column('group', 'organization_id')
    op.drop_index(op.f('ix_organization_name'), table_name='organization')
    op.drop_table('organization')
