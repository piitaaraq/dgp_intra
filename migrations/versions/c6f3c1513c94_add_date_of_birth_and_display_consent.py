"""Add date of birth and display consent

Revision ID: c6f3c1513c94
Revises: e720624089a4
Create Date: 2025-10-07 14:57:20.630270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'c6f3c1513c94'
down_revision: Union[str, None] = 'e720624089a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('user', sa.Column('dob', sa.Date(), nullable=True))
    op.add_column('user', sa.Column('pub_dob', sa.Boolean(), nullable=False, server_default=sa.false()))
    # optional: if Alembic created an index for dob and you want it:
    op.create_index('ix_user_dob', 'user', ['dob'])

def downgrade():
    # if you created the index above:
    op.drop_index('ix_user_dob', table_name='user')
    op.drop_column('user', 'pub_dob')
    op.drop_column('user', 'dob')
