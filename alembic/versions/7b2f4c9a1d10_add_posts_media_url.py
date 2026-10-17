"""add posts.media_url

Revision ID: 7b2f4c9a1d10
Revises: 1e5629ac07d3
Create Date: 2026-10-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b2f4c9a1d10'
down_revision: Union[str, Sequence[str], None] = '1e5629ac07d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Algunas bases locales ya tienen la columna (creada antes de Alembic).
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("posts")}
    if "media_url" not in columns:
        op.add_column('posts', sa.Column('media_url', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('posts', 'media_url')
