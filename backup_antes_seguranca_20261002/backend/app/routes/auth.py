"""
Blueprint 'auth' -- autenticacao (RF17).

Rotas expostas sob o prefixo /api/v1/auth:
    POST /api/v1/auth/login    -> autentica e retorna access/refresh token
    POST /api/v1/auth/refresh  -> gera novo access token a partir do refresh
    GET  /api/v1/auth/me       -> dados do usuario autenticado
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from app.extensions import limiter
from app.models.auth import Usuario
from app.utils.security import verificar_senha

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# Claims do JWT que ja fazem parte do padrao do flask_jwt_extended e nao
# devem ser expostas de novo dentro do bloco de claims customizadas.
_CLAIMS_RESERVADAS = {"sub", "exp", "iat", "nbf", "jti", "type", "fresh"}


def _montar_claims_adicionais(usuario: Usuario) -> dict:
    return {
        "perfil": usuario.perfil.nome if usuario.perfil else None,
        "nome": usuario.nome,
        "email": usuario.email,
    }


def _chave_rate_limit_login():
    """
    Combina IP de origem + email informado no corpo da requisicao, para que
    o limite de tentativas de login seja por (IP, email) e nao apenas por
    IP -- um atacante atras de um unico IP nao consegue "gastar" o limite
    de todos os emails de uma vez, e nao consegue burlar o limite de um
    email especifico trocando de IP sem custo.
    """
    from flask_limiter.util import get_remote_address

    payload = request.get_json(silent=True) or {}
    email = payload.get("email") if isinstance(payload, dict) else None
    email_normalizado = email.strip().lower() if isinstance(email, str) else "sem-email"
    return f"{get_remote_address()}:{email_normalizado}"


@auth_bp.post("/login")
@limiter.limit("5 per minute", key_func=_chave_rate_limit_login)
@limiter.limit("20 per minute")  # limite adicional so por IP, cobre varios emails
def login():
    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    email = payload.get("email")
    senha = payload.get("senha")

    if not email or not isinstance(email, str) or not email.strip():
        return jsonify({"erro": "Campo 'email' e obrigatorio e deve ser texto."}), 400
    if not senha or not isinstance(senha, str):
        return jsonify({"erro": "Campo 'senha' e obrigatorio e deve ser texto."}), 400

    email_normalizado = email.strip().lower()
    usuario = Usuario.query.filter_by(email=email_normalizado).first()

    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        return jsonify({"erro": "Credenciais invalidas."}), 401

    if not usuario.ativo:
        return (
            jsonify({"erro": "Usuario inativo. Contate o administrador do sistema."}),
            403,
        )

    claims_adicionais = _montar_claims_adicionais(usuario)
    access_token = create_access_token(
        identity=str(usuario.id), additional_claims=claims_adicionais
    )
    refresh_token = create_refresh_token(
        identity=str(usuario.id), additional_claims=claims_adicionais
    )

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "usuario": usuario.to_dict(),
            }
        ),
        200,
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identidade = get_jwt_identity()

    try:
        usuario_id = int(identidade)
    except (TypeError, ValueError):
        return jsonify({"erro": "Token de refresh invalido."}), 401

    usuario = Usuario.query.get(usuario_id)
    if usuario is None or not usuario.ativo:
        return jsonify({"erro": "Usuario nao encontrado ou inativo."}), 401

    claims_adicionais = _montar_claims_adicionais(usuario)
    novo_access_token = create_access_token(
        identity=str(usuario.id), additional_claims=claims_adicionais
    )

    return jsonify({"access_token": novo_access_token}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identidade = get_jwt_identity()

    try:
        usuario_id = int(identidade)
    except (TypeError, ValueError):
        return jsonify({"erro": "Token invalido."}), 401

    usuario = Usuario.query.get(usuario_id)
    if usuario is None:
        return jsonify({"erro": "Usuario nao encontrado."}), 404

    dados = usuario.to_dict()
    claims = get_jwt()
    dados["claims"] = {
        chave: valor for chave, valor in claims.items() if chave not in _CLAIMS_RESERVADAS
    }
    return jsonify(dados), 200
