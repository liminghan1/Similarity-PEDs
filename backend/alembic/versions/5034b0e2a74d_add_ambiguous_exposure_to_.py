"""add ambiguous_exposure to useclassification enum

Revision ID: 5034b0e2a74d
Revises: 656a21183cb0
Create Date: 2026-09-03 19:26:11.705259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5034b0e2a74d'
down_revision: Union[str, None] = '656a21183cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alembic autogenerate cannot detect a new value added to a native Postgres ENUM type (a
    # known SQLAlchemy/Alembic limitation), so this was written by hand rather than generated --
    # see backend/app/models/faers.py::UseClassification.AMBIGUOUS_EXPOSURE for why this value
    # exists (pipelines/faers/classification.py v2's two-tier misuse-evidence redesign).
    # `IF NOT EXISTS` makes this safe to re-run; Postgres 12+ allows ADD VALUE inside a
    # transaction as long as the new value isn't used in the same transaction (it isn't here).
    op.execute("ALTER TYPE useclassification ADD VALUE IF NOT EXISTS 'AMBIGUOUS_EXPOSURE'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing a value requires recreating the enum
    # type (drop dependent default/column, create a new type, cast the column, drop the old
    # type) -- not implemented here since nothing in this project's downgrade path has ever
    # needed to actually reverse past this revision; if that changes, do the recreate-and-cast
    # dance rather than leaving stale AMBIGUOUS_EXPOSURE rows with a type that claims not to
    # support them.
    pass
