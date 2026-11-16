import os
import unittest
from unittest.mock import patch

from sqlalchemy.dialects.mysql import LONGBLOB, TINYINT
from sqlalchemy.ext.compiler import compiles
from werkzeug.security import generate_password_hash


# Converte tipos exclusivos do MySQL para equivalentes do SQLite nos testes.
@compiles(TINYINT, "sqlite")
def compilar_tinyint_para_sqlite(tipo, compilador, **opcoes):
    return "INTEGER"


@compiles(LONGBLOB, "sqlite")
def compilar_longblob_para_sqlite(tipo, compilador, **opcoes):
    return "BLOB"


with patch.dict(
    os.environ,
    {
        "DB_HOST": "system-test.invalid",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    },
):
    from app import app, db
    from app import routes
    from app.modelos import (
        Cuidador,
        LeituraTemperatura,
        Paciente,
        Responsavel,
        Usuario,
        registro_glicemico as RegistroGlicemico,
    )

TABELAS_DE_TESTE = [
    Usuario.__table__,
    Cuidador.__table__,
    Paciente.__table__,
    Responsavel.__table__,
    LeituraTemperatura.__table__,
    RegistroGlicemico.__table__,
]


class TestesDeSistema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
        )
        with app.app_context():
            db.metadata.create_all(db.engine, tables=TABELAS_DE_TESTE)

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.session.remove()
            db.metadata.drop_all(db.engine, tables=TABELAS_DE_TESTE)

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            db.session.remove()
            db.metadata.drop_all(db.engine, tables=TABELAS_DE_TESTE)
            db.metadata.create_all(db.engine, tables=TABELAS_DE_TESTE)

        routes.ultima_leitura.update(
            temperatura="--",
            status="Aguardando leitura",
            hora="--",
        )
        routes.ultima.update(temperatura=None, hora=None)

    def tearDown(self):
        with app.app_context():
            db.session.remove()

    def definir_sessao(self, usuario_id=1, papel=None):
        with self.client.session_transaction() as sessao:
            sessao["usuario_id"] = usuario_id
            if papel:
                sessao["papel_ativo"] = papel

    def criar_usuario(self, username="pessoa-teste", email="pessoa@example.com"):
        with app.app_context():
            usuario = Usuario(
                name="Pessoa de Teste",
                username=username,
                email=email,
                passw_hash=generate_password_hash("senha-segura"),
                remember_me=0,
            )
            db.session.add(usuario)
            db.session.commit()
            return usuario.id

    def test_inicio_redireciona_usuario_anonimo_para_login(self):
        resposta = self.client.get("/home")

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/login")

    def test_paginas_publicas_abrem(self):
        paginas = (
            "/",
            "/cadastro",
            "/login",
            "/recuperar-senha",
            "/pediabetico",
            "/questionario",
            "/questionario/paciente",
            "/questionario/tipo_cuidador",
            "/validar_profissional",
            "/questionario/quest_responsavel",
        )

        for pagina in paginas:
            with self.subTest(pagina=pagina):
                resposta = self.client.get(pagina)
                self.assertEqual(resposta.status_code, 200)

    def test_rotas_que_exigem_sessao_nao_exibem_dados_anonimamente(self):
        for pagina in ("/perfil", "/registroglicemia"):
            with self.subTest(pagina=pagina):
                resposta = self.client.get(pagina)
                self.assertEqual(resposta.status_code, 302)
                self.assertEqual(resposta.headers["Location"], "/login")

    def test_login_com_senha_incorreta_mostra_mensagem_de_erro(self):
        self.criar_usuario()

        resposta = self.client.post(
            "/login",
            data={"username": "pessoa-teste", "password": "senha-incorreta"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Usu\xc3\xa1rio ou senha incorretos.", resposta.data)
        with self.client.session_transaction() as sessao:
            self.assertNotIn("usuario_id", sessao)

    def test_login_inicia_sessao_e_redireciona_para_questionario(self):
        usuario_id = self.criar_usuario()

        resposta = self.client.post(
            "/login",
            data={"username": "pessoa-teste", "password": "senha-segura"},
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/home")
        with self.client.session_transaction() as sessao_usuario:
            self.assertEqual(sessao_usuario["usuario_id"], usuario_id)

        resposta_inicio = self.client.get("/home")
        self.assertEqual(resposta_inicio.status_code, 302)
        self.assertEqual(resposta_inicio.headers["Location"], "/questionario")

    def test_cadastro_valido_redireciona_para_questionario(self):
        resposta = self.client.post(
            "/cadastro",
            data={
                "name": "Pessoa Nova",
                "username": "pessoa-nova",
                "email": "nova@example.com",
                "password": "senha-segura",
                "confirm_password": "senha-segura",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/questionario")
        with app.app_context():
            usuario = db.session.query(Usuario).filter_by(
                username="pessoa-nova"
            ).one()
            self.assertEqual(usuario.email, "nova@example.com")
        with self.client.session_transaction() as sessao:
            self.assertIn("usuario_id", sessao)

    def test_cadastro_invalido_permanece_no_formulario(self):
        resposta = self.client.post(
            "/cadastro",
            data={
                "name": "",
                "username": "",
                "email": "email-invalido",
                "password": "123",
                "confirm_password": "diferente",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Insira um endere", resposta.data)

    def test_recuperacao_de_senha_atualiza_credencial_e_volta_ao_login(self):
        self.criar_usuario()
        with patch.object(
            routes.AuthenticationController,
            "redefinir_senha",
            return_value=True,
        ) as redefinir_senha:
            resposta = self.client.post(
                "/recuperar-senha",
                data={
                    "email": "pessoa@example.com",
                    "nova_senha": "nova-senha-segura",
                    "confirmar_senha": "nova-senha-segura",
                },
            )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/login")
        redefinir_senha.assert_called_once()

    def test_logout_limpa_sessao_e_redireciona_para_login(self):
        self.definir_sessao()

        resposta = self.client.get("/logout")

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/login")
        with self.client.session_transaction() as sessao:
            self.assertNotIn("usuario_id", sessao)

    def test_questionario_salva_papel_de_paciente_e_prossegue(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id)

        resposta = self.client.post(
            "/questionario",
            data={"papeis": "paciente"},
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/questionario/paciente")
        with app.app_context():
            self.assertIsNotNone(
                db.session.query(Paciente).filter_by(id_usuario=usuario_id).first()
            )

    def test_questionario_sem_papel_exibe_validacao(self):
        resposta = self.client.post("/questionario", data={})

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Selecione ao menos um papel", resposta.data)

    def test_questionario_paciente_salva_dados_e_abre_inicio(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id)
        with app.app_context():
            db.session.add(Paciente(id_usuario=usuario_id))
            db.session.commit()

        resposta = self.client.post(
            "/questionario/paciente",
            data={
                "dia": "15",
                "mes": "6",
                "ano": "2000",
                "sexo": "feminino",
                "tipo_diabetes": "tipo_1",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/home")
        with app.app_context():
            paciente = db.session.query(Paciente).filter_by(id_usuario=usuario_id).one()
            self.assertEqual(str(paciente.nascimento), "2000-06-15")
            self.assertEqual(paciente.genero, "F")

    def test_fluxo_de_cuidador_salva_papel_e_tipo_familiar(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id)
        resposta_papel = self.client.post(
            "/questionario",
            data={"papeis": "cuidador"},
        )
        resposta_tipo = self.client.post(
            "/questionario/tipo_cuidador",
            data={"tipo_cuidador": "familiar"},
        )

        self.assertEqual(resposta_papel.status_code, 302)
        self.assertEqual(resposta_papel.headers["Location"], "/questionario/tipo_cuidador")
        self.assertEqual(resposta_tipo.status_code, 302)
        self.assertIn("/verificar_paciente", resposta_tipo.headers["Location"])
        with app.app_context():
            cuidador = db.session.query(Cuidador).filter_by(
                id_usuario=usuario_id
            ).one()
            self.assertEqual(cuidador.tipo_cuidador.value, "familiar")

    def test_tipo_de_cuidador_encaminha_profissional_para_validacao(self):
        with patch.object(routes.UsuarioController, "salvar_tipo_cuidador"):
            resposta = self.client.post(
                "/questionario/tipo_cuidador",
                data={"tipo_cuidador": "profissional"},
            )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/validar_profissional", resposta.headers["Location"])

    def test_validacao_profissional_aceita_registro_com_uf_e_redireciona(self):
        with patch.object(routes.UsuarioController, "salvar_dados_profissional"):
            resposta = self.client.post(
                "/validar_profissional",
                data={
                    "conselhoprofissional": "CRM",
                    "registroprofissional": "RN123456",
                },
            )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/verificar_paciente")

    def test_validacao_profissional_rejeita_registro_malformado(self):
        resposta = self.client.post(
            "/validar_profissional",
            data={
                "conselhoprofissional": "CRM",
                "registroprofissional": "UF123",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"UF v", resposta.data)

    def test_associacao_ajax_de_paciente_retorna_redirecionamento(self):
        self.definir_sessao(papel="cuidador")
        with (
            patch.object(
                routes.UsuarioController,
                "obter_papel_ativo",
                return_value="cuidador",
            ),
            patch.object(
                routes.UsuarioController,
                "associar_paciente",
                return_value="success",
            ),
        ):
            resposta = self.client.post(
                "/verificar_paciente",
                data={"email": "paciente@example.com"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.get_json(),
            {"success": True, "redirect": "/home"},
        )

    def test_associacao_ajax_de_paciente_informa_quando_nao_encontrado(self):
        self.definir_sessao(papel="cuidador")
        with (
            patch.object(
                routes.UsuarioController,
                "obter_papel_ativo",
                return_value="cuidador",
            ),
            patch.object(
                routes.UsuarioController,
                "associar_paciente",
                return_value="not_found",
            ),
        ):
            resposta = self.client.post(
                "/verificar_paciente",
                data={"email": "inexistente@example.com"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

        self.assertEqual(resposta.status_code, 404)
        self.assertFalse(resposta.get_json()["success"])

    def test_pagina_de_associacao_exibe_formulario_para_cuidador(self):
        self.definir_sessao(papel="cuidador")
        with patch.object(
            routes.UsuarioController,
            "obter_papel_ativo",
            return_value="cuidador",
        ):
            resposta = self.client.get("/verificar_paciente")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Associar Paciente", resposta.data)

    def test_pagina_de_associacao_redireciona_papel_nao_autorizado(self):
        with patch.object(
            routes.UsuarioController,
            "obter_papel_ativo",
            return_value="paciente",
        ):
            resposta = self.client.get("/verificar_paciente")

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/home")

    def test_questionario_responsavel_rejeita_relacao_invalida(self):
        resposta = self.client.post(
            "/questionario/quest_responsavel",
            data={
                "tipo_responsavel": "menor_idade",
                "relacao_responsavel": "Inválida",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/questionario/quest_responsavel", resposta.headers["Location"])

    def test_questionario_responsavel_salva_relacao_valida(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id)
        with app.app_context():
            db.session.add(Responsavel(id_usuario=usuario_id))
            db.session.commit()

        resposta = self.client.post(
            "/questionario/quest_responsavel",
            data={
                "tipo_responsavel": "menor_idade",
                "relacao_responsavel": "Mãe",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/verificar_paciente")
        with self.client.session_transaction() as sessao:
            self.assertEqual(sessao["relacao_responsavel"], "Mãe")
        with app.app_context():
            responsavel = db.session.query(Responsavel).filter_by(
                id_usuario=usuario_id
            ).one()
            self.assertEqual(responsavel.responsabilidade, "menor_idade")

    def test_troca_de_papel_atualiza_sessao(self):
        self.definir_sessao(papel="paciente")
        with (
            patch.object(routes.UsuarioController, "buscar_usuario_login", return_value=True),
            patch.object(routes.UsuarioController, "selecionar_papel", return_value=True),
        ):
            resposta = self.client.post("/home/papel", data={"papel": "cuidador"})

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/home")

    def test_troca_de_paciente_redireciona_para_inicio(self):
        self.definir_sessao(papel="cuidador")
        with patch.object(
            routes.UsuarioController,
            "selecionar_paciente_cuidado",
            return_value={"id": 7},
        ):
            resposta = self.client.post(
                "/home/paciente",
                data={"paciente_id": "7"},
            )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/home")

    def test_pagina_inicial_autenticada_carrega_dados(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id, "paciente")
        with (
            patch.object(
                routes.UsuarioController,
                "buscar_usuario_login",
                return_value=Usuario(
                    id=usuario_id,
                    name="Pessoa de Teste",
                    username="pessoa-teste",
                    remember_me=0,
                ),
            ),
            patch.object(
                routes.UsuarioController,
                "listar_papeis_usuario",
                return_value=["paciente"],
            ),
            patch.object(
                routes.UsuarioController,
                "obter_papel_ativo",
                return_value="paciente",
            ),
            patch.object(
                routes.UsuarioController,
                "buscar_registros_glicemia_login",
                return_value=[],
            ),
            patch.object(
                routes.UsuarioController,
                "buscar_eventos_calendario_login",
                return_value=[],
            ),
        ):
            resposta = self.client.get("/home")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Pessoa de Teste", resposta.data)

    def test_rotas_de_evento_de_calendario_enviam_operacao_e_redirecionam(self):
        dados_evento = {
            "nome": "Consulta",
            "descricao": "Consulta de rotina",
            "data": "2026-12-10",
            "hora": "10:30",
            "tipo": "Consulta médica",
        }
        with (
            patch.object(
                routes.UsuarioController,
                "criar_evento_calendario",
                return_value=True,
            ) as criar,
            patch.object(
                routes.UsuarioController,
                "editar_evento_calendario",
                return_value=True,
            ) as editar,
            patch.object(
                routes.UsuarioController,
                "excluir_evento_calendario",
                return_value=True,
            ) as excluir,
        ):
            respostas = (
                self.client.post("/calendario/evento", data=dados_evento),
                self.client.post("/calendario/evento/3/editar", data=dados_evento),
                self.client.post("/calendario/evento/3/excluir"),
            )

        for resposta in respostas:
            self.assertEqual(resposta.status_code, 302)
            self.assertEqual(resposta.headers["Location"], "/home")
        criar.assert_called_once()
        editar.assert_called_once()
        excluir.assert_called_once_with(3)

    def test_registro_de_glicemia_paciente_exibe_formulario_e_salva(self):
        self.definir_sessao(papel="paciente")
        with patch.object(
            routes.UsuarioController,
            "obter_papel_ativo",
            return_value="paciente",
        ):
            resposta_formulario = self.client.get("/registroglicemia")
            resposta_envio = self.client.post(
                "/registroglicemia",
                data={
                    "data": "2026-11-02",
                    "hora": "09:15",
                    "glicemia": "110",
                    "estado": "jejum",
                },
            )

        self.assertEqual(resposta_formulario.status_code, 200)
        self.assertEqual(resposta_envio.status_code, 302)
        self.assertIn("/registroglicemia", resposta_envio.headers["Location"])
        with app.app_context():
            registro = db.session.query(RegistroGlicemico).one()
            self.assertEqual(float(registro.medida), 110)
            self.assertEqual(registro.id_usuario, 1)

    def test_perfil_atualiza_dados_e_redireciona(self):
        usuario_id = self.criar_usuario()
        self.definir_sessao(usuario_id, "paciente")
        with (
            patch.object(
                routes.UsuarioController,
                "buscar_usuario_login",
                return_value=Usuario(
                    id=usuario_id,
                    name="Pessoa de Teste",
                    username="pessoa-teste",
                    remember_me=0,
                ),
            ),
            patch.object(
                routes.UsuarioController,
                "obter_papel_ativo",
                return_value="paciente",
            ),
            patch.object(
                routes.UsuarioController,
                "buscar_paciente_login",
                return_value=(None, "Não informado", "Não informado", None),
            ),
            patch.object(
                routes.UsuarioController,
                "atualizar_perfil",
                return_value=(True, "Perfil atualizado."),
            ) as atualizar,
        ):
            resposta = self.client.post(
                "/perfil",
                data={
                    "nome": "Pessoa Atualizada",
                    "email": "atualizada@example.com",
                    "peso": "70",
                    "genero": "F",
                    "tipo_diabete": "tipo1",
                },
            )
            resposta_perfil = self.client.get("/perfil")

        self.assertEqual(resposta_perfil.status_code, 200)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/perfil")
        atualizar.assert_called_once()

    def test_desativacao_de_vinculo_de_responsavel_redireciona_ao_perfil(self):
        self.definir_sessao(papel="responsavel")
        with patch.object(
            routes.UsuarioController,
            "desativar_vinculo_responsavel",
            return_value=True,
        ) as desativar:
            resposta = self.client.post(
                "/perfil/responsavel/paciente/8/desativar"
            )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.headers["Location"], "/perfil")
        desativar.assert_called_once_with(8)

    def test_foto_de_perfil_sem_foto_redireciona_para_avatar_padrao(self):
        resposta = self.client.get("/foto-perfil")

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/static/img/avatar_borda.png", resposta.headers["Location"])

    def test_endpoint_de_temperatura_retorna_erro_para_valores_invalidos(self):
        for dados in ({}, {"temperatura": "quente"}, {"temperatura": "nan"}):
            with self.subTest(dados=dados):
                resposta = self.client.post("/temperatura", json=dados)
                self.assertEqual(resposta.status_code, 400)

    def test_endpoint_de_temperatura_retorna_ultima_leitura(self):
        routes.ultima.update(temperatura=37.1, hora="02/11/2026 10:00:00")

        resposta = self.client.get("/temperatura")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["temperatura"], 37.1)

    def test_envio_de_temperatura_salva_leitura_e_atualiza_status(self):
        resposta = self.client.post(
            "/pediabetico",
            json={"temperatura": 36.75},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"sucesso": True})

        with app.app_context():
            leitura = db.session.query(LeituraTemperatura).one()
            self.assertEqual(float(leitura.temperatura), 36.75)

        resposta_status = self.client.get("/pediabetico/atualizar")
        self.assertEqual(resposta_status.status_code, 200)
        self.assertEqual(resposta_status.get_json()["temperatura"], 36.75)
        self.assertEqual(
            resposta_status.get_json()["status"],
            "Leitura recebida",
        )

    def test_envio_de_temperatura_rejeita_valores_ausentes_ou_invalidos(self):
        dados_enviados = ({}, {"temperatura": "quente"}, {"temperatura": "inf"})

        for dados in dados_enviados:
            with self.subTest(dados=dados):
                resposta = self.client.post("/pediabetico", json=dados)

                self.assertEqual(resposta.status_code, 400)
                self.assertFalse(resposta.get_json()["sucesso"])

        with app.app_context():
            self.assertEqual(db.session.query(LeituraTemperatura).count(), 0)


if __name__ == "__main__":
    unittest.main()
