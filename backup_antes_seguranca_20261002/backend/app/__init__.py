"""
Application factory do backend do Sistema de Gestao para Clinica Odontologica.

`create_app()` inicializa as extensoes Flask (SQLAlchemy, Flask-JWT-Extended,
Flask-CORS) e registra todos os blueprints existentes sob seus respectivos
prefixos /api/v1/....
"""

import logging

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import obter_config
from app.extensions import db, jwt, limiter


def create_app(config_object=None):
    app = Flask(__name__)

    config_object = config_object or obter_config()
    app.config.from_object(config_object)

    _validar_configuracao_critica(app)

    _inicializar_extensoes(app)
    _registrar_blueprints(app)
    _registrar_rotas_utilitarias(app)
    _registrar_error_handlers(app)

    return app


def _validar_configuracao_critica(app):
    """
    Falha rapido (em vez de subir com defaults inseguros) se segredos
    criticos nao foram fornecidos via variavel de ambiente.
    """
    faltando = [
        nome
        for nome in ("SECRET_KEY", "JWT_SECRET_KEY")
        if not app.config.get(nome)
    ]
    if faltando:
        raise RuntimeError(
            "Variaveis de ambiente obrigatorias ausentes: "
            f"{', '.join(faltando)}. Configure-as (veja .env.example) antes "
            "de iniciar a aplicacao."
        )

    # B2: recusar segredos de exemplo, curtos ou fracos. Com o segredo
    # publico do .env.example qualquer pessoa conseguiria assinar um JWT
    # de administrador.
    problemas = []
    for nome in ("SECRET_KEY", "JWT_SECRET_KEY"):
        motivo = _motivo_segredo_fraco(str(app.config.get(nome)))
        if motivo:
            problemas.append(f"{nome}: {motivo}")
    if app.config.get("SECRET_KEY") == app.config.get("JWT_SECRET_KEY"):
        problemas.append("SECRET_KEY e JWT_SECRET_KEY devem ser diferentes")
    if problemas:
        raise RuntimeError(
            "Segredos inseguros na configuracao: "
            + "; ".join(problemas)
            + ". Gere valores aleatorios com: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )

    if not app.config.get("CORS_ORIGINS"):
        logging.getLogger(__name__).warning(
            "FRONTEND_URL nao configurada: nenhuma origem sera liberada no "
            "CORS. Defina FRONTEND_URL para permitir que o frontend acesse "
            "a API."
        )


TAMANHO_MINIMO_SEGREDO = 32

# Trechos que indicam valor de exemplo/placeholder (comparacao sem
# diferenciar maiusculas).
_MARCADORES_SEGREDO_EXEMPLO = (
    "trocar",
    "change",
    "exemplo",
    "example",
    "placeholder",
    "secret",
    "segredo",
    "senha",
    "password",
    "default",
    "xxxx",
    "1234",
)


def _motivo_segredo_fraco(valor):
    """Retorna o motivo se o segredo for inaceitavel, ou None se for ok."""
    valor = (valor or "").strip()
    if len(valor) < TAMANHO_MINIMO_SEGREDO:
        return f"tem menos de {TAMANHO_MINIMO_SEGREDO} caracteres"
    minusculo = valor.lower()
    for marcador in _MARCADORES_SEGREDO_EXEMPLO:
        if marcador in minusculo:
            return "parece um valor de exemplo/placeholder"
    if len(set(valor)) < 10:
        return "tem pouca variedade de caracteres (nao parece aleatorio)"
    return None


def _inicializar_extensoes(app):
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # CORS restrito explicitamente as origens de FRONTEND_URL. Nunca "*":
    # as rotas da API trafegam dados de pacientes/prontuarios (LGPD) e
    # exigem JWT em header Authorization, que nao pode ser exposto a
    # qualquer origem.
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}},
        supports_credentials=True,
    )


def _registrar_blueprints(app):
    from app.routes.agenda import agenda_bp
    from app.routes.auth import auth_bp
    from app.routes.clinico import clinico_bp
    from app.routes.estoque import estoque_bp
    from app.routes.financeiro import financeiro_bp
    from app.routes.pacientes import pacientes_bp
    from app.routes.profissionais import profissionais_bp
    from app.routes.relatorios import relatorios_bp
    from app.routes.usuarios import usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(pacientes_bp)
    app.register_blueprint(profissionais_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(clinico_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(relatorios_bp)


def _registrar_rotas_utilitarias(app):
    @app.get("/health")
    @app.get("/api/v1/health")
    def healthcheck():
        return jsonify({"status": "ok"}), 200


def _registrar_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_erro):
        return jsonify({"erro": "Recurso nao encontrado."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_erro):
        return jsonify({"erro": "Metodo HTTP nao permitido para este recurso."}), 405

    @app.errorhandler(500)
    def internal_error(_erro):
        logging.getLogger(__name__).exception("Erro interno nao tratado.")
        return jsonify({"erro": "Erro interno do servidor."}), 500
