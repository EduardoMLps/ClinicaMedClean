"""
Configuracao da aplicacao, lida inteiramente de variaveis de ambiente.

Nenhum valor sensivel (senhas, chaves secretas, etc.) deve ser hardcoded
neste modulo -- em desenvolvimento, as variaveis sao normalmente fornecidas
via arquivo `.env` (nao versionado, veja `.env.example` na raiz do projeto);
em producao, via variaveis de ambiente do orquestrador/host.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

# Carrega um arquivo .env (se existir) para popular os.environ em
# desenvolvimento local. Em producao (containers, etc.) as variaveis de
# ambiente ja sao injetadas pelo orquestrador e load_dotenv() e um no-op
# silencioso caso o arquivo nao exista.
load_dotenv()


def _env_bool(nome, padrao=False):
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on")


def _montar_sqlalchemy_uri():
    """
    Monta a SQLALCHEMY_DATABASE_URI a partir de DB_HOST/DB_PORT/DB_USER/
    DB_PASSWORD/DB_NAME. Permite tambem que SQLALCHEMY_DATABASE_URI seja
    definida diretamente via variavel de ambiente, o que tem prioridade
    (util para bancos de teste/CI com URI customizada).
    """
    uri_explicita = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if uri_explicita:
        return uri_explicita

    db_user = os.environ.get("DB_USER", "")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = os.environ.get("DB_NAME", "clinica_odontologica")

    return (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        "?charset=utf8mb4"
    )


class Config:
    """Configuracao base, compartilhada por todos os ambientes."""

    # --- Flask / seguranca --------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # --- Banco de dados (Flask-SQLAlchemy) ------------------------------
    SQLALCHEMY_DATABASE_URI = _montar_sqlalchemy_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # --- JWT (Flask-JWT-Extended) ---------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    )
    JWT_TOKEN_LOCATION = ["headers"]

    # --- CORS -------------------------------------------------------------
    # FRONTEND_URL pode conter uma unica origem ou uma lista separada por
    # virgulas (ex.: "https://app.clinica.com,https://admin.clinica.com").
    # CORS NUNCA e liberado com "*" -- apenas para as origens explicitamente
    # configuradas.
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
    CORS_ORIGINS = [
        origem.strip() for origem in FRONTEND_URL.split(",") if origem.strip()
    ]

    # --- Flask-Limiter (rate limiting) ------------------------------------
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # --- Diversos -----------------------------------------------------
    DEBUG = _env_bool("FLASK_DEBUG", False)
    ENV = os.environ.get("FLASK_ENV", "production")


config_por_ambiente = {
    "development": Config,
    "production": Config,
    "default": Config,
}


def obter_config(nome_ambiente=None):
    nome_ambiente = nome_ambiente or os.environ.get("FLASK_ENV", "default")
    return config_por_ambiente.get(nome_ambiente, Config)
