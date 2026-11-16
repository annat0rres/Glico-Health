from flask import Flask
from flask_wtf import CSRFProtect
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pymysql

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_uri()

csrf = CSRFProtect(app)


def criar_banco():
    import os
    if Config.CURRENT_DATABASE != "mysql":
        return

    # Mantém o os.getenv, mas com números limpos como padrão para não quebrar
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "labinfo")
    port = int(os.getenv("DB_PORT", "3306"))
    db_name = os.getenv("DB_NAME", "glicohealthbd")

    try:
        # Se NÃO for localhost, significa que ele achou o banco da nuvem
        if "localhost" not in host:
            print("Rodando na nuvem. Ignorando criação automática de banco.")
            return

        # Se for localhost, roda a criação normal no seu computador
        conexao = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        cursor = conexao.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"Aviso na inicialização do banco: {e}")

criar_banco()


db = SQLAlchemy(app)
migration_directory = (
    "migrations_postgresql"
    if Config.CURRENT_DATABASE == "postgresql"
    else "migrations"
)
migrate = Migrate(app, db, directory=migration_directory)

from app import routes
from app import modelos

# with app.app_context():
#     Base.metadata.create_all(db.engine)