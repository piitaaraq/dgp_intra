"""Merge spliced user-table branch into main

Revision ID: e720624089a4
Revises: 18b89cf348e8, 9e621f6213ca
Create Date: 2025-09-08 11:26:11.940161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e720624089a4'
down_revision: Union[str, None] = ('18b89cf348e8', '9e621f6213ca')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
