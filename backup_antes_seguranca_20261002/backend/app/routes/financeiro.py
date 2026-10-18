"""
Blueprint 'financeiro' -- orcamento e financeiro (RF08-RF13).

Rotas expostas sob o prefixo /api/v1:
    Procedimentos (catalogo)
        GET    /api/v1/procedimentos
        GET    /api/v1/procedimentos/<id>
        POST   /api/v1/procedimentos
        PUT    /api/v1/procedimentos/<id>
        DELETE /api/v1/procedimentos/<id>

    Convenios e tabela de precos negociados
        GET    /api/v1/convenios
        GET    /api/v1/convenios/<id>
        POST   /api/v1/convenios
        PUT    /api/v1/convenios/<id>
        DELETE /api/v1/convenios/<id>
        GET    /api/v1/convenios/<convenio_id>/precos
        POST   /api/v1/convenios/<convenio_id>/precos
        PUT    /api/v1/convenios/<convenio_id>/precos/<preco_id>
        DELETE /api/v1/convenios/<convenio_id>/precos/<preco_id>

    Orcamentos e plano de tratamento
        GET  /api/v1/orcamentos
        GET  /api/v1/orcamentos/<id>
        POST /api/v1/orcamentos                 -> calcula total a partir dos itens
        POST /api/v1/orcamentos/<id>/aprovar     -> gera plano_tratamento + contas_receber
        POST /api/v1/orcamentos/<id>/recusar

    Contas a pagar
        GET    /api/v1/contas-pagar
        POST   /api/v1/contas-pagar
        PUT    /api/v1/contas-pagar/<id>
        DELETE /api/v1/contas-pagar/<id>

    Contas a receber (somente leitura -- geradas via aprovacao de orcamento)
        GET /api/v1/contas-receber

    Pagamentos e comissoes
        GET  /api/v1/pagamentos
        POST /api/v1/pagamentos    -> baixa conta_receber e gera comissao_profissional
        GET  /api/v1/comissoes

    Dashboard
        GET /api/v1/financeiro/resumo

Todas as rotas de leitura exigem JWT valido. Todas as rotas de escrita
exigem JWT valido + perfil autorizado (require_perfil). Toda escrita em
orcamentos, orcamento_itens, planos_tratamento, contas_receber,
contas_pagar, pagamentos e comissoes_profissionais chama
registrar_auditoria (grava em log_auditoria), por se tratar de dados
financeiros sensiveis -- pagamentos em particular e uma das tabelas
explicitamente exigidas pelo padrao do time.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models.financeiro import (
    ComissaoProfissional,
    ContaPagar,
    ContaReceber,
    Convenio,
    Orcamento,
    OrcamentoItem,
    Pagamento,
    PlanoTratamento,
    Procedimento,
    TabelaPrecosConvenio,
)
from app.utils.auth_decorators import require_perfil
from app.utils.security import registrar_auditoria

financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------
# Constantes de dominio
# ---------------------------------------------------------------------------

PERFIS_ESCRITA_PROCEDIMENTOS = ["administrador", "financeiro"]
PERFIS_ESCRITA_CONVENIO = ["administrador", "financeiro"]
PERFIS_ESCRITA_ORCAMENTO = ["administrador", "financeiro", "recepcao"]
PERFIS_APROVACAO_ORCAMENTO = ["administrador", "financeiro"]
PERFIS_ESCRITA_CONTA_PAGAR = ["administrador", "financeiro"]
PERFIS_ESCRITA_PAGAMENTO = ["administrador", "financeiro"]
PERFIS_DASHBOARD_FINANCEIRO = ["administrador", "financeiro"]

# Percentual de comissao padrao (%) usado quando nao ha configuracao
# especifica em configuracoes_clinica (chave 'comissao_percentual_padrao')
# nem override explicito no payload de POST /pagamentos.
DEFAULT_PERCENTUAL_COMISSAO = Decimal("30.00")

TAMANHO_CENTAVOS = Decimal("0.01")
MAX_PARCELAS = 60


# ---------------------------------------------------------------------------
# Helpers genericos
# ---------------------------------------------------------------------------


def _erro(mensagem, status=400, detalhes=None):
    corpo = {"erro": mensagem}
    if detalhes:
        corpo["detalhes"] = detalhes
    return jsonify(corpo), status


def _identidade_do_ator():
    """Extrai o id (int) do usuario autenticado a partir do JWT, com fallback seguro."""
    try:
        identidade = get_jwt_identity()
        return int(identidade) if identidade is not None else None
    except (TypeError, ValueError, RuntimeError):
        return None


def _paciente_existe(paciente_id) -> bool:
    """
    Verifica se o paciente existe, via consulta parametrizada (sem
    concatenacao de string). O model Paciente pertence a outro modulo
    do sistema, por isso a checagem e feita diretamente na tabela,
    seguindo o mesmo padrao usado em app/routes/clinico.py.
    """
    resultado = db.session.execute(
        db.text("SELECT id FROM pacientes WHERE id = :paciente_id"),
        {"paciente_id": paciente_id},
    ).first()
    return resultado is not None


def _profissional_existe(profissional_id) -> bool:
    """Verifica se o profissional existe e esta ativo, via consulta parametrizada."""
    resultado = db.session.execute(
        db.text(
            "SELECT id FROM profissionais WHERE id = :profissional_id AND ativo = 1"
        ),
        {"profissional_id": profissional_id},
    ).first()
    return resultado is not None


def _obter_percentual_comissao_padrao() -> Decimal:
    """
    Le o percentual de comissao configuravel a partir da tabela
    configuracoes_clinica (chave 'comissao_percentual_padrao'), via
    consulta parametrizada. Se a chave nao existir, o valor for invalido,
    ou a consulta falhar por qualquer motivo (ex.: tabela ainda nao
    provisionada no ambiente), usa DEFAULT_PERCENTUAL_COMISSAO como
    fallback seguro -- a geracao da comissao nunca deve ser bloqueada por
    uma falha de leitura de configuracao.

    A leitura roda dentro de um SAVEPOINT (begin_nested): esta funcao e
    chamada no meio da transacao de POST /pagamentos, depois que o
    pagamento e a baixa da conta_receber ja foram enviados ao banco
    (flush) mas ainda nao commitados -- se a leitura falhar, so o
    SAVEPOINT e desfeito, preservando as alteracoes pendentes da
    transacao externa (que serao commitadas normalmente pelo chamador).
    """
    try:
        with db.session.begin_nested():
            resultado = db.session.execute(
                db.text(
                    "SELECT valor FROM configuracoes_clinica WHERE chave = :chave"
                ),
                {"chave": "comissao_percentual_padrao"},
            ).first()
    except SQLAlchemyError:
        return DEFAULT_PERCENTUAL_COMISSAO

    if resultado is None or resultado[0] is None:
        return DEFAULT_PERCENTUAL_COMISSAO
    try:
        percentual = Decimal(str(resultado[0]))
    except (InvalidOperation, TypeError, ValueError):
        return DEFAULT_PERCENTUAL_COMISSAO
    if percentual <= 0 or percentual > 100:
        return DEFAULT_PERCENTUAL_COMISSAO
    return percentual


def _validar_inteiro_positivo(valor, nome_campo):
    """Retorna (valor_int, None) ou (None, mensagem_de_erro)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, f"Campo '{nome_campo}' e obrigatorio e deve ser um numero inteiro."
    if valor <= 0:
        return None, f"Campo '{nome_campo}' deve ser um numero inteiro positivo."
    return valor, None


