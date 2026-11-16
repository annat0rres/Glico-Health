"""Create the application schema for PostgreSQL.

Revision ID: pg0001_baseline
Revises:
Create Date: 2026-11-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "pg0001_baseline"
down_revision = None
branch_labels = ("postgresql",)
depends_on = None


cuidador_tipo = postgresql.ENUM(
    "familiar", "profissional", name="cuidadortipocuidador", create_type=False
)
paciente_diabete = postgresql.ENUM(
    "tipo1", "tipo2", "gestacional", name="pacientetipodiabete", create_type=False
)
responsavel_status = postgresql.ENUM(
    "ativo",
    "desativado",
    "pendente",
    name="vinculoresponsavelpacientestatus",
    create_type=False,
)
estado_pessoal = postgresql.ENUM(
    "Jejum",
    "Pré-refeição",
    "Pós-refeição",
    "Sintomático",
    "Atividade física",
    "Antes de dormir",
    "Madrugada",
    "Outro",
    name="estadopessoal",
    create_type=False,
)
tipo_evento = postgresql.ENUM(
    "Consulta médica",
    "Exame",
    "Vacina",
    "Registro de glicemia",
    "Tomar medicação",
    "Outro",
    name="tipoevento",
    create_type=False,
)


def upgrade():
    bind = op.get_bind()
    for enum_type in (
        cuidador_tipo,
        paciente_diabete,
        responsavel_status,
        estado_pessoal,
        tipo_evento,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False),
        sa.Column("email", sa.String(length=64), nullable=True),
        sa.Column("passw_hash", sa.String(length=256), nullable=True),
        sa.Column("foto_perfil", sa.LargeBinary(), nullable=True),
        sa.Column("foto_perfil_tipo", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "cuidador",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("tipo_cuidador", cuidador_tipo, nullable=True),
        sa.Column("conselho_profissional", sa.String(length=10), nullable=True),
        sa.Column("registro_profissional", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id"], name="fk_usuario_cuidador"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "fk_usuario_cuidador_idx", "cuidador", ["id_usuario"], unique=False
    )
    op.create_table(
        "paciente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("nascimento", sa.Date(), nullable=True),
        sa.Column("genero", sa.CHAR(length=1), nullable=True),
        sa.Column("tipo_diabete", paciente_diabete, nullable=True),
        sa.Column("peso", sa.DECIMAL(precision=5, scale=1), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id"], name="fk_usuario_paciente"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "fk_usuario_paciente_idx", "paciente", ["id_usuario"], unique=False
    )
    op.create_table(
        "responsavel",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("responsabilidade", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id"], name="fk_usuario_responsavel"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "fk_usuario_responsavel_idx", "responsavel", ["id_usuario"], unique=False
    )
    op.create_table(
        "registro_glicemico",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("medida", sa.DECIMAL(precision=5, scale=1), nullable=False),
        sa.Column("data_registro", sa.Date(), nullable=False),
        sa.Column("hora_registro", sa.Time(), nullable=False),
        sa.Column("estado", estado_pessoal, nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id"], name="fk_usuario_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "fk_usuario_id_idx", "registro_glicemico", ["id_usuario"], unique=False
    )
    op.create_table(
        "vinculocuidador_paciente",
        sa.Column("id_cuidador", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column(
            "criado_por_cuidador",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("data_associacao", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'Pendente'"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["id_cuidador"], ["cuidador.id"], name="fk_cuidador_vinculo"
        ),
        sa.ForeignKeyConstraint(
            ["id_paciente"], ["paciente.id"], name="fk_cuidador_paciente"
        ),
        sa.PrimaryKeyConstraint("id_cuidador", "id_paciente"),
    )
    op.create_index(
        "fk_cuidador_paciente_idx",
        "vinculocuidador_paciente",
        ["id_paciente"],
        unique=False,
    )
    op.create_table(
        "vinculoresponsavel_paciente",
        sa.Column("id_responsavel", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("relacao", sa.String(length=30), nullable=True),
        sa.Column("status", responsavel_status, nullable=True),
        sa.Column(
            "criado_por_responsavel",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("data_associacao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_paciente"], ["paciente.id"], name="fk_paciente_responsavel"
        ),
        sa.ForeignKeyConstraint(
            ["id_responsavel"], ["responsavel.id"], name="fk_responsavel_vinculo"
        ),
        sa.PrimaryKeyConstraint("id_responsavel", "id_paciente"),
    )
    op.create_index(
        "fk_paciente_responsavel_idx",
        "vinculoresponsavel_paciente",
        ["id_paciente"],
        unique=False,
    )
    op.create_table(
        "evento_calendario",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("dia_resevado", sa.Date(), nullable=False),
        sa.Column("hora_resevada", sa.Time(), nullable=False),
        sa.Column("tipo_evento", tipo_evento, nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario.id"], name="fk_usuario_evento"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "fk_evento_usuario_idx", "evento_calendario", ["id_usuario"], unique=False
    )
    op.create_table(
        "leitura_temperatura",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("temperatura", sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column("data_hora", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_leitura_temperatura_data_hora",
        "leitura_temperatura",
        ["data_hora"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_leitura_temperatura_data_hora", table_name="leitura_temperatura"
    )
    op.drop_table("leitura_temperatura")
    op.drop_index("fk_evento_usuario_idx", table_name="evento_calendario")
    op.drop_table("evento_calendario")
    op.drop_index(
        "fk_paciente_responsavel_idx", table_name="vinculoresponsavel_paciente"
    )
    op.drop_table("vinculoresponsavel_paciente")
    op.drop_index("fk_cuidador_paciente_idx", table_name="vinculocuidador_paciente")
    op.drop_table("vinculocuidador_paciente")
    op.drop_index("fk_usuario_id_idx", table_name="registro_glicemico")
    op.drop_table("registro_glicemico")
    op.drop_index("fk_usuario_responsavel_idx", table_name="responsavel")
    op.drop_table("responsavel")
    op.drop_index("fk_usuario_paciente_idx", table_name="paciente")
    op.drop_table("paciente")
    op.drop_index("fk_usuario_cuidador_idx", table_name="cuidador")
    op.drop_table("cuidador")
    op.drop_table("usuario")

    bind = op.get_bind()
    for enum_type in (
        tipo_evento,
        estado_pessoal,
        responsavel_status,
        paciente_diabete,
        cuidador_tipo,
    ):
        enum_type.drop(bind, checkfirst=True)
