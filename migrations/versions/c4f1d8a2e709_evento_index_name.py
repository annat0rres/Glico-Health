"""Use a schema-unique index name for calendar events.

Revision ID: c4f1d8a2e709
Revises: d2e3f4a5b6c7
Create Date: 2026-11-16

"""
from alembic import op

revision = "c4f1d8a2e709"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "fk_evento_usuario_idx",
        "evento_calendario",
        ["id_usuario"],
        unique=False,
    )
    op.drop_index("fk_usuario_id_idx", table_name="evento_calendario")


def downgrade():
    op.create_index(
        "fk_usuario_id_idx",
        "evento_calendario",
        ["id_usuario"],
        unique=False,
    )
    op.drop_index("fk_evento_usuario_idx", table_name="evento_calendario")
