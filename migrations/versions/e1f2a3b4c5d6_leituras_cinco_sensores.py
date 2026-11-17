"""adiciona os cinco sensores a leitura de temperatura

Revision ID: e1f2a3b4c5d6
Revises: c4f1d8a2e709
Create Date: 2026-11-17

"""
from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "c4f1d8a2e709"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("leitura_temperatura", sa.Column("dedao", sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column("leitura_temperatura", sa.Column("metatarso_3", sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column("leitura_temperatura", sa.Column("metatarso_5", sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column("leitura_temperatura", sa.Column("meio_pe", sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column("leitura_temperatura", sa.Column("calcanhar", sa.DECIMAL(precision=5, scale=2), nullable=True))


def downgrade():
    op.drop_column("leitura_temperatura", "calcanhar")
    op.drop_column("leitura_temperatura", "meio_pe")
    op.drop_column("leitura_temperatura", "metatarso_5")
    op.drop_column("leitura_temperatura", "metatarso_3")
    op.drop_column("leitura_temperatura", "dedao")
