"""Añade la URL pública de imagen a las publicaciones."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261017_media_url"
down_revision: str | None = "1e5629ac07d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("media_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("posts", "media_url")