def _validar_decimal(valor, nome_campo, permitir_zero=True, obrigatorio=True):
    """
    Converte um valor recebido em JSON (int, float ou str) para Decimal,
    validando que e um numero positivo (ou nao-negativo, se permitir_zero).

    Retorna (Decimal, None) em caso de sucesso, ou (None, mensagem_erro).
    """
    if valor is None:
        if obrigatorio:
            return None, f"Campo '{nome_campo}' e obrigatorio."
        return None, None

    if isinstance(valor, bool):
        return None, f"Campo '{nome_campo}' deve ser um numero."

    try:
        decimal_valor = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None, f"Campo '{nome_campo}' deve ser um numero valido."

    if decimal_valor.is_nan() or decimal_valor.is_infinite():
        return None, f"Campo '{nome_campo}' deve ser um numero valido."

    if permitir_zero and decimal_valor < 0:
        return None, f"Campo '{nome_campo}' nao pode ser negativo."
    if not permitir_zero and decimal_valor <= 0:
        return None, f"Campo '{nome_campo}' deve ser maior que zero."

    return decimal_valor.quantize(TAMANHO_CENTAVOS, rounding=ROUND_HALF_UP), None


def _parse_data(valor, nome_campo, obrigatorio=True, permitir_passado=True):
    """Converte uma string 'AAAA-MM-DD' para date. Retorna (date, None) ou (None, erro)."""
    if not valor:
        if obrigatorio:
            return None, f"Campo '{nome_campo}' e obrigatorio (formato AAAA-MM-DD)."
        return None, None
    if not isinstance(valor, str):
        return None, f"Campo '{nome_campo}' deve ser uma string no formato AAAA-MM-DD."
    try:
        data_convertida = datetime.strptime(valor.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None, f"Campo '{nome_campo}' e invalido. Use o formato AAAA-MM-DD."
    if not permitir_passado and data_convertida < date.today():
        return None, f"Campo '{nome_campo}' nao pode ser uma data no passado."
    return data_convertida, None


def _paginar(query, model_to_dict):
    pagina = request.args.get("pagina", 1, type=int) or 1
    por_pagina = request.args.get("por_pagina", 20, type=int) or 20
    por_pagina = min(max(por_pagina, 1), 100)

    paginacao = query.paginate(page=pagina, per_page=por_pagina, error_out=False)
    return {
        "dados": [model_to_dict(item) for item in paginacao.items],
        "pagina": paginacao.page,
        "por_pagina": paginacao.per_page,
        "total": paginacao.total,
        "total_paginas": paginacao.pages,
    }


def _mensagem_integridade(exc, mensagem_padrao):
    """Traduz erros de integridade do banco (FK/UNIQUE) em mensagens claras."""
    texto = str(getattr(exc, "orig", exc)).lower()
    if "unique" in texto or "duplicate" in texto:
        return "Ja existe um registro com esses dados (violacao de restricao unica)."
    if "foreign key" in texto or "fk_" in texto:
        return "Operacao viola uma referencia obrigatoria (chave estrangeira). Verifique os ids informados."
    return mensagem_padrao


# ---------------------------------------------------------------------------
# Procedimentos (catalogo) -- CRUD
# ---------------------------------------------------------------------------


@financeiro_bp.get("/procedimentos")
@jwt_required()
def listar_procedimentos():
    termo_busca = (request.args.get("q") or "").strip()
    query = Procedimento.query
    if termo_busca:
        query = query.filter(Procedimento.nome.ilike(f"%{termo_busca}%"))
    query = query.order_by(Procedimento.nome.asc())
    return jsonify(_paginar(query, lambda p: p.to_dict())), 200


@financeiro_bp.get("/procedimentos/<int:procedimento_id>")
@jwt_required()
def obter_procedimento(procedimento_id):
    procedimento = Procedimento.query.get(procedimento_id)
    if procedimento is None:
        return _erro("Procedimento nao encontrado.", 404)
    return jsonify(procedimento.to_dict()), 200


@financeiro_bp.post("/procedimentos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PROCEDIMENTOS)
def criar_procedimento():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []
    nome = payload.get("nome")
    if not nome or not isinstance(nome, str) or not nome.strip():
        erros.append("Campo 'nome' e obrigatorio e deve ser texto nao vazio.")

    preco, erro_preco = _validar_decimal(
        payload.get("preco", 0), "preco", permitir_zero=True, obrigatorio=False
    )
    if erro_preco:
        erros.append(erro_preco)
    if preco is None:
        preco = Decimal("0.00")

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    procedimento = Procedimento(nome=nome.strip(), preco=preco)
    db.session.add(procedimento)
    db.session.flush()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="procedimentos",
        registro_id=procedimento.id,
        antes=None,
        depois=procedimento.to_dict(),
    )
    db.session.commit()

    return jsonify(procedimento.to_dict()), 201


@financeiro_bp.put("/procedimentos/<int:procedimento_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PROCEDIMENTOS)
def atualizar_procedimento(procedimento_id):
    procedimento = Procedimento.query.get(procedimento_id)
    if procedimento is None:
        return _erro("Procedimento nao encontrado.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []
    estado_antes = procedimento.to_dict()

    if "nome" in payload:
        nome = payload.get("nome")
        if not nome or not isinstance(nome, str) or not nome.strip():
            erros.append("Campo 'nome' nao pode ser vazio.")
        else:
            procedimento.nome = nome.strip()

    if "preco" in payload:
        preco, erro_preco = _validar_decimal(
            payload.get("preco"), "preco", permitir_zero=True, obrigatorio=True
        )
        if erro_preco:
            erros.append(erro_preco)
        else:
            procedimento.preco = preco

    if erros:
        db.session.rollback()
        return _erro("Dados invalidos.", 400, erros)

    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="atualizar",
        tabela="procedimentos",
        registro_id=procedimento.id,
        antes=estado_antes,
        depois=procedimento.to_dict(),
    )
    db.session.commit()

    return jsonify(procedimento.to_dict()), 200


@financeiro_bp.delete("/procedimentos/<int:procedimento_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PROCEDIMENTOS)
def excluir_procedimento(procedimento_id):
    procedimento = Procedimento.query.get(procedimento_id)
    if procedimento is None:
        return _erro("Procedimento nao encontrado.", 404)

    estado_antes = procedimento.to_dict()
    try:
        db.session.delete(procedimento)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_identidade_do_ator(),
            acao="excluir",
            tabela="procedimentos",
            registro_id=procedimento_id,
            antes=estado_antes,
            depois=None,
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _erro(
            "Nao e possivel excluir este procedimento pois existem itens de "
            "orcamento ou precos de convenio vinculados a ele.",
            409,
        )

    return jsonify({"mensagem": "Procedimento excluido com sucesso."}), 200


# ---------------------------------------------------------------------------
# Convenios e tabela de precos negociados (RF10)
# ---------------------------------------------------------------------------


@financeiro_bp.get("/convenios")
@jwt_required()
def listar_convenios():
    query = Convenio.query.order_by(Convenio.nome.asc())
    return jsonify(_paginar(query, lambda c: c.to_dict())), 200


@financeiro_bp.get("/convenios/<int:convenio_id>")
@jwt_required()
def obter_convenio(convenio_id):
    convenio = Convenio.query.get(convenio_id)
    if convenio is None:
        return _erro("Convenio nao encontrado.", 404)
    dados = convenio.to_dict()
    dados["tabela_precos"] = [p.to_dict() for p in convenio.tabela_precos]
    return jsonify(dados), 200


@financeiro_bp.post("/convenios")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def criar_convenio():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    nome = payload.get("nome")
    if not nome or not isinstance(nome, str) or not nome.strip():
        return _erro("Campo 'nome' e obrigatorio e deve ser texto nao vazio.", 400)

    convenio = Convenio(nome=nome.strip())
    try:
        db.session.add(convenio)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_identidade_do_ator(),
            acao="criar",
            tabela="convenios",
            registro_id=convenio.id,
            antes=None,
            depois=convenio.to_dict(),
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        return _erro(_mensagem_integridade(exc, "Nao foi possivel cadastrar o convenio."), 400)

    return jsonify(convenio.to_dict()), 201


@financeiro_bp.put("/convenios/<int:convenio_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def atualizar_convenio(convenio_id):
    convenio = Convenio.query.get(convenio_id)
    if convenio is None:
        return _erro("Convenio nao encontrado.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    nome = payload.get("nome")
    if not nome or not isinstance(nome, str) or not nome.strip():
        return _erro("Campo 'nome' e obrigatorio e deve ser texto nao vazio.", 400)

    estado_antes = convenio.to_dict()
    convenio.nome = nome.strip()

    try:
        db.session.flush()
        registrar_auditoria(
            usuario_id=_identidade_do_ator(),
            acao="atualizar",
            tabela="convenios",
            registro_id=convenio.id,
            antes=estado_antes,
            depois=convenio.to_dict(),
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        return _erro(_mensagem_integridade(exc, "Nao foi possivel atualizar o convenio."), 400)

    return jsonify(convenio.to_dict()), 200


@financeiro_bp.delete("/convenios/<int:convenio_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def excluir_convenio(convenio_id):
    convenio = Convenio.query.get(convenio_id)
    if convenio is None:
        return _erro("Convenio nao encontrado.", 404)

    estado_antes = convenio.to_dict()
    db.session.delete(convenio)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="excluir",
        tabela="convenios",
        registro_id=convenio_id,
        antes=estado_antes,
        depois=None,
    )
    db.session.commit()

    return jsonify({"mensagem": "Convenio excluido com sucesso."}), 200


@financeiro_bp.get("/convenios/<int:convenio_id>/precos")
@jwt_required()
def listar_precos_convenio(convenio_id):
    convenio = Convenio.query.get(convenio_id)
    if convenio is None:
        return _erro("Convenio nao encontrado.", 404)
    return jsonify([p.to_dict() for p in convenio.tabela_precos]), 200


@financeiro_bp.post("/convenios/<int:convenio_id>/precos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def criar_preco_convenio(convenio_id):
    convenio = Convenio.query.get(convenio_id)
    if convenio is None:
        return _erro("Convenio nao encontrado.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []
    procedimento_id, erro = _validar_inteiro_positivo(
        payload.get("procedimento_id"), "procedimento_id"
    )
    if erro:
        erros.append(erro)
    elif Procedimento.query.get(procedimento_id) is None:
        erros.append(f"Procedimento com id {procedimento_id} nao encontrado.")

    preco, erro_preco = _validar_decimal(
        payload.get("preco"), "preco", permitir_zero=False, obrigatorio=True
    )
    if erro_preco:
        erros.append(erro_preco)

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    preco_convenio = TabelaPrecosConvenio(
        convenio_id=convenio.id, procedimento_id=procedimento_id, preco=preco
    )
    try:
        db.session.add(preco_convenio)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_identidade_do_ator(),
            acao="criar",
            tabela="tabela_precos_convenio",
            registro_id=preco_convenio.id,
            antes=None,
            depois=preco_convenio.to_dict(),
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _erro(
            "Ja existe um preco cadastrado para este procedimento neste convenio. "
            "Utilize PUT para atualiza-lo.",
            409,
        )

    return jsonify(preco_convenio.to_dict()), 201


@financeiro_bp.put("/convenios/<int:convenio_id>/precos/<int:preco_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def atualizar_preco_convenio(convenio_id, preco_id):
    preco_convenio = TabelaPrecosConvenio.query.filter_by(
        id=preco_id, convenio_id=convenio_id
    ).first()
    if preco_convenio is None:
        return _erro("Preco de convenio nao encontrado.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    preco, erro_preco = _validar_decimal(
        payload.get("preco"), "preco", permitir_zero=False, obrigatorio=True
    )
    if erro_preco:
        return _erro(erro_preco, 400)

    estado_antes = preco_convenio.to_dict()
    preco_convenio.preco = preco
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="atualizar",
        tabela="tabela_precos_convenio",
        registro_id=preco_convenio.id,
        antes=estado_antes,
        depois=preco_convenio.to_dict(),
    )
    db.session.commit()

    return jsonify(preco_convenio.to_dict()), 200


@financeiro_bp.delete("/convenios/<int:convenio_id>/precos/<int:preco_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONVENIO)
def excluir_preco_convenio(convenio_id, preco_id):
    preco_convenio = TabelaPrecosConvenio.query.filter_by(
        id=preco_id, convenio_id=convenio_id
    ).first()
    if preco_convenio is None:
        return _erro("Preco de convenio nao encontrado.", 404)

    estado_antes = preco_convenio.to_dict()
    db.session.delete(preco_convenio)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="excluir",
        tabela="tabela_precos_convenio",
        registro_id=preco_id,
        antes=estado_antes,
        depois=None,
    )
    db.session.commit()

    return jsonify({"mensagem": "Preco de convenio excluido com sucesso."}), 200


# ---------------------------------------------------------------------------
# Orcamentos e plano de tratamento (RF08, RF09)
# ---------------------------------------------------------------------------


def _validar_itens_orcamento(itens_brutos):
    """
    Valida a lista de itens de um orcamento (procedimento_id + quantidade).

    Retorna (lista_validada, None) ou (None, lista_de_erros). Cada item
    validado e um dict {"procedimento_id": int, "quantidade": int}.
    """
    if not isinstance(itens_brutos, list) or not itens_brutos:
        return None, ["Campo 'itens' e obrigatorio e deve ser uma lista nao vazia."]

    erros = []
    itens_validados = []
    for indice, item in enumerate(itens_brutos):
        if not isinstance(item, dict):
            erros.append(f"Item {indice}: deve ser um objeto JSON.")
            continue

        procedimento_id, erro = _validar_inteiro_positivo(
            item.get("procedimento_id"), "procedimento_id"
        )
        if erro:
            erros.append(f"Item {indice}: {erro}")
            continue

        quantidade_bruta = item.get("quantidade", 1)
        if isinstance(quantidade_bruta, bool) or not isinstance(quantidade_bruta, int):
            erros.append(f"Item {indice}: campo 'quantidade' deve ser um numero inteiro.")
            continue
        if quantidade_bruta <= 0:
            erros.append(f"Item {indice}: campo 'quantidade' deve ser maior que zero.")
            continue

        itens_validados.append(
            {"procedimento_id": procedimento_id, "quantidade": quantidade_bruta}
        )

    if erros:
        return None, erros
    return itens_validados, None


@financeiro_bp.get("/orcamentos")
@jwt_required()
def listar_orcamentos():
    query = Orcamento.query

    paciente_id = request.args.get("paciente_id", type=int)
    if paciente_id is not None:
        query = query.filter(Orcamento.paciente_id == paciente_id)

    status = (request.args.get("status") or "").strip()
    if status:
        if status not in Orcamento.STATUS_VALIDOS:
            return _erro(
                f"Status invalido. Valores aceitos: {', '.join(Orcamento.STATUS_VALIDOS)}.", 400
            )
        query = query.filter(Orcamento.status == status)

    query = query.order_by(Orcamento.criado_em.desc())
    return jsonify(_paginar(query, lambda o: o.to_dict())), 200


@financeiro_bp.get("/orcamentos/<int:orcamento_id>")
@jwt_required()
def obter_orcamento(orcamento_id):
    orcamento = Orcamento.query.get(orcamento_id)
    if orcamento is None:
        return _erro("Orcamento nao encontrado.", 404)
    return jsonify(orcamento.to_dict(incluir_itens=True)), 200


@financeiro_bp.post("/orcamentos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_ORCAMENTO)
def criar_orcamento():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []

    paciente_id, erro = _validar_inteiro_positivo(payload.get("paciente_id"), "paciente_id")
    if erro:
        erros.append(erro)
    elif not _paciente_existe(paciente_id):
        erros.append(f"Paciente com id {paciente_id} nao encontrado.")

    convenio_id = payload.get("convenio_id")
    if convenio_id is not None:
        convenio_id, erro_convenio = _validar_inteiro_positivo(convenio_id, "convenio_id")
        if erro_convenio:
            erros.append(erro_convenio)
        elif Convenio.query.get(convenio_id) is None:
            erros.append(f"Convenio com id {convenio_id} nao encontrado.")

    itens_validados, erros_itens = _validar_itens_orcamento(payload.get("itens"))
    if erros_itens:
        erros.extend(erros_itens)

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    # Busca todos os procedimentos referenciados em uma unica consulta,
    # via ORM (sem concatenacao de string), para validar existencia e
    # obter os precos de catalogo.
    procedimento_ids = {item["procedimento_id"] for item in itens_validados}
    procedimentos = {
        p.id: p for p in Procedimento.query.filter(Procedimento.id.in_(procedimento_ids)).all()
    }
    faltantes = procedimento_ids - set(procedimentos.keys())
    if faltantes:
        return _erro(
            "Um ou mais procedimentos informados nao existem.",
            400,
            [f"procedimento_id {pid} nao encontrado." for pid in sorted(faltantes)],
        )

    # Se um convenio foi informado, busca os precos negociados para os
    # procedimentos do orcamento; caso um procedimento nao tenha preco
    # negociado, usa o preco de catalogo como fallback.
    precos_convenio = {}
    if convenio_id is not None:
        precos_convenio = {
            tp.procedimento_id: tp.preco
            for tp in TabelaPrecosConvenio.query.filter(
                TabelaPrecosConvenio.convenio_id == convenio_id,
                TabelaPrecosConvenio.procedimento_id.in_(procedimento_ids),
            ).all()
        }

    total = Decimal("0.00")
    itens_para_criar = []
    for item in itens_validados:
        procedimento = procedimentos[item["procedimento_id"]]
        valor_unit = precos_convenio.get(item["procedimento_id"], procedimento.preco)
        valor_unit = Decimal(str(valor_unit)).quantize(TAMANHO_CENTAVOS, rounding=ROUND_HALF_UP)
        total += valor_unit * item["quantidade"]
        itens_para_criar.append(
            {
                "procedimento_id": item["procedimento_id"],
                "quantidade": item["quantidade"],
                "valor_unit": valor_unit,
            }
        )

    orcamento = Orcamento(paciente_id=paciente_id, status="pendente", total=total)
    db.session.add(orcamento)
    db.session.flush()  # obtem orcamento.id para os itens

    for item in itens_para_criar:
        db.session.add(
            OrcamentoItem(
                orcamento_id=orcamento.id,
                procedimento_id=item["procedimento_id"],
                quantidade=item["quantidade"],
                valor_unit=item["valor_unit"],
            )
        )
    db.session.flush()

    dados_orcamento = orcamento.to_dict(incluir_itens=True)
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="orcamentos",
        registro_id=orcamento.id,
        antes=None,
        depois=dados_orcamento,
    )
    db.session.commit()

    return jsonify(dados_orcamento), 201


@financeiro_bp.post("/orcamentos/<int:orcamento_id>/aprovar")
@jwt_required()
@require_perfil(PERFIS_APROVACAO_ORCAMENTO)
def aprovar_orcamento(orcamento_id):
    orcamento = Orcamento.query.get(orcamento_id)
    if orcamento is None:
        return _erro("Orcamento nao encontrado.", 404)
    if orcamento.status != "pendente":
        return _erro(
            f"Orcamento nao pode ser aprovado: status atual e '{orcamento.status}' "
            "(somente orcamentos 'pendente' podem ser aprovados).",
            400,
        )

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []

    parcelas = payload.get("parcelas", 1)
    if isinstance(parcelas, bool) or not isinstance(parcelas, int):
        erros.append("Campo 'parcelas' deve ser um numero inteiro.")
    elif parcelas <= 0 or parcelas > MAX_PARCELAS:
        erros.append(f"Campo 'parcelas' deve ser um inteiro entre 1 e {MAX_PARCELAS}.")

    intervalo_dias = payload.get("intervalo_dias", 30)
    if isinstance(intervalo_dias, bool) or not isinstance(intervalo_dias, int):
        erros.append("Campo 'intervalo_dias' deve ser um numero inteiro.")
    elif intervalo_dias <= 0:
        erros.append("Campo 'intervalo_dias' deve ser maior que zero.")

    primeiro_vencimento, erro_data = _parse_data(
        payload.get("primeiro_vencimento"), "primeiro_vencimento", obrigatorio=False
    )
    if erro_data:
        erros.append(erro_data)
    if primeiro_vencimento is None:
        primeiro_vencimento = date.today()

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    # Divide o total do orcamento em N parcelas iguais, ajustando a
    # ultima parcela para absorver eventuais centavos de arredondamento
    # (garante que a soma das parcelas seja exatamente igual ao total).
    total = orcamento.total
    valor_parcela_base = (total / parcelas).quantize(TAMANHO_CENTAVOS, rounding=ROUND_HALF_UP)
    valores_parcelas = [valor_parcela_base] * parcelas
    diferenca = total - (valor_parcela_base * parcelas)
    valores_parcelas[-1] = (valores_parcelas[-1] + diferenca).quantize(
        TAMANHO_CENTAVOS, rounding=ROUND_HALF_UP
    )

    estado_antes_orcamento = orcamento.to_dict()
    orcamento.status = "aprovado"

    plano = PlanoTratamento(
        orcamento_id=orcamento.id,
        paciente_id=orcamento.paciente_id,
        status="planejado",
        iniciado_em=datetime.utcnow(),
    )
    db.session.add(plano)
    db.session.flush()

    contas_criadas = []
    for indice, valor_parcela in enumerate(valores_parcelas):
        vencimento = primeiro_vencimento + timedelta(days=intervalo_dias * indice)
        conta = ContaReceber(
            orcamento_id=orcamento.id,
            paciente_id=orcamento.paciente_id,
            valor=valor_parcela,
            vencimento=vencimento,
            status="pendente",
        )
        db.session.add(conta)
        contas_criadas.append(conta)
    db.session.flush()

    ator_id = _identidade_do_ator()

    registrar_auditoria(
        usuario_id=ator_id,
        acao="atualizar",
        tabela="orcamentos",
        registro_id=orcamento.id,
        antes=estado_antes_orcamento,
        depois=orcamento.to_dict(),
    )
    registrar_auditoria(
        usuario_id=ator_id,
        acao="criar",
        tabela="planos_tratamento",
        registro_id=plano.id,
        antes=None,
        depois=plano.to_dict(),
    )
    for conta in contas_criadas:
        registrar_auditoria(
            usuario_id=ator_id,
            acao="criar",
            tabela="contas_receber",
            registro_id=conta.id,
            antes=None,
            depois=conta.to_dict(),
        )

    db.session.commit()

    return (
        jsonify(
            {
                "orcamento": orcamento.to_dict(),
                "plano_tratamento": plano.to_dict(),
                "contas_receber": [c.to_dict() for c in contas_criadas],
            }
        ),
        200,
    )


@financeiro_bp.post("/orcamentos/<int:orcamento_id>/recusar")
@jwt_required()
@require_perfil(PERFIS_APROVACAO_ORCAMENTO)
def recusar_orcamento(orcamento_id):
    orcamento = Orcamento.query.get(orcamento_id)
    if orcamento is None:
        return _erro("Orcamento nao encontrado.", 404)
    if orcamento.status != "pendente":
        return _erro(
            f"Orcamento nao pode ser recusado: status atual e '{orcamento.status}' "
            "(somente orcamentos 'pendente' podem ser recusados).",
            400,
        )

    estado_antes = orcamento.to_dict()
    orcamento.status = "recusado"
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="atualizar",
        tabela="orcamentos",
        registro_id=orcamento.id,
        antes=estado_antes,
        depois=orcamento.to_dict(),
    )
    db.session.commit()

    return jsonify(orcamento.to_dict()), 200


# ---------------------------------------------------------------------------
# Contas a pagar (RF12)
# ---------------------------------------------------------------------------


@financeiro_bp.get("/contas-pagar")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONTA_PAGAR)
def listar_contas_pagar():
    query = ContaPagar.query

    status = (request.args.get("status") or "").strip()
    if status:
        if status not in ContaPagar.STATUS_VALIDOS:
            return _erro(
                f"Status invalido. Valores aceitos: {', '.join(ContaPagar.STATUS_VALIDOS)}.", 400
            )
        query = query.filter(ContaPagar.status == status)

    query = query.order_by(ContaPagar.vencimento.asc())
    return jsonify(_paginar(query, lambda c: c.to_dict())), 200


@financeiro_bp.post("/contas-pagar")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONTA_PAGAR)
def criar_conta_pagar():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []

    descricao = payload.get("descricao")
    if not descricao or not isinstance(descricao, str) or not descricao.strip():
        erros.append("Campo 'descricao' e obrigatorio e deve ser texto nao vazio.")

    valor, erro_valor = _validar_decimal(payload.get("valor"), "valor", permitir_zero=False)
    if erro_valor:
        erros.append(erro_valor)

    vencimento, erro_data = _parse_data(payload.get("vencimento"), "vencimento")
    if erro_data:
        erros.append(erro_data)

    status = payload.get("status", "pendente")
    if status not in ContaPagar.STATUS_VALIDOS:
        erros.append(f"Campo 'status' deve ser um de {ContaPagar.STATUS_VALIDOS}.")

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    conta = ContaPagar(descricao=descricao.strip(), valor=valor, vencimento=vencimento, status=status)
    db.session.add(conta)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="contas_pagar",
        registro_id=conta.id,
        antes=None,
        depois=conta.to_dict(),
    )
    db.session.commit()

    return jsonify(conta.to_dict()), 201


@financeiro_bp.put("/contas-pagar/<int:conta_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONTA_PAGAR)
def atualizar_conta_pagar(conta_id):
    conta = ContaPagar.query.get(conta_id)
    if conta is None:
        return _erro("Conta a pagar nao encontrada.", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []
    estado_antes = conta.to_dict()

    if "descricao" in payload:
        descricao = payload.get("descricao")
        if not descricao or not isinstance(descricao, str) or not descricao.strip():
            erros.append("Campo 'descricao' nao pode ser vazio.")
        else:
            conta.descricao = descricao.strip()

    if "valor" in payload:
        valor, erro_valor = _validar_decimal(payload.get("valor"), "valor", permitir_zero=False)
        if erro_valor:
            erros.append(erro_valor)
        else:
            conta.valor = valor

    if "vencimento" in payload:
        vencimento, erro_data = _parse_data(payload.get("vencimento"), "vencimento")
        if erro_data:
            erros.append(erro_data)
        else:
            conta.vencimento = vencimento

    if "status" in payload:
        status = payload.get("status")
        if status not in ContaPagar.STATUS_VALIDOS:
            erros.append(f"Campo 'status' deve ser um de {ContaPagar.STATUS_VALIDOS}.")
        else:
            conta.status = status

    if erros:
        db.session.rollback()
        return _erro("Dados invalidos.", 400, erros)

    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="atualizar",
        tabela="contas_pagar",
        registro_id=conta.id,
        antes=estado_antes,
        depois=conta.to_dict(),
    )
    db.session.commit()

    return jsonify(conta.to_dict()), 200


@financeiro_bp.delete("/contas-pagar/<int:conta_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CONTA_PAGAR)
def excluir_conta_pagar(conta_id):
    conta = ContaPagar.query.get(conta_id)
    if conta is None:
        return _erro("Conta a pagar nao encontrada.", 404)

    estado_antes = conta.to_dict()
    db.session.delete(conta)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="excluir",
        tabela="contas_pagar",
        registro_id=conta_id,
        antes=estado_antes,
        depois=None,
    )
    db.session.commit()

    return jsonify({"mensagem": "Conta a pagar excluida com sucesso."}), 200


# ---------------------------------------------------------------------------
# Contas a receber (somente leitura -- geradas via aprovacao de orcamento)
# ---------------------------------------------------------------------------


@financeiro_bp.get("/contas-receber")
@jwt_required()
def listar_contas_receber():
    query = ContaReceber.query

    paciente_id = request.args.get("paciente_id", type=int)
    if paciente_id is not None:
        query = query.filter(ContaReceber.paciente_id == paciente_id)

    orcamento_id = request.args.get("orcamento_id", type=int)
    if orcamento_id is not None:
        query = query.filter(ContaReceber.orcamento_id == orcamento_id)

    status = (request.args.get("status") or "").strip()
    if status:
        if status not in ContaReceber.STATUS_VALIDOS:
            return _erro(
                f"Status invalido. Valores aceitos: {', '.join(ContaReceber.STATUS_VALIDOS)}.", 400
            )
        query = query.filter(ContaReceber.status == status)

    query = query.order_by(ContaReceber.vencimento.asc())
    return jsonify(_paginar(query, lambda c: c.to_dict())), 200


# ---------------------------------------------------------------------------
# Pagamentos e comissoes (RF11, RF13)
# ---------------------------------------------------------------------------


@financeiro_bp.get("/pagamentos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PAGAMENTO)
def listar_pagamentos():
    query = Pagamento.query

    orcamento_id = request.args.get("orcamento_id", type=int)
    if orcamento_id is not None:
        query = query.filter(Pagamento.orcamento_id == orcamento_id)

    query = query.order_by(Pagamento.pago_em.desc())
    return jsonify(_paginar(query, lambda p: p.to_dict())), 200


@financeiro_bp.post("/pagamentos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PAGAMENTO)
def criar_pagamento():
    """
    Registra um pagamento, baixa a conta_receber correspondente e gera
    automaticamente a comissao_profissional (RF13), calculada com base
    num percentual configuravel (payload.percentual_comissao ou, na
    ausencia deste, o valor configurado em configuracoes_clinica /
    DEFAULT_PERCENTUAL_COMISSAO).
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    erros = []

    conta_receber_id, erro = _validar_inteiro_positivo(
        payload.get("conta_receber_id"), "conta_receber_id"
    )
    if erro:
        erros.append(erro)

    forma = payload.get("forma")
    if not isinstance(forma, str) or forma not in Pagamento.FORMAS_VALIDAS:
        erros.append(f"Campo 'forma' deve ser um de {Pagamento.FORMAS_VALIDAS}.")

    profissional_id, erro_prof = _validar_inteiro_positivo(
        payload.get("profissional_id"), "profissional_id"
    )
    if erro_prof:
        erros.append(erro_prof)
    elif not _profissional_existe(profissional_id):
        erros.append(f"Profissional com id {profissional_id} nao encontrado ou inativo.")

    percentual_comissao = None
    if payload.get("percentual_comissao") is not None:
        percentual_comissao, erro_percentual = _validar_decimal(
            payload.get("percentual_comissao"), "percentual_comissao", permitir_zero=False
        )
        if erro_percentual:
            erros.append(erro_percentual)
        elif percentual_comissao > 100:
            erros.append("Campo 'percentual_comissao' nao pode ser maior que 100.")

    if erros:
        return _erro("Dados invalidos.", 400, erros)

    conta = ContaReceber.query.get(conta_receber_id)
    if conta is None:
        return _erro(f"Conta a receber com id {conta_receber_id} nao encontrada.", 404)
    if conta.status not in ("pendente", "atrasado"):
        return _erro(
            f"Conta a receber ja se encontra com status '{conta.status}' e nao pode "
            "receber um novo pagamento.",
            400,
        )

    # O schema atual nao possui coluna de "valor pago parcial" em
    # contas_receber -- cada conta e baixada integralmente por um
    # pagamento. Se um valor for informado, ele deve corresponder
    # exatamente ao valor da conta, evitando baixas divergentes.
    valor_pagamento = conta.valor
    if payload.get("valor") is not None:
        valor_informado, erro_valor = _validar_decimal(
            payload.get("valor"), "valor", permitir_zero=False
        )
        if erro_valor:
            return _erro(erro_valor, 400)
        if valor_informado != conta.valor:
            return _erro(
                "O campo 'valor' informado (R$ "
                f"{valor_informado}) e diferente do valor da conta a receber "
                f"(R$ {conta.valor}). Pagamentos parciais nao sao suportados; "
                "informe o valor exato ou omita o campo para usar o valor da conta.",
                400,
            )
        valor_pagamento = valor_informado

    ator_id = _identidade_do_ator()

    pagamento = Pagamento(
        orcamento_id=conta.orcamento_id,
        valor=valor_pagamento,
        forma=forma,
        pago_em=datetime.utcnow(),
    )
    db.session.add(pagamento)
    db.session.flush()

    # pagamentos e uma tabela financeira sensivel -- auditoria obrigatoria.
    registrar_auditoria(
        usuario_id=ator_id,
        acao="criar",
        tabela="pagamentos",
        registro_id=pagamento.id,
        antes=None,
        depois=pagamento.to_dict(),
    )

    estado_antes_conta = conta.to_dict()
    conta.status = "pago"
    db.session.flush()
    registrar_auditoria(
        usuario_id=ator_id,
        acao="atualizar",
        tabela="contas_receber",
        registro_id=conta.id,
        antes=estado_antes_conta,
        depois=conta.to_dict(),
    )

    comissao = None
    aviso_comissao = None
    if conta.orcamento_id is None:
        # Sem orcamento vinculado nao ha como associar a comissao a um
        # orcamento (comissoes_profissionais.orcamento_id e NOT NULL no
        # schema); a baixa do pagamento segue normalmente.
        aviso_comissao = (
            "Esta conta a receber nao esta vinculada a um orcamento; nenhuma "
            "comissao foi gerada automaticamente."
        )
    else:
        percentual = percentual_comissao or _obter_percentual_comissao_padrao()
        valor_calculado = (valor_pagamento * percentual / Decimal("100")).quantize(
            TAMANHO_CENTAVOS, rounding=ROUND_HALF_UP
        )
        comissao_obj = ComissaoProfissional(
            profissional_id=profissional_id,
            orcamento_id=conta.orcamento_id,
            percentual=percentual,
            valor_calculado=valor_calculado,
        )
        db.session.add(comissao_obj)
        db.session.flush()
        registrar_auditoria(
            usuario_id=ator_id,
            acao="criar",
            tabela="comissoes_profissionais",
            registro_id=comissao_obj.id,
            antes=None,
            depois=comissao_obj.to_dict(),
        )
        comissao = comissao_obj.to_dict()

    db.session.commit()

    resposta = {
        "pagamento": pagamento.to_dict(),
        "conta_receber": conta.to_dict(),
        "comissao": comissao,
    }
    if aviso_comissao:
        resposta["aviso"] = aviso_comissao

    return jsonify(resposta), 201


@financeiro_bp.get("/comissoes")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PAGAMENTO)
def listar_comissoes():
    query = ComissaoProfissional.query

    profissional_id = request.args.get("profissional_id", type=int)
    if profissional_id is not None:
        query = query.filter(ComissaoProfissional.profissional_id == profissional_id)

    orcamento_id = request.args.get("orcamento_id", type=int)
    if orcamento_id is not None:
        query = query.filter(ComissaoProfissional.orcamento_id == orcamento_id)

    query = query.order_by(ComissaoProfissional.id.desc())
    return jsonify(_paginar(query, lambda c: c.to_dict())), 200


# ---------------------------------------------------------------------------
# Dashboard financeiro (RF12)
# ---------------------------------------------------------------------------


@financeiro_bp.get("/financeiro/resumo")
@jwt_required()
@require_perfil(PERFIS_DASHBOARD_FINANCEIRO)
def resumo_financeiro():
    """
    Totais para alimentar o dashboard financeiro:
        - total_a_receber: soma de contas_receber com status 'pendente' ou 'atrasado'
        - recebido_no_mes: soma de pagamentos.valor no mes corrente
        - inadimplencia: contas_receber vencidas e ainda nao pagas
          (status='atrasado', ou status='pendente' com vencimento < hoje)
        - total_a_pagar_pendente: soma de contas_pagar com status 'pendente' ou 'atrasado'
    """
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    if hoje.month == 12:
        inicio_proximo_mes = date(hoje.year + 1, 1, 1)
    else:
        inicio_proximo_mes = date(hoje.year, hoje.month + 1, 1)
    inicio_mes_dt = datetime.combine(inicio_mes, datetime.min.time())
    inicio_proximo_mes_dt = datetime.combine(inicio_proximo_mes, datetime.min.time())

    total_a_receber = (
        db.session.query(func.coalesce(func.sum(ContaReceber.valor), 0))
        .filter(ContaReceber.status.in_(["pendente", "atrasado"]))
        .scalar()
    )

    recebido_no_mes = (
        db.session.query(func.coalesce(func.sum(Pagamento.valor), 0))
        .filter(Pagamento.pago_em >= inicio_mes_dt, Pagamento.pago_em < inicio_proximo_mes_dt)
        .scalar()
    )

    query_inadimplencia = ContaReceber.query.filter(
        db.or_(
            ContaReceber.status == "atrasado",
            db.and_(ContaReceber.status == "pendente", ContaReceber.vencimento < hoje),
        )
    )
    inadimplencia_quantidade = query_inadimplencia.count()
    inadimplencia_valor = (
        db.session.query(func.coalesce(func.sum(ContaReceber.valor), 0))
        .filter(
            db.or_(
                ContaReceber.status == "atrasado",
                db.and_(ContaReceber.status == "pendente", ContaReceber.vencimento < hoje),
            )
        )
        .scalar()
    )

    total_a_pagar_pendente = (
        db.session.query(func.coalesce(func.sum(ContaPagar.valor), 0))
        .filter(ContaPagar.status.in_(["pendente", "atrasado"]))
        .scalar()
    )

    return (
        jsonify(
            {
                "gerado_em": datetime.utcnow().isoformat(),
                "periodo_mes_referencia": inicio_mes.isoformat(),
                "total_a_receber": float(total_a_receber or 0),
                "recebido_no_mes": float(recebido_no_mes or 0),
                "inadimplencia": {
                    "quantidade_contas": inadimplencia_quantidade,
                    "valor_total": float(inadimplencia_valor or 0),
                },
                "total_a_pagar_pendente": float(total_a_pagar_pendente or 0),
            }
        ),
        200,
    )
