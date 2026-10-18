"""
Blueprint 'usuarios' -- gestao de usuarios do sistema (RF17, RF18).

Todas as rotas exigem JWT valido e perfil 'administrador'
(unico perfil autorizado a gerenciar usuarios).

Rotas expostas sob o prefixo /api/v1/usuarios:
    GET    /api/v1/usuarios          -> lista usuarios (ativos por padrao)
    POST   /api/v1/usuarios          -> cria usuario (senha vem em texto puro)
    PUT    /api/v1/usuarios/<id>     -> atualiza usuario
    DELETE /api/v1/usuarios/<id>     -> soft delete (ativo = false)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models.auth import Perfil, Usuario
from app.utils.auth_decorators import require_perfil
from app.utils.security import hash_senha, registrar_auditoria, validar_politica_senha
from app.utils.sessao import encerrar_todas_as_sessoes

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/api/v1/usuarios")

PERFIS_AUTORIZADOS = ["administrador"]


def _resolver_profissional(payload: dict):
    """
    B9: le 'profissional_id' (int ou null) do payload. Retorna
    (valor, None) ou (None, mensagem_de_erro). Usa a sentinela _SEM_VALOR
    quando o campo nao foi enviado.
    """
    if "profissional_id" not in payload:
        return _SEM_VALOR, None
    valor = payload.get("profissional_id")
    if valor is None:
        return None, None
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        return None, "Campo 'profissional_id' deve ser um inteiro positivo ou null."
    from app.models.pacientes import Profissional

    profissional = db.session.get(Profissional, valor)
    if profissional is None or not profissional.ativo:
        return None, f"Profissional com id {valor} nao encontrado ou inativo."
    return valor, None


_SEM_VALOR = object()


def _identidade_do_ator() -> int:
    """Extrai o id (int) do usuario autenticado a partir do JWT."""
    return int(get_jwt_identity())


def _resolver_perfil(payload: dict):
    """
    Resolve o Perfil informado no payload via 'perfil_id' (int) ou
    'perfil_nome' (str). Retorna (perfil, None) em caso de sucesso ou
    (None, mensagem_de_erro) em caso de falha.
    """
    perfil_id = payload.get("perfil_id")
    perfil_nome = payload.get("perfil_nome")

    if perfil_id is not None:
        if isinstance(perfil_id, bool) or not isinstance(perfil_id, int):
            return None, "Campo 'perfil_id' deve ser um numero inteiro."
        perfil = Perfil.query.get(perfil_id)
        if perfil is None:
            return None, f"Perfil com id {perfil_id} nao existe."
        return perfil, None

    if perfil_nome is not None:
        if not isinstance(perfil_nome, str) or not perfil_nome.strip():
            return None, "Campo 'perfil_nome' deve ser texto nao vazio."
        perfil = Perfil.query.filter_by(nome=perfil_nome.strip().lower()).first()
        if perfil is None:
            return None, f"Perfil '{perfil_nome}' nao existe."
        return perfil, None

    return None, "E obrigatorio informar 'perfil_id' ou 'perfil_nome'."


@usuarios_bp.get("")
@jwt_required()
@require_perfil(PERFIS_AUTORIZADOS)
def listar_usuarios():
    incluir_inativos = request.args.get("incluir_inativos", "false").strip().lower() == "true"

    query = Usuario.query
    if not incluir_inativos:
        query = query.filter_by(ativo=True)

    usuarios = query.order_by(Usuario.nome.asc()).all()
    return jsonify({"usuarios": [u.to_dict() for u in usuarios], "total": len(usuarios)}), 200


@usuarios_bp.post("")
@jwt_required()
@require_perfil(PERFIS_AUTORIZADOS)
def criar_usuario():
    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    nome = payload.get("nome")
    email = payload.get("email")
    senha = payload.get("senha")

    erros = []
    if not nome or not isinstance(nome, str) or not nome.strip():
        erros.append("Campo 'nome' e obrigatorio e deve ser texto nao vazio.")
    if not email or not isinstance(email, str) or "@" not in email:
        erros.append("Campo 'email' e obrigatorio e deve ser um e-mail valido.")
    erros.extend(
        validar_politica_senha(
            senha,
            email=email if isinstance(email, str) else None,
            nome=nome if isinstance(nome, str) else None,
        )
    )

    perfil, erro_perfil = _resolver_perfil(payload)
    if erro_perfil:
        erros.append(erro_perfil)

    profissional_id, erro_prof = _resolver_profissional(payload)
    if erro_prof:
        erros.append(erro_prof)

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    email_normalizado = email.strip().lower()
    if Usuario.query.filter_by(email=email_normalizado).first() is not None:
        return (
            jsonify(
                {"erro": f"Ja existe um usuario cadastrado com o e-mail '{email_normalizado}'."}
            ),
            400,
        )

    novo_usuario = Usuario(
        nome=nome.strip(),
        email=email_normalizado,
        senha_hash=hash_senha(senha),
        perfil_id=perfil.id,
        ativo=True,
        profissional_id=None if profissional_id is _SEM_VALOR else profissional_id,
    )

    db.session.add(novo_usuario)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="usuarios",
        registro_id=novo_usuario.id,
        antes=None,
        depois=novo_usuario.to_dict(),
    )

    return jsonify(novo_usuario.to_dict()), 201


@usuarios_bp.put("/<int:usuario_id>")
@jwt_required()
@require_perfil(PERFIS_AUTORIZADOS)
def atualizar_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if usuario is None:
        return jsonify({"erro": f"Usuario com id {usuario_id} nao encontrado."}), 404

    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    estado_antes = usuario.to_dict()
    erros = []
    encerrar_sessoes = False

    if "nome" in payload:
        nome = payload.get("nome")
        if not nome or not isinstance(nome, str) or not nome.strip():
            erros.append("Campo 'nome' deve ser texto nao vazio.")
        else:
            usuario.nome = nome.strip()

    if "email" in payload:
        email = payload.get("email")
        if not email or not isinstance(email, str) or "@" not in email:
            erros.append("Campo 'email' deve ser um e-mail valido.")
        else:
            email_normalizado = email.strip().lower()
            duplicado = Usuario.query.filter(
                Usuario.email == email_normalizado, Usuario.id != usuario.id
            ).first()
            if duplicado is not None:
                erros.append(f"Ja existe outro usuario com o e-mail '{email_normalizado}'.")
            else:
                usuario.email = email_normalizado

    if "senha" in payload:
        senha = payload.get("senha")
        problemas = validar_politica_senha(senha, email=usuario.email, nome=usuario.nome)
        if problemas:
            erros.extend(problemas)
        else:
            usuario.senha_hash = hash_senha(senha)
            encerrar_sessoes = True

    if "perfil_id" in payload or "perfil_nome" in payload:
        perfil, erro_perfil = _resolver_perfil(payload)
        if erro_perfil:
            erros.append(erro_perfil)
        else:
            if perfil.id != usuario.perfil_id:
                encerrar_sessoes = True
            usuario.perfil_id = perfil.id

    if "ativo" in payload:
        ativo = payload.get("ativo")
        if not isinstance(ativo, bool):
            erros.append("Campo 'ativo' deve ser booleano (true/false).")
        elif ativo is False and usuario.id == _identidade_do_ator():
            erros.append("Nao e permitido desativar o proprio usuario logado.")
        else:
            if usuario.ativo and not ativo:
                encerrar_sessoes = True
            usuario.ativo = ativo

    profissional_id, erro_prof = _resolver_profissional(payload)
    if erro_prof:
        erros.append(erro_prof)
    elif profissional_id is not _SEM_VALOR:
        usuario.profissional_id = profissional_id

    if erros:
        db.session.rollback()
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    if encerrar_sessoes:
        # B3: troca de senha/perfil ou desativacao derruba os tokens antigos.
        encerrar_todas_as_sessoes(usuario.id, commit=False)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="atualizar",
        tabela="usuarios",
        registro_id=usuario.id,
        antes=estado_antes,
        depois=usuario.to_dict(),
    )

    return jsonify(usuario.to_dict()), 200


@usuarios_bp.delete("/<int:usuario_id>")
@jwt_required()
@require_perfil(PERFIS_AUTORIZADOS)
def excluir_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if usuario is None:
        return jsonify({"erro": f"Usuario com id {usuario_id} nao encontrado."}), 404

    if not usuario.ativo:
        return jsonify({"erro": "Usuario ja esta inativo."}), 400

    ator_id = _identidade_do_ator()
    if usuario.id == ator_id:
        return jsonify({"erro": "Nao e permitido desativar o proprio usuario logado."}), 400

    estado_antes = usuario.to_dict()
    usuario.ativo = False
    encerrar_todas_as_sessoes(usuario.id, commit=False)
    db.session.commit()

    registrar_auditoria(
        usuario_id=ator_id,
        acao="excluir",
        tabela="usuarios",
        registro_id=usuario.id,
        antes=estado_antes,
        depois=usuario.to_dict(),
    )

    return (
        jsonify(
            {
                "mensagem": f"Usuario '{usuario.nome}' desativado com sucesso.",
                "usuario": usuario.to_dict(),
            }
        ),
        200,
    )
