from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4

from app import db
from datetime import date 
from flask import session
from app.modelos import (
    Usuario,
    Paciente,
    Cuidador,
    Responsavel,
    VinculocuidadorPaciente,
    VinculoresponsavelPaciente,
    VinculoresponsavelPacienteStatus,
    EstadoPessoal,
    registro_glicemico as RegistroGlicemico,
    evento_calendario as EventoCalendario,
    tipoEvento,
)
from sqlalchemy import select
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

class UsuarioController:
    PAPEIS = {
        "paciente": "Paciente",
        "cuidador": "Cuidador",
        "responsavel": "Responsável",
    }

    @staticmethod
    def email_em_uso(email, excluir_usuario_id=None):
        email_normalizado = (email or "").strip().casefold()
        if not email_normalizado:
            return False

        consulta = select(Usuario.id).where(
            sa.func.lower(sa.func.trim(Usuario.email)) == email_normalizado
        )
        if excluir_usuario_id is not None:
            consulta = consulta.where(Usuario.id != excluir_usuario_id)
        return db.session.scalars(consulta).first() is not None

    @staticmethod
    def listar_papeis_usuario():
        usuario_id = session.get("usuario_id")
        if not usuario_id:
            return []

        papeis = []
        verificacoes = (
            ("paciente", Paciente),
            ("cuidador", Cuidador),
            ("responsavel", Responsavel),
        )
        for papel, modelo in verificacoes:
            if db.session.scalars(
                select(modelo.id).where(modelo.id_usuario == usuario_id)
            ).first() is not None:
                papeis.append(papel)
        return papeis

    @staticmethod
    def obter_papel_ativo():
        papeis = UsuarioController.listar_papeis_usuario()
        papel_ativo = session.get("papel_ativo")
        if papel_ativo not in papeis:
            papel_ativo = papeis[0] if papeis else None
            if papel_ativo:
                session["papel_ativo"] = papel_ativo
            else:
                session.pop("papel_ativo", None)
        return papel_ativo

    @staticmethod
    def selecionar_papel(papel):
        if papel not in UsuarioController.listar_papeis_usuario():
            return False

        session["papel_ativo"] = papel
        session.pop("paciente_visualizado_id", None)
        return True

    @staticmethod
    def associar_paciente(email, relacao=None):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return "error"

            papel_ativo = UsuarioController.obter_papel_ativo()
            cuidador = UsuarioController.buscar_cuidador_login() if papel_ativo == "cuidador" else None
            responsavel = UsuarioController.buscar_responsavel_login() if papel_ativo == "responsavel" else None
            paciente = db.session.scalars(
                select(Paciente)
                .join(Usuario, Paciente.id_usuario == Usuario.id)
                .where(sa.func.lower(Usuario.email) == email.strip().lower())
            ).first()

            if not paciente:
                return "not_found"
            if not cuidador and not responsavel:
                return "error"

            if responsavel:
                relacoes_validas = {"Pai", "Mãe", "Tia", "Tio", "Avó", "Avô", "Outro"}
                if relacao not in relacoes_validas:
                    return "invalid_relation"

            if cuidador:
                vinculo_cuidador = db.session.get(
                    VinculocuidadorPaciente,
                    (cuidador.id, paciente.id),
                )
                if not vinculo_cuidador:
                    db.session.add(
                        VinculocuidadorPaciente(
                            id_cuidador=cuidador.id,
                            id_paciente=paciente.id,
                            criado_por_cuidador=True,
                            data_associacao=datetime.now(),
                            status="Pendente",
                        )
                    )

            if responsavel:
                vinculo_responsavel = db.session.get(
                    VinculoresponsavelPaciente,
                    (responsavel.id, paciente.id),
                )
                if vinculo_responsavel:
                    vinculo_responsavel.relacao = relacao
                    vinculo_responsavel.status = VinculoresponsavelPacienteStatus.ATIVO
                else:
                    db.session.add(
                        VinculoresponsavelPaciente(
                            id_responsavel=responsavel.id,
                            id_paciente=paciente.id,
                            relacao=relacao,
                            status=VinculoresponsavelPacienteStatus.ATIVO,
                            criado_por_responsavel=True,
                            data_associacao=datetime.now(),
                        )
                    )

            db.session.commit()
            session["paciente_visualizado_id"] = paciente.id
            if responsavel:
                session["relacao_responsavel"] = relacao
            return "success"
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao associar paciente: {e}")
            return "error"

    @staticmethod
    def listar_pacientes_cuidados():
        usuario_id = session.get('usuario_id')
        cuidador = db.session.scalars(
            select(Cuidador).where(Cuidador.id_usuario == usuario_id)
        ).first() if usuario_id else None
        if not cuidador:
            return []

        pacientes_vinculados = db.session.execute(
            select(Paciente, Usuario)
            .join(Usuario, Paciente.id_usuario == Usuario.id)
            .join(
                VinculocuidadorPaciente,
                VinculocuidadorPaciente.id_paciente == Paciente.id,
            )
            .where(VinculocuidadorPaciente.id_cuidador == cuidador.id)
            .order_by(Usuario.name)
        ).all()
        return [
            {
                "id": paciente.id,
                "usuario_id": usuario.id,
                "nome": usuario.name,
                "email": usuario.email or "",
            }
            for paciente, usuario in pacientes_vinculados
        ]

    @staticmethod
    def listar_pacientes_responsavel():
        usuario_id = session.get('usuario_id')
        responsavel = db.session.scalars(
            select(Responsavel).where(Responsavel.id_usuario == usuario_id)
        ).first() if usuario_id else None
        if not responsavel:
            return []

        pacientes_vinculados = db.session.execute(
            select(Paciente, Usuario, VinculoresponsavelPaciente)
            .join(Usuario, Paciente.id_usuario == Usuario.id)
            .join(
                VinculoresponsavelPaciente,
                VinculoresponsavelPaciente.id_paciente == Paciente.id,
            )
            .where(VinculoresponsavelPaciente.id_responsavel == responsavel.id)
            .order_by(Usuario.name)
        ).all()
        return [
            {
                "id": paciente.id,
                "usuario_id": usuario.id,
                "nome": usuario.name,
                "email": usuario.email or "",
                "relacao": vinculo.relacao or "Não informada",
                "status": getattr(vinculo.status, "value", vinculo.status) or "pendente",
            }
            for paciente, usuario, vinculo in pacientes_vinculados
        ]

    @staticmethod
    def listar_pacientes_acompanhados(papel=None):
        papel = papel or UsuarioController.obter_papel_ativo()
        if papel == "cuidador":
            pacientes_vinculados = UsuarioController.listar_pacientes_cuidados()
        elif papel == "responsavel":
            pacientes_vinculados = UsuarioController.listar_pacientes_responsavel()
        else:
            return []

        pacientes = {
            paciente["id"]: paciente
            for paciente in pacientes_vinculados
            if paciente.get("status") != VinculoresponsavelPacienteStatus.DESATIVADO.value
        }
        return sorted(pacientes.values(), key=lambda paciente: paciente["nome"].casefold())

    @staticmethod
    def selecionar_paciente_cuidado(paciente_id):
        paciente = next(
            (p for p in UsuarioController.listar_pacientes_acompanhados() if p["id"] == paciente_id),
            None,
        )
        if not paciente:
            return None

        session["paciente_visualizado_id"] = paciente["id"]
        return paciente

    @staticmethod
    def desativar_vinculo_responsavel(paciente_id):
        try:
            if UsuarioController.obter_papel_ativo() != "responsavel":
                return False
            responsavel = UsuarioController.buscar_responsavel_login()
            if not responsavel:
                return False

            vinculo = db.session.get(
                VinculoresponsavelPaciente,
                (responsavel.id, paciente_id),
            )
            if not vinculo or vinculo.status == VinculoresponsavelPacienteStatus.DESATIVADO:
                return False

            vinculo.status = VinculoresponsavelPacienteStatus.DESATIVADO
            db.session.commit()
            if session.get("paciente_visualizado_id") == paciente_id:
                session.pop("paciente_visualizado_id", None)
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao desativar vínculo do responsável: {e}")
            return False

    @staticmethod
    def salvar_responsabilidade(tipo_responsavel):
        try:
            usuario_id = session.get("usuario_id")
            if not usuario_id or tipo_responsavel not in {"menor_idade", "curatelado"}:
                return False

            responsavel = UsuarioController.buscar_responsavel_login()
            if not responsavel:
                return False

            responsavel.responsabilidade = tipo_responsavel
            db.session.commit()
            session["tipo_responsavel"] = tipo_responsavel
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar responsabilidade: {e}")
            return False

    @staticmethod
    def cadastro(formCadastro):
        email = (formCadastro.email.data or "").strip()
        if UsuarioController.email_em_uso(email):
            return False

        usuario = Usuario(
            name=formCadastro.name.data,
            username=formCadastro.username.data,
            email=email,
            passw_hash=generate_password_hash(formCadastro.password.data),
            remember_me=False
        )

        db.session.add(usuario)
        db.session.commit()
    
        session['usuario_id'] = usuario.id

        print("O usuario {} ({}) - {} fez o cadastro".format(
            formCadastro.name.data,
            formCadastro.username.data,
            formCadastro.email.data
        ))
        
        return True

    @staticmethod
    def salvar_papeis(lista_papeis):
        try:
            usuario_id = session.get('usuario_id')

            if not usuario_id:
                print("Erro: Nenhum usuário encontrado na sessão.")
                return False

            # Busca o usuário
            usuario_atual = db.session.get(Usuario, usuario_id)

            if not usuario_atual:
                print("Erro: Usuário não encontrado no banco de dados.")
                return False

            # Salva os papéis através dos relacionamentos
            for papel in lista_papeis:

                if papel == "paciente":
                    db.session.add(
                        Paciente(id_usuario=usuario_id)
                    )

                elif papel == "cuidador":
                    db.session.add(
                        Cuidador(id_usuario=usuario_id, tipo_cuidador=None)  # Inicialmente sem tipo definido
                    )

                elif papel == "responsavel":
                    db.session.add(
                        Responsavel(id_usuario=usuario_id)
                    )

            db.session.commit()

            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar papéis no banco: {e}")
            return False

    @staticmethod
    def salvar_questionario_paciente(form_paciente):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                print("Erro: Nenhum usuário encontrado na sessão.")
                return False

            # Busca o questionário existente para atualizar
            questionario = db.session.scalars(select(Paciente).where(Paciente.id_usuario == usuario_id)).first()
            
            if not questionario:
                print("Erro: Questionário não encontrado para o usuário.")
                return False

            # Atualiza os dados do questionário
            # Dados da data de nascimento
            dia = int(form_paciente.dia.data)
            mes = int(form_paciente.mes.data)
            ano = int(form_paciente.ano.data)

            questionario.nascimento = date(
                ano,
                mes,
                dia
            )
            generos = {
                "masculino": "M",
                "feminino": "F",
                "outro": "O"
            }

            questionario.genero = generos.get(
                form_paciente.sexo.data
            )

            tipos_diabetes = {
                "tipo_1": "tipo1",
                "tipo_2": "tipo2",
                "gestacional": "gestacional"
            }

            questionario.tipo_diabete = tipos_diabetes.get(
                form_paciente.tipo_diabetes.data
            )

            db.session.commit()

            print(f"Questionário do paciente {usuario_id} salvo com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar questionário do paciente: {e}")
            return False

    @staticmethod
    def cadastrar_paciente_acompanhado(form_paciente, nome):
        try:
            papel_ativo = UsuarioController.obter_papel_ativo()
            cuidador = UsuarioController.buscar_cuidador_login() if papel_ativo == "cuidador" else None
            responsavel = UsuarioController.buscar_responsavel_login() if papel_ativo == "responsavel" else None
            if not nome or not cuidador and not responsavel:
                return False

            relacao = session.get("relacao_responsavel")
            if responsavel and relacao not in {"Pai", "Mãe", "Tia", "Tio", "Avó", "Avô", "Outro"}:
                return False

            usuario_paciente = Usuario(
                name=nome,
                username=f"paciente-{uuid4().hex}",
                remember_me=False,
            )
            db.session.add(usuario_paciente)
            db.session.flush()

            paciente = Paciente(id_usuario=usuario_paciente.id)
            dia = int(form_paciente.dia.data)
            mes = int(form_paciente.mes.data)
            ano = int(form_paciente.ano.data)
            paciente.nascimento = date(ano, mes, dia)
            paciente.genero = {
                "masculino": "M",
                "feminino": "F",
                "outro": "O",
            }.get(form_paciente.sexo.data)
            paciente.tipo_diabete = {
                "tipo_1": "tipo1",
                "tipo_2": "tipo2",
                "gestacional": "gestacional",
            }.get(form_paciente.tipo_diabetes.data)
            db.session.add(paciente)
            db.session.flush()

            if cuidador:
                db.session.add(
                    VinculocuidadorPaciente(
                        id_cuidador=cuidador.id,
                        id_paciente=paciente.id,
                        criado_por_cuidador=True,
                        data_associacao=datetime.now(),
                        status="Pendente",
                    )
                )
            else:
                db.session.add(
                    VinculoresponsavelPaciente(
                        id_responsavel=responsavel.id,
                        id_paciente=paciente.id,
                        relacao=relacao,
                        status=VinculoresponsavelPacienteStatus.ATIVO,
                        criado_por_responsavel=True,
                        data_associacao=datetime.now(),
                    )
                )

            db.session.commit()
            session["paciente_visualizado_id"] = paciente.id
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar paciente acompanhado: {e}")
            return False

    @staticmethod
    def salvar_tipo_cuidador(tipo_cuidador):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                print("Erro: Nenhum usuário encontrado na sessão.")
                return False

            # Busca o cuidador existente para atualizar
            cuidador = db.session.scalars(select(Cuidador).where(Cuidador.id_usuario == usuario_id)).first()
            
            if not cuidador:
                print("Erro: Cuidador não encontrado para o usuário.")
                return False

            # Atualiza o tipo de cuidador
            cuidador.tipo_cuidador = tipo_cuidador

            db.session.commit()

            print(f"Tipo de cuidador do usuário {usuario_id} salvo com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar tipo de cuidador: {e}")
            return False

    @staticmethod
    def salvar_dados_profissional(conselho_profissional, registro_profissional):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                print("Erro: Nenhum usuário encontrado na sessão.")
                return False

            # Busca o cuidador existente para atualizar
            cuidador = db.session.scalars(select(Cuidador).where(Cuidador.id_usuario == usuario_id)).first()
            
            if not cuidador:
                print("Erro: Cuidador não encontrado para o usuário.")
                return False

            # Atualiza os dados profissionais
            cuidador.conselho_profissional = conselho_profissional
            cuidador.registro_profissional = registro_profissional

            db.session.commit()

            print(f"Dados profissionais do cuidador {usuario_id} salvos com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar dados profissionais: {e}")
            return False

    @staticmethod
    def atualizar_perfil(nome, email, peso, genero=None, tipo_diabete=None, foto=None):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return False, "Sua sessão expirou. Faça login novamente."

            usuario = db.session.get(Usuario, usuario_id)
            paciente = db.session.scalars(
                select(Paciente).where(Paciente.id_usuario == usuario_id)
            ).first()

            if not usuario:
                return False, "Usuário não encontrado."
            if not paciente:
                return False, "Dados do paciente não encontrados."
            if not nome or not nome.strip() or not email or not email.strip():
                return False, "Nome e email são obrigatórios."
            if UsuarioController.email_em_uso(email, usuario_id):
                return False, "Este e-mail já está cadastrado em outra conta."

            if peso and peso.strip():
                valor_peso = Decimal(peso.replace(',', '.'))
                if valor_peso <= 0:
                    return False, "O peso deve ser maior que zero."
            else:
                valor_peso = None

            usuario.name = nome.strip()
            usuario.email = email.strip().lower()
            paciente.peso = valor_peso

            if genero in {"M", "F", "O"}:
                paciente.genero = genero
            if tipo_diabete in {"tipo1", "tipo2", "gestacional"}:
                paciente.tipo_diabete = tipo_diabete

            print("FOTO:", foto)
            print("FILENAME:", foto.filename if foto else None)
            print("MIMETYPE:", foto.mimetype if foto else None)
            
            if foto and foto.filename:
                usuario.foto_perfil = foto.read()
                usuario.foto_perfil_tipo = foto.mimetype

            db.session.commit()
            return True, "Perfil atualizado com sucesso!"
        except (ValueError, ArithmeticError):
            db.session.rollback()
            return False, "Informe um peso válido."
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar perfil: {e}")
            return False, "Não foi possível atualizar o perfil."

    @staticmethod
    def buscar_usuario_login(): #função que faz a busca pelo usuário
        usuario_id = session.get('usuario_id')

        if not usuario_id:
            print ("Erro: Nenhum usuário encontrado.")
            return None 

        usuario = db.session.get(Usuario, usuario_id)

        if not usuario:
            print("Erro: Nenhum usuário cadastrado no banco de dados.")
            return None

        return usuario 

    @staticmethod
    def buscar_cuidador_login():
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return None
        return db.session.scalars(
            select(Cuidador).where(Cuidador.id_usuario == usuario_id)
        ).first()

    @staticmethod
    def buscar_responsavel_login():
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return None
        return db.session.scalars(
            select(Responsavel).where(Responsavel.id_usuario == usuario_id)
        ).first()

    @staticmethod
    def atualizar_perfil_cuidador(nome, email, conselho, registro, foto=None):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return False, "Sua sessão expirou. Faça login novamente."

            usuario = db.session.get(Usuario, usuario_id)
            cuidador = UsuarioController.buscar_cuidador_login()
            if not usuario or not cuidador:
                return False, "Dados do cuidador não encontrados."
            if not nome or not nome.strip() or not email or not email.strip():
                return False, "Nome e email são obrigatórios."
            if UsuarioController.email_em_uso(email, usuario_id):
                return False, "Este e-mail já está cadastrado em outra conta."
            usuario.name = nome.strip()
            usuario.email = email.strip().lower()
            if conselho and registro:
                cuidador.conselho_profissional = conselho.strip()
                cuidador.registro_profissional = registro.strip().upper()
            if foto and foto.filename:
                usuario.foto_perfil = foto.read()
                usuario.foto_perfil_tipo = foto.mimetype

            db.session.commit()
            return True, "Perfil atualizado com sucesso!"
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar perfil do cuidador: {e}")
            return False, "Não foi possível atualizar o perfil."

    @staticmethod
    def atualizar_perfil_responsavel(nome, email, foto=None):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return False, "Sua sessão expirou. Faça login novamente."

            usuario = db.session.get(Usuario, usuario_id)
            responsavel = UsuarioController.buscar_responsavel_login()
            if not usuario or not responsavel:
                return False, "Dados do responsável não encontrados."
            if not nome or not nome.strip() or not email or not email.strip():
                return False, "Nome e email são obrigatórios."
            if UsuarioController.email_em_uso(email, usuario_id):
                return False, "Este e-mail já está cadastrado em outra conta."

            usuario.name = nome.strip()
            usuario.email = email.strip().lower()
            if foto and foto.filename:
                usuario.foto_perfil = foto.read()
                usuario.foto_perfil_tipo = foto.mimetype

            db.session.commit()
            return True, "Perfil atualizado com sucesso!"
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao atualizar perfil do responsável: {e}")
            return False, "Não foi possível atualizar o perfil."

    @staticmethod
    def buscar_registros_glicemia_login(usuario_id=None):
        usuario_id = usuario_id or session.get('usuario_id')
        if not usuario_id:
            return []

        registros = db.session.scalars(
            select(RegistroGlicemico)
            .where(RegistroGlicemico.id_usuario == usuario_id)
            .order_by(RegistroGlicemico.data_registro, RegistroGlicemico.hora_registro)
        ).all()

        return [
            {
                "data": registro.data_registro.isoformat(),
                "hora": registro.hora_registro.strftime("%H:%M"),
                "medida": float(registro.medida),
            }
            for registro in registros
        ]

    @staticmethod
    def buscar_eventos_calendario_login():
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return []

        eventos = db.session.scalars(
            select(EventoCalendario)
            .where(EventoCalendario.id_usuario == usuario_id)
            .order_by(EventoCalendario.dia_resevado, EventoCalendario.hora_resevada)
        ).all()

        return [
            {
                "id": evento.id,
                "title": evento.titulo,
                "start": (
                    f"{evento.dia_resevado.isoformat()}T"
                    f"{evento.hora_resevada.strftime('%H:%M')}"
                ),
                "description": evento.descricao or "",
                "tipo": evento.tipo_evento.value if evento.tipo_evento else "",
            }
            for evento in eventos
        ]

    @staticmethod
    def criar_evento_calendario(titulo, descricao, data_evento, hora_evento, tipo):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id or not titulo or not data_evento or not hora_evento:
                return False

            evento = EventoCalendario(
                id_usuario=usuario_id,
                titulo=titulo.strip(),
                descricao=descricao.strip() if descricao else None,
                dia_resevado=date.fromisoformat(data_evento),
                hora_resevada=time.fromisoformat(hora_evento),
                tipo_evento={
                    "Consulta médica": tipoEvento.CONSULTA,
                    "Exame": tipoEvento.EXAME,
                    "Vacina": tipoEvento.VACINA,
                    "Remédio": tipoEvento.MEDICACAO,
                    "Outro": tipoEvento.OUTRO,
                }.get(tipo),
            )
            db.session.add(evento)
            db.session.commit()
            return True
        except (ValueError, TypeError):
            db.session.rollback()
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar evento do calendário: {e}")
            return False

    @staticmethod
    def editar_evento_calendario(evento_id, titulo, descricao, data_evento, hora_evento, tipo):
        try:
            usuario_id = session.get('usuario_id')
            evento = db.session.scalars(
                select(EventoCalendario).where(
                    EventoCalendario.id == evento_id,
                    EventoCalendario.id_usuario == usuario_id,
                )
            ).first()
            if not evento or not titulo or not data_evento or not hora_evento:
                return False

            evento.titulo = titulo.strip()
            evento.descricao = descricao.strip() if descricao else None
            evento.dia_resevado = date.fromisoformat(data_evento)
            evento.hora_resevada = time.fromisoformat(hora_evento)
            evento.tipo_evento = {
                "Consulta médica": tipoEvento.CONSULTA,
                "Exame": tipoEvento.EXAME,
                "Vacina": tipoEvento.VACINA,
                "Remédio": tipoEvento.MEDICACAO,
                "Outro": tipoEvento.OUTRO,
            }.get(tipo)
            db.session.commit()
            return True
        except (ValueError, TypeError):
            db.session.rollback()
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao editar evento do calendário: {e}")
            return False

    @staticmethod
    def excluir_evento_calendario(evento_id):
        try:
            usuario_id = session.get('usuario_id')
            evento = db.session.scalars(
                select(EventoCalendario).where(
                    EventoCalendario.id == evento_id,
                    EventoCalendario.id_usuario == usuario_id,
                )
            ).first()
            if not evento:
                return False

            db.session.delete(evento)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao excluir evento do calendário: {e}")
            return False

    @staticmethod
    def buscar_paciente_login():
        usuario_id = session.get('usuario_id')

        if not usuario_id:
            print("Erro: Nenhum usuário encontrado.")
            return None, 'Não informado', 'Não informado', None

        query = sa.select(Paciente).where(Paciente.id_usuario == usuario_id)
        paciente = db.session.scalars(query).first()

        if not paciente:
            print("Erro: Paciente não cadastrado no banco de dados.")
            return None, 'Não informado', 'Não informado', None

        if paciente.genero == 'F':
            genero = 'Feminino'
        elif paciente.genero == 'M':
            genero = 'Masculino'
        else:
            genero = 'Não informado'

        tipo_diabete_valor = paciente.tipo_diabete.value if paciente.tipo_diabete else None

        if tipo_diabete_valor == 'tipo1':
            tipo_diabete = 'Tipo 1'
        elif tipo_diabete_valor == 'tipo2':
            tipo_diabete = 'Tipo 2'
        elif tipo_diabete_valor == 'gestacional':
            tipo_diabete = 'Gestacional'
        else: 
            tipo_diabete = 'Não informado'

        if paciente.nascimento: 
            hoje = date.today()

            idade = hoje.year - paciente.nascimento.year

            if (hoje.month, hoje.day) < (paciente.nascimento.month, paciente.nascimento.day):
                idade -= 1
        else:
            idade = None 

        return paciente, genero, tipo_diabete, idade 

    @staticmethod
    def registrar_glicemia(data_registro, hora_registro, medida, estado, paciente_id=None):
        try:
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                print("Erro: Nenhum usuário encontrado na sessão.")
                return False

            papel_ativo = UsuarioController.obter_papel_ativo()
            if papel_ativo in {"cuidador", "responsavel"}:
                if not paciente_id:
                    return False
                paciente_vinculado = next(
                    (paciente for paciente in UsuarioController.listar_pacientes_acompanhados(papel_ativo)
                     if paciente["id"] == int(paciente_id)),
                    None,
                )
                if not paciente_vinculado:
                    return False
                usuario_id = paciente_vinculado["usuario_id"]
            elif papel_ativo != "paciente" or paciente_id:
                return False

            estados = {
                "jejum": EstadoPessoal.JEJUM,
                "pre-refeicao": EstadoPessoal.PRE_REF,
                "pos-refeicao": EstadoPessoal.POS_REF,
                "sintomatico": EstadoPessoal.SINTOMATICO,
            }
            valor_medida = Decimal(str(medida).replace(',', '.'))
            registro = RegistroGlicemico(
                id_usuario=usuario_id,
                medida=valor_medida,
                data_registro=date.fromisoformat(data_registro),
                hora_registro=time.fromisoformat(hora_registro),
                estado=estados.get(estado),
            )
            db.session.add(registro)
            db.session.commit()

            print(f"Glicemia registrada para o usuário {usuario_id}: {medida} mg/dL")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao registrar glicemia: {e}")
            return False
        