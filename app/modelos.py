from typing import Optional
import datetime
import enum

from sqlalchemy import Boolean, CHAR, Date, DateTime, Enum, ForeignKeyConstraint, Index, Integer, String, text, Text, Time, DECIMAL, LargeBinary
from app import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Base(db.Model):
    __abstract__ = True

class CuidadorTipoCuidador(str, enum.Enum):
    FAMILIAR = 'familiar'
    PROFISSIONAL = 'profissional'


class PacienteTipoDiabete(str, enum.Enum):
    TIPO1 = 'tipo1'
    TIPO2 = 'tipo2'
    GESTACIONAL = 'gestacional'


class VinculoresponsavelPacienteStatus(str, enum.Enum):
    ATIVO = 'ativo'
    DESATIVADO = 'desativado'
    PENDENTE = 'pendente'


class Usuario(Base):
    __tablename__ = 'usuario'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    remember_me: Mapped[bool] = mapped_column(Boolean, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    passw_hash: Mapped[Optional[str]] = mapped_column(String(256))
    foto_perfil: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    foto_perfil_tipo: Mapped[Optional[str]] = mapped_column(String(50))

    cuidador: Mapped[list['Cuidador']] = relationship('Cuidador', back_populates='usuario')
    paciente: Mapped[list['Paciente']] = relationship('Paciente', back_populates='usuario')
    responsavel: Mapped[list['Responsavel']] = relationship('Responsavel', back_populates='usuario')


class Cuidador(Base):
    __tablename__ = 'cuidador'
    __table_args__ = (
        ForeignKeyConstraint(['id_usuario'], ['usuario.id'], name='fk_usuario_cuidador'),
        Index('fk_usuario_cuidador_idx', 'id_usuario')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer)
    tipo_cuidador: Mapped[Optional[CuidadorTipoCuidador]] = mapped_column(Enum(CuidadorTipoCuidador, values_callable=lambda cls: [member.value for member in cls]))
    conselho_profissional: Mapped[Optional[str]] = mapped_column(String(10))
    registro_profissional: Mapped[Optional[str]] = mapped_column(String(20))

    usuario: Mapped['Usuario'] = relationship('Usuario', back_populates='cuidador')
    vinculocuidador_paciente: Mapped[list['VinculocuidadorPaciente']] = relationship('VinculocuidadorPaciente', back_populates='cuidador')


class Paciente(Base):
    __tablename__ = 'paciente'
    __table_args__ = (
        ForeignKeyConstraint(['id_usuario'], ['usuario.id'], name='fk_usuario_paciente'),
        Index('fk_usuario_paciente_idx', 'id_usuario')
    )

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer,nullable=False)
    nascimento: Mapped[Optional[datetime.date]] = mapped_column(Date)
    genero: Mapped[Optional[str]] = mapped_column(CHAR(1))
    tipo_diabete: Mapped[Optional[PacienteTipoDiabete]] = mapped_column(Enum(PacienteTipoDiabete, values_callable=lambda cls: [member.value for member in cls]))
    peso: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5,1))


    usuario: Mapped['Usuario'] = relationship('Usuario', back_populates='paciente')
    vinculocuidador_paciente: Mapped[list['VinculocuidadorPaciente']] = relationship('VinculocuidadorPaciente', back_populates='paciente')
    vinculoresponsavel_paciente: Mapped[list['VinculoresponsavelPaciente']] = relationship('VinculoresponsavelPaciente', back_populates='paciente')


class Responsavel(Base):
    __tablename__ = 'responsavel'
    __table_args__ = (
        ForeignKeyConstraint(['id_usuario'], ['usuario.id'], name='fk_usuario_responsavel'),
        Index('fk_usuario_responsavel_idx', 'id_usuario')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer)
    responsabilidade: Mapped[Optional[str]] = mapped_column(String(30))

    usuario: Mapped['Usuario'] = relationship('Usuario', back_populates='responsavel')
    vinculoresponsavel_paciente: Mapped[list['VinculoresponsavelPaciente']] = relationship('VinculoresponsavelPaciente', back_populates='responsavel')


