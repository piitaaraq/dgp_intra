"""Add room management system and user roles

Revision ID: 5101a32a0d0e
Revises: 4271e9aed2d0
Create Date: 2025-12-10 12:18:37.886217
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5101a32a0d0e'
down_revision: Union[str, None] = '4271e9aed2d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create rooms table
    op.create_table('rooms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('room_number', sa.String(length=10), nullable=False),
    sa.Column('floor', sa.Integer(), nullable=False),
    sa.Column('patient_count', sa.Integer(), nullable=True),
    sa.Column('relative_count', sa.Integer(), nullable=True),
    sa.Column('cleaning_status', sa.Enum('CLEAN', 'NEEDS_CLEANING', name='cleaningstatus'), nullable=True),
    sa.Column('last_cleaned_at', sa.DateTime(), nullable=True),
    sa.Column('last_cleaned_by_id', sa.Integer(), nullable=True),
    sa.Column('last_occupancy_change', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['last_cleaned_by_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rooms_room_number'), ['room_number'], unique=True)
    
    # Create cleaning_logs table
    op.create_table('cleaning_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.Integer(), nullable=False),
    sa.Column('cleaned_by_id', sa.Integer(), nullable=False),
    sa.Column('cleaned_at', sa.DateTime(), nullable=False),
    sa.Column('status_before', sa.Enum('CLEAN', 'NEEDS_CLEANING', name='cleaningstatus'), nullable=False),
    sa.Column('status_after', sa.Enum('CLEAN', 'NEEDS_CLEANING', name='cleaningstatus'), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['cleaned_by_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Add role column to user table with default
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('role', 
                     sa.Enum('STAFF', 'KITCHEN', 'PATIENT_ADMIN', 'CLEANING', 'ADMIN', name='userrole'), 
                     nullable=False,
                     server_default='STAFF')
        )
    
    # Set Peter as ADMIN (replace with your actual email)
    op.execute("""
        UPDATE user 
        SET role = 'ADMIN' 
        WHERE email = 'ploe@peqqik.gl'
    """)
    
    # Set other is_admin users as KITCHEN
    op.execute("""
        UPDATE user 
        SET role = 'KITCHEN' 
        WHERE is_admin = 1 AND email != 'ploe@peqqik.gl'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('role')
    
    op.drop_table('cleaning_logs')
    
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rooms_room_number'))
    
    op.drop_table('rooms')