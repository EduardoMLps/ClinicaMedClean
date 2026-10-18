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

    _configurar_proxy_reverso(app)
    _inicializar_extensoes(app)
    _registrar_blueprints(app)
    _registrar_rotas_utilitarias(app)
    _registrar_error_handlers(app)
    _registrar_cabecalhos_seguranca(app)
    _registrar_comandos_cli(app)
    _garantir_tabelas_de_seguranca(app)

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


def _configurar_proxy_reverso(app):
    """
    B6: atras do nginx, o IP da conexao e sempre o do proxy. Com
    TRUSTED_PROXY_COUNT >= 1 o ProxyFix passa a usar o X-Forwarded-For
    (que o nginx do Med Flow sobrescreve com o IP real do cliente), e o
    limite de tentativas de login volta a ser por pessoa, nao global.
    Sem proxy (instalacao local), deixe 0 para nao confiar em cabecalhos
    que o proprio cliente poderia forjar.
    """
    quantidade = app.config.get("TRUSTED_PROXY_COUNT", 0)
    if quantidade > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=quantidade,
            x_proto=quantidade,
            x_host=quantidade,
        )


def _inicializar_extensoes(app):
    from app.utils.sessao import registrar_callbacks_jwt

    db.init_app(app)
    jwt.init_app(app)
    registrar_callbacks_jwt(jwt)
    limiter.init_app(app)

    if app.config.get("ENV") == "production" and str(
        app.config.get("RATELIMIT_STORAGE_URI", "")
    ).startswith("memory"):
        logging.getLogger(__name__).warning(
            "RATELIMIT_STORAGE_URI=memory:// em producao: com varios workers "
            "do gunicorn cada processo conta as tentativas de login "
            "separadamente. Use Redis (ex.: redis://redis:6379/0)."
        )

    # CORS restrito explicitamente as origens de FRONTEND_URL. Nunca "*":
    # as rotas da API trafegam dados de pacientes/prontuarios (LGPD) e
    # exigem JWT em header Authorization, que nao pode ser exposto a
    # qualquer origem.
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}},
        # B14: o token vai no cabecalho Authorization, nao em cookie; nao ha
        # motivo para liberar credenciais de navegador entre origens.
        supports_credentials=False,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
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

    @app.errorhandler(413)
    def payload_grande(_erro):
        limite_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        return (
            jsonify({"erro": f"Arquivo ou requisicao maior que o limite de {limite_mb} MB."}),
            413,
        )

    @app.errorhandler(429)
    def muitas_tentativas(_erro):
        return (
            jsonify({"erro": "Muitas tentativas. Aguarde um minuto e tente novamente."}),
            429,
        )

    @app.errorhandler(500)
    def internal_error(_erro):
        logging.getLogger(__name__).exception("Erro interno nao tratado.")
        return jsonify({"erro": "Erro interno do servidor."}), 500


def _registrar_cabecalhos_seguranca(app):
    """Cabecalhos aplicados a toda resposta da API (B7), mesmo sem nginx."""

    @app.after_request
    def _cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "no-referrer")
        # Dados de pacientes nunca devem ficar em cache de navegador/proxy.
        resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta


def _registrar_comandos_cli(app):
    """Comandos administrativos: flask --app wsgi <comando>."""
    import getpass

    import click

    @app.cli.command("definir-senha-admin")
    @click.option("--email", default="admin@clinica.local", show_default=True)
    def definir_senha_admin(email):
        """Define a senha de um usuario (B1: substitui a senha de demonstracao)."""
        from app.models.auth import Usuario
        from app.utils.security import hash_senha, validar_politica_senha
        from app.utils.sessao import encerrar_todas_as_sessoes

        usuario = Usuario.query.filter_by(email=email.strip().lower()).first()
        if usuario is None:
            raise click.ClickException(f"Usuario '{email}' nao encontrado.")
        senha = getpass.getpass("Nova senha: ")
        if senha != getpass.getpass("Repita a nova senha: "):
            raise click.ClickException("As senhas nao conferem.")
        problemas = validar_politica_senha(senha, email=usuario.email, nome=usuario.nome)
        if problemas:
            raise click.ClickException(" ".join(problemas))
        usuario.senha_hash = hash_senha(senha)
        encerrar_todas_as_sessoes(usuario.id, commit=False)
        db.session.commit()
        click.echo(f"Senha de {usuario.email} atualizada. Sessoes anteriores encerradas.")

    @app.cli.command("limpar-tokens-expirados")
    def limpar_tokens():
        """Remove da lista de revogados os tokens que ja expiraram."""
        from app.utils.sessao import limpar_tokens_expirados

        click.echo(f"{limpar_tokens_expirados()} registro(s) removido(s).")

    @app.cli.command("limpar-logs-auditoria")
    @click.option("--dias", default=None, type=int, help="Padrao: AUDIT_LOG_RETENCAO_DIAS")
    def limpar_logs(dias):
        """B13: apaga registros de auditoria mais antigos que a retencao definida."""
        from app.utils.security import limpar_logs_auditoria_antigos

        dias = dias or app.config.get("AUDIT_LOG_RETENCAO_DIAS")
        click.echo(f"{limpar_logs_auditoria_antigos(dias)} registro(s) removido(s).")


def _garantir_tabelas_de_seguranca(app):
    """
    Cria as tabelas novas da versao 4.0.1 (tokens_revogados,
    revogacoes_sessao_usuario) em bancos ja existentes, sem mexer nas demais.
    Equivale a rodar database/migracao_4.0.1_seguranca.sql.
    """
    from app.models.auth import RevogacaoSessaoUsuario, TokenRevogado

    with app.app_context():
        try:
            for tabela in (TokenRevogado.__table__, RevogacaoSessaoUsuario.__table__):
                tabela.create(db.engine, checkfirst=True)
            _adicionar_coluna_profissional_em_usuarios()
        except Exception:  # banco fora do ar na subida, sem permissao, etc.
            logging.getLogger(__name__).warning(
                "Nao foi possivel conferir/criar as tabelas de sessao. Rode "
                "database/migracao_4.0.1_seguranca.sql manualmente.",
                exc_info=True,
            )


def _adicionar_coluna_profissional_em_usuarios():
    """B9: cria usuarios.profissional_id em bancos anteriores a 4.0.1."""
    from sqlalchemy import inspect, text

    inspetor = inspect(db.engine)
    if "usuarios" not in inspetor.get_table_names():
        return
    colunas = {c["name"] for c in inspetor.get_columns("usuarios")}
    if "profissional_id" in colunas:
        return
    with db.engine.begin() as conexao:
        if db.engine.dialect.name == "mysql":
            conexao.execute(
                text(
                    "ALTER TABLE usuarios "
                    "ADD COLUMN profissional_id BIGINT UNSIGNED NULL, "
                    "ADD CONSTRAINT fk_usuarios_profissional FOREIGN KEY (profissional_id) "
                    "REFERENCES profissionais (id) ON DELETE SET NULL ON UPDATE CASCADE"
                )
            )
        else:
            conexao.execute(text("ALTER TABLE usuarios ADD COLUMN profissional_id BIGINT NULL"))
    logging.getLogger(__name__).info("Coluna usuarios.profissional_id criada (migracao 4.0.1).")
