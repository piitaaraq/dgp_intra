"""Merging heads

Revision ID: c5ef529f6e17
Revises: 5472d4cb54fc, da7df8c6994f
Create Date: 2025-09-03 14:34:19.032960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5ef529f6e17'
down_revision: Union[str, None] = ('5472d4cb54fc', 'da7df8c6994f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
