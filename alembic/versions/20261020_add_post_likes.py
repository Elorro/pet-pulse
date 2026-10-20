"""Create persistent likes for posts."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261020_post_likes"
down_revision: str | Sequence[str] | None = ("20261017_media_url", "7b2f4c9a1d10")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "post_likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("like_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["like_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "like_id", name="uq_post_likes_post_user"),
    )


def downgrade() -> None:
    op.drop_table("post_likes")
