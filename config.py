import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "glicohealth-development-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def get_uri():
        # Tenta pegar a URI completa primeiro (se existir)
        env_uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
        if env_uri:
            if env_uri.startswith("mysql://"):
                return env_uri.replace("mysql://", "mysql+pymysql://", 1)
            return env_uri

        # Caso prefira usar as variáveis separadas do Aiven ou Local:
        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "labinfo")
        db_name = os.getenv("DB_NAME", "glicohealthbd")
        db_port = os.getenv("DB_PORT", "3306")

        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Atribui a URI à configuração que o Flask-SQLAlchemy procura
Config.SQLALCHEMY_DATABASE_URI = Config.get_uri()