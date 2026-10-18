"""
Rotas de relatorios gerenciais (RF15, RF16): faturamento por periodo,
produtividade por profissional (atendimentos concluidos) e taxa de falta
(no-show) dos pacientes.

Blueprint: 'relatorios', prefixo /api/v1/relatorios

Todas as rotas sao somente leitura (GET) mas expoem dados financeiros e de
desempenho sensiveis, portanto exigem JWT valido + perfil autorizado
(administrador ou financeiro), assim como as demais rotas de escrita do
sistema exigem JWT + perfil.

Observacao sobre reaproveitamento de models: os models 'Agendamento' e
'Profissional' ja existem em app/models/pacientes.py (modulo de agenda) e
o model 'Pagamento' ja existe em app/models/financeiro.py (modulo de
orcamento/financeiro) -- todos sao reaproveitados aqui via import, para
nao redeclarar a mesma tabela em dois pontos do codigo (o que quebraria o
mapeamento do SQLAlchemy).
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models.financeiro import Pagamento
from app.models.pacientes import Agendamento, Profissional
from app.utils.auth_decorators import require_perfil

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/api/v1/relatorios")

# Relatorios gerenciais sao restritos a administrador e financeiro.
PERFIS_RELATORIOS = ["administrador", "financeiro"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _parse_data(valor, campo):
    """Converte string 'AAAA-MM-DD' em date. Levanta ValueError se invalido."""
    if not valor or not isinstance(valor, str):
        raise ValueError(f"O parametro '{campo}' e invalido. Use o formato AAAA-MM-DD.")
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"O parametro '{campo}' e invalido. Use o formato AAAA-MM-DD.")


def _periodo_da_requisicao():
    """
    Le e valida os parametros de query 'data_inicio' e 'data_fim'
    (formato AAAA-MM-DD). Quando nao informados, usa como padrao o
    periodo do primeiro dia do mes corrente ate hoje.

    Retorna (data_inicio: date, data_fim: date, erro: str|None).
    """
    hoje = date.today()
    data_inicio_bruta = request.args.get("data_inicio")
    data_fim_bruta = request.args.get("data_fim")

    try:
        data_inicio = (
            _parse_data(data_inicio_bruta, "data_inicio")
            if data_inicio_bruta
            else hoje.replace(day=1)
        )
        data_fim = _parse_data(data_fim_bruta, "data_fim") if data_fim_bruta else hoje
    except ValueError as exc:
        return None, None, str(exc)

    if data_fim < data_inicio:
        return None, None, "O parametro 'data_fim' nao pode ser anterior a 'data_inicio'."

    return data_inicio, data_fim, None


def _limites_datetime_do_periodo(data_inicio, data_fim):
    """Converte um intervalo de datas (inclusive) nos limites datetime
    correspondentes: 00:00:00 do primeiro dia ate 23:59:59.999999 do ultimo."""
    inicio_dt = datetime.combine(data_inicio, datetime.min.time())
    fim_dt = datetime.combine(data_fim, datetime.max.time())
    return inicio_dt, fim_dt


# ---------------------------------------------------------------------------
# RF15 (parte 1): faturamento por periodo
# ---------------------------------------------------------------------------


@relatorios_bp.get("/faturamento")
@jwt_required()
@require_perfil(PERFIS_RELATORIOS)
def relatorio_faturamento():
    """
    Faturamento (pagamentos recebidos) em um periodo.

    Parametros de query:
        data_inicio (AAAA-MM-DD, opcional -- padrao: 1o dia do mes corrente)
        data_fim    (AAAA-MM-DD, opcional -- padrao: hoje)
    """
    data_inicio, data_fim, erro = _periodo_da_requisicao()
    if erro:
        return _erro(erro, 400)

    inicio_dt, fim_dt = _limites_datetime_do_periodo(data_inicio, data_fim)

    filtro_periodo = (Pagamento.pago_em >= inicio_dt, Pagamento.pago_em <= fim_dt)

    total_geral, quantidade_pagamentos = (
        db.session.query(
            func.coalesce(func.sum(Pagamento.valor), 0),
            func.count(Pagamento.id),
        )
        .filter(*filtro_periodo)
        .one()
    )

    linhas_por_forma = (
        db.session.query(
            Pagamento.forma,
            func.coalesce(func.sum(Pagamento.valor), 0),
            func.count(Pagamento.id),
        )
        .filter(*filtro_periodo)
        .group_by(Pagamento.forma)
        .order_by(Pagamento.forma.asc())
        .all()
    )

    linhas_por_dia = (
        db.session.query(
            func.date(Pagamento.pago_em),
            func.coalesce(func.sum(Pagamento.valor), 0),
            func.count(Pagamento.id),
        )
        .filter(*filtro_periodo)
        .group_by(func.date(Pagamento.pago_em))
        .order_by(func.date(Pagamento.pago_em).asc())
        .all()
    )

    def _data_para_iso(valor):
        if isinstance(valor, (date, datetime)):
            return valor.isoformat()[:10]
        return str(valor)

    return jsonify({
        "periodo": {"data_inicio": data_inicio.isoformat(), "data_fim": data_fim.isoformat()},
        "total_faturado": float(total_geral or 0),
        "quantidade_pagamentos": int(quantidade_pagamentos or 0),
        "por_forma_pagamento": [
            {"forma": forma, "total": float(total or 0), "quantidade": int(qtd or 0)}
            for forma, total, qtd in linhas_por_forma
        ],
        "por_dia": [
            {"data": _data_para_iso(dia), "total": float(total or 0), "quantidade": int(qtd or 0)}
            for dia, total, qtd in linhas_por_dia
        ],
    }), 200


# ---------------------------------------------------------------------------
# RF15 (parte 2): produtividade por profissional
# ---------------------------------------------------------------------------


@relatorios_bp.get("/produtividade")
@jwt_required()
@require_perfil(PERFIS_RELATORIOS)
def relatorio_produtividade():
    """
    Quantidade de atendimentos concluidos por profissional em um periodo
    (RF15). Um "atendimento" e um agendamento com status = 'concluido'.

    Parametros de query:
        data_inicio     (AAAA-MM-DD, opcional -- padrao: 1o dia do mes corrente)
        data_fim        (AAAA-MM-DD, opcional -- padrao: hoje)
        profissional_id (int, opcional -- filtra um unico profissional)
    """
    data_inicio, data_fim, erro = _periodo_da_requisicao()
    if erro:
        return _erro(erro, 400)

    profissional_id = request.args.get("profissional_id", type=int)
    if request.args.get("profissional_id") is not None and profissional_id is None:
        return _erro("O parametro 'profissional_id' deve ser um numero inteiro.", 400)

    inicio_dt, fim_dt = _limites_datetime_do_periodo(data_inicio, data_fim)

    query = (
        db.session.query(
            Profissional.id,
            Profissional.nome,
            func.count(Agendamento.id),
        )
        .join(Agendamento, Agendamento.profissional_id == Profissional.id)
        .filter(
            Agendamento.status == "concluido",
            Agendamento.inicio >= inicio_dt,
            Agendamento.inicio <= fim_dt,
        )
    )

    if profissional_id is not None:
        query = query.filter(Profissional.id == profissional_id)

    linhas = (
        query.group_by(Profissional.id, Profissional.nome)
        .order_by(func.count(Agendamento.id).desc())
        .all()
    )

    return jsonify({
        "periodo": {"data_inicio": data_inicio.isoformat(), "data_fim": data_fim.isoformat()},
        "produtividade": [
            {
                "profissional_id": profissional_id_linha,
                "profissional_nome": nome,
                "total_atendimentos": int(total),
            }
            for profissional_id_linha, nome, total in linhas
        ],
    }), 200


# ---------------------------------------------------------------------------
# RF16: taxa de falta (no-show)
# ---------------------------------------------------------------------------


@relatorios_bp.get("/taxa-falta")
@jwt_required()
@require_perfil(PERFIS_RELATORIOS)
def relatorio_taxa_falta():
    """
    Taxa de falta (no-show) dos pacientes em um periodo (RF16): proporcao
    de agendamentos com status = 'faltou' em relacao ao total de
    agendamentos concluidos ou com falta (cancelamentos nao entram na
    base de calculo, pois nao representam ausencia do paciente em um
    horario efetivamente reservado para atendimento).

    Parametros de query:
        data_inicio     (AAAA-MM-DD, opcional -- padrao: 1o dia do mes corrente)
        data_fim        (AAAA-MM-DD, opcional -- padrao: hoje)
        profissional_id (int, opcional -- filtra um unico profissional)
    """
    data_inicio, data_fim, erro = _periodo_da_requisicao()
    if erro:
        return _erro(erro, 400)

    profissional_id = request.args.get("profissional_id", type=int)
    if request.args.get("profissional_id") is not None and profissional_id is None:
        return _erro("O parametro 'profissional_id' deve ser um numero inteiro.", 400)

    inicio_dt, fim_dt = _limites_datetime_do_periodo(data_inicio, data_fim)

    # Base de calculo: agendamentos que efetivamente chegaram ao horario
    # marcado (concluido) ou nao compareceram (faltou). Agendados,
    # confirmados, em atendimento ou cancelados nao entram no denominador.
    status_considerados = ("concluido", "faltou")

    query_base = Agendamento.query.filter(
        Agendamento.status.in_(status_considerados),
        Agendamento.inicio >= inicio_dt,
        Agendamento.inicio <= fim_dt,
    )
    if profissional_id is not None:
        query_base = query_base.filter(Agendamento.profissional_id == profissional_id)

    total_considerado = query_base.count()
    total_faltas = query_base.filter(Agendamento.status == "faltou").count()
    taxa_geral = (total_faltas / total_considerado) if total_considerado > 0 else 0.0

    linhas_por_profissional = (
        db.session.query(
            Profissional.id,
            Profissional.nome,
            func.count(Agendamento.id),
            func.sum(func.cast(Agendamento.status == "faltou", db.Integer)),
        )
        .join(Agendamento, Agendamento.profissional_id == Profissional.id)
        .filter(
            Agendamento.status.in_(status_considerados),
            Agendamento.inicio >= inicio_dt,
            Agendamento.inicio <= fim_dt,
        )
    )
    if profissional_id is not None:
        linhas_por_profissional = linhas_por_profissional.filter(Profissional.id == profissional_id)

    linhas_por_profissional = linhas_por_profissional.group_by(
        Profissional.id, Profissional.nome
    ).all()

    por_profissional = []
    for prof_id, nome, total, faltas in linhas_por_profissional:
        total = int(total or 0)
        faltas = int(faltas or 0)
        por_profissional.append({
            "profissional_id": prof_id,
            "profissional_nome": nome,
            "total_agendamentos": total,
            "total_faltas": faltas,
            "taxa_falta": round(faltas / total, 4) if total > 0 else 0.0,
        })
    por_profissional.sort(key=lambda item: item["taxa_falta"], reverse=True)

    return jsonify({
        "periodo": {"data_inicio": data_inicio.isoformat(), "data_fim": data_fim.isoformat()},
        "geral": {
            "total_agendamentos": total_considerado,
            "total_faltas": total_faltas,
            "taxa_falta": round(taxa_geral, 4),
        },
        "por_profissional": por_profissional,
    }), 200
