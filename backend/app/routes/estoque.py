"""
Rotas de estoque (RF14): CRUD de produtos/materiais de consumo, registro de
movimentacoes de entrada/saida (com atualizacao atomica da quantidade em
estoque) e alerta de produtos abaixo da quantidade minima.

Blueprint: 'estoque', prefixo /api/v1/estoque

Observacao de design: a quantidade de um produto (produtos_estoque.quantidade)
NUNCA e alterada diretamente por PUT /estoque/<id> -- toda alteracao de
quantidade passa obrigatoriamente por POST /estoque/<id>/movimentacao, para
que exista sempre uma movimentacao (e sua respectiva trilha de auditoria)
explicando a origem de qualquer mudanca de saldo.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app.utils.security import escapar_like
from app.extensions import db
from app.models.estoque import TIPOS_MOVIMENTACAO_ESTOQUE, MovimentacaoEstoque, ProdutoEstoque
from app.utils.auth_decorators import require_perfil
from app.utils.security import registrar_auditoria

estoque_bp = Blueprint("estoque", __name__, url_prefix="/api/v1/estoque")

# Perfis autorizados a criar/alterar produtos e registrar movimentacoes.
PERFIS_ESCRITA_ESTOQUE = ["administrador", "recepcao"]
# Exclusao de produto e restrita a administrador (operacao mais sensivel,
# pode apagar historico de controle de material da clinica).
PERFIS_EXCLUSAO_ESTOQUE = ["administrador"]

TAMANHO_MAXIMO_NOME = 150
TAMANHO_MAXIMO_UNIDADE = 20
TAMANHO_MAXIMO_MOTIVO = 200


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _usuario_atual_id():
    """Extrai o id do usuario autenticado a partir do JWT, com fallback seguro."""
    try:
        identidade = get_jwt_identity()
        return int(identidade) if identidade is not None else None
    except (TypeError, ValueError, RuntimeError):
        return None


def _validar_inteiro_nao_negativo(valor, campo, obrigatorio=True, padrao=None):
    """Retorna (valor_int, None) ou (None, mensagem_de_erro)."""
    if valor is None:
        if obrigatorio:
            return None, f"Campo '{campo}' e obrigatorio e deve ser um numero inteiro."
        return padrao, None
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, f"Campo '{campo}' deve ser um numero inteiro."
    if valor < 0:
        return None, f"Campo '{campo}' nao pode ser negativo."
    return valor, None


def _validar_inteiro_positivo(valor, campo):
    """Retorna (valor_int, None) ou (None, mensagem_de_erro)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, f"Campo '{campo}' e obrigatorio e deve ser um numero inteiro."
    if valor <= 0:
        return None, f"Campo '{campo}' deve ser um numero inteiro positivo."
    return valor, None


def _validar_payload_produto(dados, parcial=False):
    """
    Valida e normaliza o payload de criacao (parcial=False) ou atualizacao
    (parcial=True) de um produto de estoque.

    Retorna (dict_normalizado, None) em caso de sucesso, ou (None, mensagem_erro).
    Nunca aceita o campo 'quantidade' -- esse saldo so muda via movimentacao.
    """
    if not isinstance(dados, dict):
        return None, "Corpo da requisicao deve ser um JSON valido."

    if "quantidade" in dados:
        return None, (
            "O campo 'quantidade' nao pode ser alterado diretamente. "
            "Use POST /api/v1/estoque/<id>/movimentacao para registrar entradas/saidas."
        )

    normalizado = {}

    if not parcial or "nome" in dados:
        nome = dados.get("nome")
        if not nome or not isinstance(nome, str) or not nome.strip():
            return None, "O campo 'nome' e obrigatorio e deve ser um texto nao vazio."
        if len(nome.strip()) > TAMANHO_MAXIMO_NOME:
            return None, f"O campo 'nome' deve ter no maximo {TAMANHO_MAXIMO_NOME} caracteres."
        normalizado["nome"] = nome.strip()

    if not parcial or "unidade" in dados:
        unidade = dados.get("unidade")
        if not unidade or not isinstance(unidade, str) or not unidade.strip():
            return None, "O campo 'unidade' e obrigatorio e deve ser um texto nao vazio (ex.: 'un', 'caixa', 'ml')."
        if len(unidade.strip()) > TAMANHO_MAXIMO_UNIDADE:
            return None, f"O campo 'unidade' deve ter no maximo {TAMANHO_MAXIMO_UNIDADE} caracteres."
        normalizado["unidade"] = unidade.strip()

    if "quantidade_minima" in dados or not parcial:
        valor_bruto = dados.get("quantidade_minima", 0 if not parcial else None)
        if valor_bruto is None:
            valor_bruto = 0
        quantidade_minima, erro = _validar_inteiro_nao_negativo(
            valor_bruto, "quantidade_minima", obrigatorio=False, padrao=0
        )
        if erro:
            return None, erro
        normalizado["quantidade_minima"] = quantidade_minima

    return normalizado, None


