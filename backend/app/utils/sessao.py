"""
Controle de sessao (JWT) -- correcao B3.

A cada requisicao autenticada o token e conferido contra o banco:
  - o jti nao pode estar na lista de tokens revogados (logout);
  - o token nao pode ter sido emitido antes de um "encerrar sessoes" do
    usuario (troca de senha, troca de perfil, desativacao);
  - o usuario precisa existir e estar ativo;
  - o perfil gravado no token precisa ser o perfil atual no banco.

Se qualquer conferencia falhar, o token e tratado como revogado (HTTP 401).
"""

from datetime import datetime, timedelta, timezone

from flask import jsonify

from app.extensions import db


def _agora_utc_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def revogar_token(jwt_payload):
    """Revoga um token decodificado (dict de claims). Idempotente."""
    from app.models.auth import TokenRevogado

    jti = jwt_payload.get("jti")
    if not jti:
        return
    if TokenRevogado.query.filter_by(jti=jti).first() is not None:
        return
    exp = jwt_payload.get("exp")
    expira_em = (
        datetime.fromtimestamp(int(exp), tz=timezone.utc).replace(tzinfo=None)
        if exp
        else _agora_utc_naive()
    )
    usuario_id = jwt_payload.get("sub")
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        usuario_id = None
    db.session.add(
        TokenRevogado(
            jti=jti,
            usuario_id=usuario_id,
            tipo=jwt_payload.get("type", "access"),
            expira_em=expira_em,
        )
    )
    db.session.commit()


def encerrar_todas_as_sessoes(usuario_id, commit=True):
    """Invalida todos os tokens ja emitidos para o usuario."""
    from app.models.auth import RevogacaoSessaoUsuario

    registro = db.session.get(RevogacaoSessaoUsuario, int(usuario_id))
    # O "iat" do JWT tem precisao de segundos. Arredondar para o PROXIMO
    # segundo garante que um token emitido no mesmo segundo da revogacao
    # (antes dela) tambem seja recusado.
    agora = _agora_utc_naive() + timedelta(seconds=1)
    if registro is None:
        db.session.add(RevogacaoSessaoUsuario(usuario_id=int(usuario_id), revogado_em=agora))
    else:
        registro.revogado_em = agora
    if commit:
        db.session.commit()


def limpar_tokens_expirados():
    """Apaga da lista de revogados os tokens que ja expiraram de qualquer forma."""
    from app.models.auth import TokenRevogado

    apagados = TokenRevogado.query.filter(
        TokenRevogado.expira_em < _agora_utc_naive()
    ).delete(synchronize_session=False)
    db.session.commit()
    return apagados


def token_invalido(jwt_payload):
    """True se o token deve ser recusado. Usado pelo Flask-JWT-Extended."""
    from app.models.auth import RevogacaoSessaoUsuario, TokenRevogado, Usuario

    jti = jwt_payload.get("jti")
    if not jti or TokenRevogado.query.filter_by(jti=jti).first() is not None:
        return True

    try:
        usuario_id = int(jwt_payload.get("sub"))
    except (TypeError, ValueError):
        return True

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        return True

    perfil_atual = usuario.perfil.nome if usuario.perfil else None
    if jwt_payload.get("perfil") != perfil_atual:
        return True

    revogacao = db.session.get(RevogacaoSessaoUsuario, usuario_id)
    if revogacao is not None:
        emitido_em = datetime.fromtimestamp(
            int(jwt_payload.get("iat", 0)), tz=timezone.utc
        ).replace(tzinfo=None)
        if emitido_em < revogacao.revogado_em:
            return True

    return False


def registrar_callbacks_jwt(jwt):
    """Liga as conferencias acima ao JWTManager da aplicacao."""
    from app.models.auth import Usuario

    @jwt.token_in_blocklist_loader
    def _token_na_lista(_jwt_header, jwt_payload):
        return token_invalido(jwt_payload)

    @jwt.revoked_token_loader
    def _token_revogado(_jwt_header, _jwt_payload):
        return jsonify({"erro": "Sessao encerrada ou invalida. Faca login novamente."}), 401

    @jwt.expired_token_loader
    def _token_expirado(_jwt_header, _jwt_payload):
        return jsonify({"erro": "Sessao expirada. Faca login novamente."}), 401

    @jwt.invalid_token_loader
    def _token_malformado(_motivo):
        return jsonify({"erro": "Token invalido. Faca login novamente."}), 401

    @jwt.unauthorized_loader
    def _sem_token(_motivo):
        return jsonify({"erro": "Autenticacao necessaria."}), 401

    @jwt.user_lookup_error_loader
    def _usuario_inexistente(_jwt_header, _jwt_payload):
        return jsonify({"erro": "Sessao encerrada ou invalida. Faca login novamente."}), 401

    @jwt.user_lookup_loader
    def _carregar_usuario(_jwt_header, jwt_payload):
        try:
            return db.session.get(Usuario, int(jwt_payload.get("sub")))
        except (TypeError, ValueError):
            return None
