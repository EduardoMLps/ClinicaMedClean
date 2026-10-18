"""
Instancias compartilhadas das extensoes Flask usadas pelo backend.

Este modulo existe para evitar import circular: models e rotas importam
`db` (SQLAlchemy) e `jwt` (JWTManager) daqui, e a factory da aplicacao
(app/__init__.py, criada pelo modulo responsavel pelo bootstrap do app)
deve chamar `db.init_app(app)` e `jwt.init_app(app)`.
"""

from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()

# Limiter global (Flask-Limiter). A politica default (aplicada a todas as
# rotas, salvo limites especificos por endpoint via decorator) e deixada
# permissiva aqui -- o endpoint sensivel a forca bruta (POST /auth/login)
# recebe seu proprio limite explicito em app/routes/auth.py. O storage
# backend e configurado via RATELIMIT_STORAGE_URI (memory:// em dev; usar
# Redis em producao com mais de um worker/processo).
limiter = Limiter(key_func=get_remote_address)