# ---------------------------------------------------------------------------
# CRUD de produtos (RF14)
# ---------------------------------------------------------------------------


@estoque_bp.get("")
@jwt_required()
def listar_produtos():
    """Lista produtos do estoque, com busca opcional por nome (?q=)."""
    termo_busca = (request.args.get("q") or "").strip()

    query = ProdutoEstoque.query
    if termo_busca:
        query = query.filter(ProdutoEstoque.nome.ilike(f"%{escapar_like(termo_busca)}%", escape="\\"))

    produtos = query.order_by(ProdutoEstoque.nome.asc()).all()
    return jsonify({
        "dados": [p.to_dict() for p in produtos],
        "total": len(produtos),
    }), 200


@estoque_bp.get("/alertas")
@jwt_required()
def listar_alertas_estoque():
    """
    Retorna os produtos cuja quantidade atual esta no ou abaixo da
    quantidade minima definida (RF14 -- alerta de reposicao de estoque).
    """
    produtos = (
        ProdutoEstoque.query.filter(ProdutoEstoque.quantidade <= ProdutoEstoque.quantidade_minima)
        .order_by(ProdutoEstoque.nome.asc())
        .all()
    )
    return jsonify({
        "dados": [p.to_dict() for p in produtos],
        "total": len(produtos),
    }), 200


@estoque_bp.get("/<int:produto_id>")
@jwt_required()
def obter_produto(produto_id):
    produto = ProdutoEstoque.query.get(produto_id)
    if produto is None:
        return _erro("Produto de estoque nao encontrado.", 404)
    return jsonify(produto.to_dict()), 200


@estoque_bp.post("")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_ESTOQUE)
def criar_produto():
    dados = request.get_json(silent=True)
    normalizado, erro = _validar_payload_produto(dados, parcial=False)
    if erro:
        return _erro(erro, 400)

    produto = ProdutoEstoque(
        nome=normalizado["nome"],
        unidade=normalizado["unidade"],
        quantidade_minima=normalizado["quantidade_minima"],
        quantidade=0,
    )

    try:
        db.session.add(produto)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="criar",
            tabela="produtos_estoque",
            registro_id=produto.id,
            antes=None,
            depois=produto.to_dict(),
        )
    except IntegrityError:
        db.session.rollback()
        return _erro("Nao foi possivel cadastrar o produto devido a dados invalidos.", 400)

    return jsonify(produto.to_dict()), 201


@estoque_bp.put("/<int:produto_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_ESTOQUE)
def atualizar_produto(produto_id):
    produto = ProdutoEstoque.query.get(produto_id)
    if produto is None:
        return _erro("Produto de estoque nao encontrado.", 404)

    dados = request.get_json(silent=True)
    normalizado, erro = _validar_payload_produto(dados, parcial=True)
    if erro:
        return _erro(erro, 400)
    if not normalizado:
        return _erro("Nenhum campo valido informado para atualizacao.", 400)

    estado_antes = produto.to_dict()
    for campo, valor in normalizado.items():
        setattr(produto, campo, valor)

    try:
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="atualizar",
            tabela="produtos_estoque",
            registro_id=produto.id,
            antes=estado_antes,
            depois=produto.to_dict(),
        )
    except IntegrityError:
        db.session.rollback()
        return _erro("Nao foi possivel atualizar o produto devido a dados invalidos.", 400)

    return jsonify(produto.to_dict()), 200


