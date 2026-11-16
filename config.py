import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

class Config:
    CURRENT_DATABASE: str
    SECRET_KEY = os.getenv("SECRET_KEY", "glicohealth-development-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def get_database_type():
        env_uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
        if env_uri:
            scheme = env_uri.partition("://")[0].lower()
            if scheme == "postgres" or scheme.startswith("postgresql"):
                return "postgresql"
            if scheme.startswith("mysql"):
                return "mysql"
            if scheme.startswith("sqlite"):
                return "sqlite"
            raise ValueError(f"Esquema de banco de dados não suportado: {scheme}.")

        current_database = os.getenv("CURRENT_DATABASE", "mysql").strip().lower()
        if current_database not in {"sqlite", "mysql", "postgresql"}:
            raise ValueError(
                "CURRENT_DATABASE deve ser 'sqlite', 'mysql' ou 'postgresql'."
            )
        return current_database

    @staticmethod
    def get_uri():
        # pegar a URI completa primeiro (se existir)
        env_uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
        if env_uri:
            if env_uri.startswith("mysql://"):
                return env_uri.replace("mysql://", "mysql+pymysql://", 1)
            if env_uri.startswith("postgres://"):
                return env_uri.replace("postgres://", "postgresql://", 1)
            return env_uri

        current_database = Config.get_database_type()
        if current_database == "sqlite":
            sqlite_database_path = os.getenv("SQLITE_DATABASE_PATH", "glicohealth.db")
            return f"sqlite:///{sqlite_database_path}"

        # aceita DB_USERNAME para PostgreSQL e mantém DB_USER para configurações existentes.
        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USERNAME") or os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "glicohealthbd")
        default_port = "3306" if current_database == "mysql" else "5432"
        db_port = os.getenv("DB_PORT") or default_port
        encoded_password = quote_plus(db_password)

        if current_database == "postgresql":
            return (
                f"postgresql://{db_user}:{encoded_password}"
                f"@{db_host}:{db_port}/{db_name}"
            )

        return (
            f"mysql+pymysql://{db_user}:{encoded_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )

# atribui a URI à configuração que o Flask-SQLAlchemy procura
Config.CURRENT_DATABASE = Config.get_database_type()
Config.SQLALCHEMY_DATABASE_URI = Config.get_uri()