class VinculocuidadorPaciente(Base):
    __tablename__ = 'vinculocuidador_paciente'
    __table_args__ = (
        ForeignKeyConstraint(['id_cuidador'], ['cuidador.id'], name='fk_cuidador_vinculo'),
        ForeignKeyConstraint(['id_paciente'], ['paciente.id'], name='fk_cuidador_paciente'),
        Index('fk_cuidador_paciente_idx', 'id_paciente')
    )

    id_cuidador: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True)
    criado_por_cuidador: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    data_associacao: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'Pendente'"))

    cuidador: Mapped['Cuidador'] = relationship('Cuidador', back_populates='vinculocuidador_paciente')
    paciente: Mapped['Paciente'] = relationship('Paciente', back_populates='vinculocuidador_paciente')


class VinculoresponsavelPaciente(Base):
    __tablename__ = 'vinculoresponsavel_paciente'
    __table_args__ = (
        ForeignKeyConstraint(['id_paciente'], ['paciente.id'], name='fk_paciente_responsavel'),
        ForeignKeyConstraint(['id_responsavel'], ['responsavel.id'], name='fk_responsavel_vinculo'),
        Index('fk_paciente_responsavel_idx', 'id_paciente')
    )

    id_responsavel: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True)
    relacao: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[Optional[VinculoresponsavelPacienteStatus]] = mapped_column(Enum(VinculoresponsavelPacienteStatus, values_callable=lambda cls: [member.value for member in cls]))
    criado_por_responsavel: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    data_associacao: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    paciente: Mapped['Paciente'] = relationship('Paciente', back_populates='vinculoresponsavel_paciente')
    responsavel: Mapped['Responsavel'] = relationship('Responsavel', back_populates='vinculoresponsavel_paciente')

class EstadoPessoal(str, enum.Enum):
    JEJUM = 'Jejum'
    PRE_REF = 'Pré-refeição'
    POS_REF = 'Pós-refeição'
    SINTOMATICO = 'Sintomático'
    EXERCICIO = 'Atividade física'
    ANTES_DORMIR = 'Antes de dormir'
    MADRUGADA = 'Madrugada'
    OUTRO = 'Outro'

class registro_glicemico(Base):
    __tablename__ = 'registro_glicemico'
    __table_args__ = (
        ForeignKeyConstraint(['id_usuario'], ['usuario.id'], name='fk_usuario_id'),
        Index('fk_evento_usuario_idx', 'id_usuario')
    )

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer,nullable=False)
    medida: Mapped[DECIMAL] = mapped_column(DECIMAL(5,1))
    data_registro: Mapped[Date] = mapped_column(Date)
    hora_registro: Mapped[Time] = mapped_column(Time)
    estado: Mapped[Optional[EstadoPessoal]] = mapped_column(Enum(EstadoPessoal, values_callable=lambda cls: [member.value for member in cls]))


class tipoEvento(str, enum.Enum):
    CONSULTA = 'Consulta médica'
    EXAME = 'Exame'
    VACINA = 'Vacina'
    GLICEMIA = 'Registro de glicemia'
    MEDICACAO = 'Tomar medicação'
    OUTRO = 'Outro'

class evento_calendario(Base):
    __tablename__ = 'evento_calendario'
    __table_args__ = (
        ForeignKeyConstraint(['id_usuario'], ['usuario.id'], name='fk_usuario_evento'),
        Index('fk_usuario_id_idx', 'id_usuario')
    )

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer,nullable=False)
    titulo: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    dia_resevado: Mapped[Date] = mapped_column(Date)
    hora_resevada: Mapped[Time] = mapped_column(Time)
    tipo_evento: Mapped[Optional[tipoEvento]] = mapped_column(Enum(tipoEvento, values_callable=lambda cls: [member.value for member in cls]))


class LeituraTemperatura(Base):
    __tablename__ = 'leitura_temperatura'
    __table_args__ = (
        Index('ix_leitura_temperatura_data_hora', 'data_hora'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    temperatura: Mapped[DECIMAL] = mapped_column(DECIMAL(5, 2), nullable=False)
    dedao: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5, 2))
    metatarso_3: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5, 2))
    metatarso_5: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5, 2))
    meio_pe: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5, 2))
    calcanhar: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(5, 2))
    data_hora: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