@estoque_bp.delete("/<int:produto_id>")
@jwt_required()
@require_perfil(PERFIS_EXCLUSAO_ESTOQUE)
def excluir_produto(produto_id):
    produto = ProdutoEstoque.query.get(produto_id)
    if produto is None:
        return _erro("Produto de estoque nao encontrado.", 404)

    estado_antes = produto.to_dict()
    db.session.delete(produto)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="excluir",
        tabela="produtos_estoque",
        registro_id=produto_id,
        antes=estado_antes,
        depois=None,
    )

    return jsonify({"mensagem": "Produto de estoque excluido com sucesso."}), 200


# ---------------------------------------------------------------------------
# Movimentacoes de entrada/saida (RF14)
# ---------------------------------------------------------------------------


@estoque_bp.post("/<int:produto_id>/movimentacao")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_ESTOQUE)
def registrar_movimentacao(produto_id):
    """
    Registra uma movimentacao de entrada ou saida para o produto informado
    e atualiza atomicamente produtos_estoque.quantidade.

    Payload esperado:
        {
            "tipo": "entrada" | "saida",
            "quantidade": <inteiro positivo>,
            "motivo": "<texto opcional>"
        }
    """
    produto = ProdutoEstoque.query.get(produto_id)
    if produto is None:
        return _erro("Produto de estoque nao encontrado.", 404)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []

    tipo = dados.get("tipo")
    if tipo not in TIPOS_MOVIMENTACAO_ESTOQUE:
        erros.append(
            f"Campo 'tipo' e obrigatorio. Valores aceitos: {', '.join(TIPOS_MOVIMENTACAO_ESTOQUE)}."
        )

    quantidade, erro_quantidade = _validar_inteiro_positivo(dados.get("quantidade"), "quantidade")
    if erro_quantidade:
        erros.append(erro_quantidade)

    motivo = dados.get("motivo")
    if motivo is not None:
        if not isinstance(motivo, str):
            erros.append("O campo 'motivo', quando informado, deve ser um texto.")
        elif len(motivo.strip()) > TAMANHO_MAXIMO_MOTIVO:
            erros.append(f"O campo 'motivo' deve ter no maximo {TAMANHO_MAXIMO_MOTIVO} caracteres.")

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    motivo_normalizado = motivo.strip() if isinstance(motivo, str) and motivo.strip() else None

    if tipo == "saida" and quantidade > produto.quantidade:
        return _erro(
            f"Estoque insuficiente: quantidade atual do produto e {produto.quantidade}, "
            f"mas foi solicitada uma saida de {quantidade}.",
            400,
        )

    estado_produto_antes = produto.to_dict()

    movimentacao = MovimentacaoEstoque(
        produto_id=produto.id,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo_normalizado,
    )
    db.session.add(movimentacao)

    if tipo == "entrada":
        produto.quantidade += quantidade
    else:
        produto.quantidade -= quantidade

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return _erro("Nao foi possivel registrar a movimentacao devido a dados invalidos.", 400)

    ator_id = _usuario_atual_id()

    registrar_auditoria(
        usuario_id=ator_id,
        acao="criar",
        tabela="movimentacoes_estoque",
        registro_id=movimentacao.id,
        antes=None,
        depois=movimentacao.to_dict(),
    )
    registrar_auditoria(
        usuario_id=ator_id,
        acao="atualizar",
        tabela="produtos_estoque",
        registro_id=produto.id,
        antes=estado_produto_antes,
        depois=produto.to_dict(),
    )

    return jsonify({
        "produto": produto.to_dict(),
        "movimentacao": movimentacao.to_dict(),
    }), 201
