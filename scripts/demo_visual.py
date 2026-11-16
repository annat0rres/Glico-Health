import argparse
import os
import sys
import tempfile
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from sqlalchemy.dialects.mysql import LONGBLOB, TINYINT
from sqlalchemy.ext.compiler import compiles
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@compiles(TINYINT, "sqlite")
def compilar_tinyint_para_sqlite(tipo, compilador, **opcoes):
    return "INTEGER"


@compiles(LONGBLOB, "sqlite")
def compilar_longblob_para_sqlite(tipo, compilador, **opcoes):
    return "BLOB"


def executar_demonstracao(modo_teste=False):
    try:
        from playwright.sync_api import Error as ErroPlaywright
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        raise SystemExit(
            "Playwright não está instalado. Execute: "
            "python -m pip install -r requirements-demo.txt"
        ) from erro

    with tempfile.TemporaryDirectory(prefix="glicohealth-demo-") as pasta_temporaria:
        caminho_banco = Path(pasta_temporaria) / "demonstracao.sqlite"
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "demonstracao-local.invalid",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{caminho_banco.as_posix()}",
            },
        ):
            from app import app, db
            from app.modelos import (
                Cuidador,
                LeituraTemperatura,
                Paciente,
                Responsavel,
                Usuario,
                evento_calendario,
                registro_glicemico,
            )

        tabelas = [
            Usuario.__table__,
            Cuidador.__table__,
            Paciente.__table__,
            Responsavel.__table__,
            LeituraTemperatura.__table__,
            evento_calendario.__table__,
            registro_glicemico.__table__,
        ]
        for tabela in tabelas:
            for indice in tabela.indexes:
                indice.name = f"{tabela.name}_{indice.name}"
        servidor = None
        thread_servidor = None

        try:
            app.config.update(
                TESTING=True,
                WTF_CSRF_ENABLED=False,
            )
            with app.app_context():
                db.metadata.create_all(db.engine, tables=tabelas)
                db.session.add(
                    Usuario(
                        name="Pessoa de Demonstração",
                        username="demonstracao",
                        email="demonstracao@example.com",
                        passw_hash=generate_password_hash("glico123"),
                        remember_me=0,
                    )
                )
                db.session.commit()

            servidor = make_server("127.0.0.1", 0, app)
            thread_servidor = Thread(target=servidor.serve_forever, daemon=True)
            thread_servidor.start()

            with sync_playwright() as playwright:
                try:
                    navegador = playwright.chromium.launch(headless=modo_teste)
                except ErroPlaywright as erro:
                    raise SystemExit(
                        "Não foi possível abrir o Chromium. Execute: "
                        "python -m playwright install chromium"
                    ) from erro

                try:
                    pagina = navegador.new_page()
                    pagina.goto(
                        f"http://127.0.0.1:{servidor.server_port}/login",
                        wait_until="domcontentloaded",
                    )
                    pagina.locator("#username").fill("demonstracao")
                    pagina.locator("#password").fill("glico123")
                    pagina.locator("#submit").click()
                    pagina.get_by_role("heading", name="Antes de tudo...").wait_for()

                    pagina.locator('[data-role="paciente"]').click()
                    pagina.locator("#btnContinuar").click()
                    pagina.locator("#dia").select_option("15")
                    pagina.locator("#mes").select_option("6")
                    pagina.locator("#ano").select_option("2000")
                    pagina.locator("#sexo").select_option("feminino")
                    pagina.locator("#tipo_diabetes").select_option("tipo_1")
                    pagina.locator("#btnContinuar").click()
                    pagina.get_by_text(
                        "Seja bem-vindo(a), Pessoa de Demonstração"
                    ).wait_for()

                    print(
                        "Demonstração concluída: login, seleção de paciente, "
                        "questionário preenchido e página inicial."
                    )
                    print("Usuário: demonstracao | Senha: glico123")
                    if not modo_teste:
                        input("Pressione Enter para fechar a demonstração...")
                finally:
                    navegador.close()
        finally:
            if servidor:
                servidor.shutdown()
                servidor.server_close()
            if thread_servidor:
                thread_servidor.join()
            with app.app_context():
                db.session.remove()
                db.metadata.drop_all(db.engine, tables=tabelas)
                db.engine.dispose()


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(
        description="Abre uma demonstração visual do fluxo de login."
    )
    argumentos.add_argument(
        "--modo-teste",
        action="store_true",
        help="Executa sem janela visível nem pausa no terminal.",
    )
    executar_demonstracao(argumentos.parse_args().modo_teste)
