from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9e621f6213ca"
down_revision = "23d5de443681"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "user",  # keep 'user' to match prod right now
        sa.Column("id", sa.Integer(), primary_key=True),
        # (add the real columns if you have them; this minimal table is enough for the FK)
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

def downgrade():
    op.drop_table("user")
