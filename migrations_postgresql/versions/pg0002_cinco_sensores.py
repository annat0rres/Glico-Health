"""adiciona os cinco sensores a leitura de temperatura

Revision ID: pg0002_cinco_sensores
Revises: pg0001_baseline
Create Date: 2026-11-17

"""
from alembic import op
import sqlalchemy as sa


revision = "pg0002_cinco_sensores"
down_revision = "pg0001_baseline"
branch_labels = ("postgresql",)
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
