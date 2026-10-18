"""
Decorators reutilizaveis de autorizacao baseados nas claims do JWT.
"""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def require_perfil(perfis_permitidos):
    """
    Decorator de rota que exige um JWT valido e verifica se o perfil do
    usuario logado (claim 'perfil', incluida no token no momento do
    login) esta na lista de perfis autorizados.

    Uso:
        @usuarios_bp.post("")
        @jwt_required()
        @require_perfil(["administrador"])
        def criar_usuario():
            ...

    O decorator tambem chama verify_jwt_in_request() internamente, entao
    e seguro usa-lo mesmo sem @jwt_required() explicito na rota -- mas o
    padrao do time e manter @jwt_required() explicito por clareza.
    """
    if not isinstance(perfis_permitidos, (list, tuple, set)) or not perfis_permitidos:
        raise ValueError(
            "require_perfil precisa receber uma lista nao vazia de perfis permitidos."
        )

    perfis_permitidos = set(perfis_permitidos)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            perfil_usuario = claims.get("perfil")

            if perfil_usuario is None:
                return (
                    jsonify(
                        {
                            "erro": "Token JWT nao contem informacao de perfil. "
                            "Faca login novamente."
                        }
                    ),
                    401,
                )

            if perfil_usuario not in perfis_permitidos:
                return (
                    jsonify(
                        {
                            "erro": "Acesso negado: seu perfil "
                            f"('{perfil_usuario}') nao tem permissao para "
                            "executar esta operacao."
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
