"""
Rotas de agenda (RF02, RF19): CRUD de agendamentos com checagem de conflito
de horario (mesmo profissional e/ou mesma cadeira), visao diaria e mudanca
rapida de status. Inclui tambem endpoints auxiliares de bloqueios de agenda
e disparo do lembrete (stub) de consulta.

Blueprint: 'agenda', prefixo /api/v1/agenda
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.pacientes import (
    Agendamento,
    BloqueioAgenda,
    CadeiraConsultorio,
    Paciente,
    Profissional,
)
from app.utils.auth_decorators import require_perfil
from app.utils.notificacoes import enviar_lembrete
from app.utils.security import registrar_auditoria

agenda_bp = Blueprint("agenda", __name__, url_prefix="/api/v1/agenda")

# Perfis autorizados a criar/alterar/excluir agendamentos.
PERFIS_ESCRITA_AGENDA = ["administrador", "recepcao"]
# Alem de recepcao/administrador, o proprio dentista pode mudar o status
# do seu atendimento (ex.: marcar 'em_atendimento' ou 'concluido').
PERFIS_STATUS_AGENDA = ["administrador", "recepcao", "dentista"]


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _usuario_atual_id():
    try:
        identidade = get_jwt_identity()
        return int(identidade) if identidade is not None else None
    except (TypeError, ValueError, RuntimeError):
        return None


def _parse_datetime(valor, campo):
    """Converte string ISO 8601 em datetime "naive" (sem timezone)."""
    if not valor or not isinstance(valor, str):
        raise ValueError(
            f"O campo '{campo}' e obrigatorio (formato ISO 8601, ex.: 2026-08-20T14:30:00)."
        )
    valor_normalizado = valor.strip()
    if valor_normalizado.endswith("Z"):
        valor_normalizado = valor_normalizado[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(valor_normalizado)
    except ValueError:
        raise ValueError(f"O campo '{campo}' possui um formato de data/hora invalido.")
    return dt.replace(tzinfo=None)


def _parse_inteiro(valor, campo, obrigatorio=True):
    if valor is None:
        if obrigatorio:
            raise ValueError(f"O campo '{campo}' e obrigatorio.")
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"O campo '{campo}' deve ser um numero inteiro.")


def _verificar_conflito(profissional_id, cadeira_id, inicio, fim, ignorar_agendamento_id=None):
    """
    Verifica sobreposicao de horario para o mesmo profissional e, se
    informada, para a mesma cadeira/consultorio -- alem de bloqueios de
    agenda (ferias/folgas) do profissional no periodo.

    So considera conflito com agendamentos em status "ativo"
    (agendado/confirmado/em_atendimento); agendamentos cancelados ou com
    falta do paciente nao bloqueiam o horario.

    Retorna uma mensagem de erro (str) se houver conflito, ou None.
    """
    status_ocupam_agenda = Agendamento.STATUS_ATIVOS

    conflito_profissional = Agendamento.query.filter(
        Agendamento.profissional_id == profissional_id,
        Agendamento.status.in_(status_ocupam_agenda),
        Agendamento.inicio < fim,
        Agendamento.fim > inicio,
    )
    if ignorar_agendamento_id is not None:
        conflito_profissional = conflito_profissional.filter(Agendamento.id != ignorar_agendamento_id)
    if conflito_profissional.first() is not None:
        return "O profissional ja possui outro agendamento sobreposto a este horario."

    if cadeira_id is not None:
        conflito_cadeira = Agendamento.query.filter(
            Agendamento.cadeira_id == cadeira_id,
            Agendamento.status.in_(status_ocupam_agenda),
            Agendamento.inicio < fim,
            Agendamento.fim > inicio,
        )
        if ignorar_agendamento_id is not None:
            conflito_cadeira = conflito_cadeira.filter(Agendamento.id != ignorar_agendamento_id)
        if conflito_cadeira.first() is not None:
            return "A cadeira/consultorio informada ja esta ocupada neste horario."

    bloqueio = BloqueioAgenda.query.filter(
        BloqueioAgenda.profissional_id == profissional_id,
        BloqueioAgenda.inicio < fim,
        BloqueioAgenda.fim > inicio,
    ).first()
    if bloqueio is not None:
        motivo = bloqueio.motivo or "sem motivo informado"
        return f"O profissional possui um bloqueio de agenda neste horario ({motivo})."

    return None


@agenda_bp.get("")
@jwt_required()
def listar_agenda():
    """
    Visao de agenda (RF02).

    Uso tipico -- visao de um dia para um profissional:
        GET /api/v1/agenda?profissional_id=1&data=2026-08-20

    Parametros de query suportados:
        profissional_id (int, opcional)
        data             (AAAA-MM-DD, opcional)
        status           (opcional, um dos valores de Agendamento.STATUS_VALIDOS)

    Se nenhum filtro de data for informado, mas profissional_id for, lista
    todos os agendamentos do profissional (mais recentes primeiro nao se
    aplica: ordenado por inicio). Se nenhum filtro for informado, retorna
    apenas agendamentos futuros (para nao devolver o historico inteiro).
    """
    profissional_id = request.args.get("profissional_id", type=int)
    data_str = request.args.get("data")
    status_filtro = request.args.get("status")

    query = Agendamento.query

    if profissional_id is not None:
        query = query.filter(Agendamento.profissional_id == profissional_id)

    if data_str:
        try:
            data_filtro = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            return _erro("Parametro 'data' invalido. Use o formato AAAA-MM-DD.", 400)
        inicio_dia = datetime.combine(data_filtro, datetime.min.time())
        fim_dia = datetime.combine(data_filtro, datetime.max.time())
        query = query.filter(Agendamento.inicio >= inicio_dia, Agendamento.inicio <= fim_dia)
    elif profissional_id is None:
        query = query.filter(Agendamento.inicio >= datetime.utcnow())

    if status_filtro:
        if status_filtro not in Agendamento.STATUS_VALIDOS:
            return _erro(
                f"status invalido. Valores aceitos: {', '.join(Agendamento.STATUS_VALIDOS)}.", 400
            )
        query = query.filter(Agendamento.status == status_filtro)

    agendamentos = query.order_by(Agendamento.inicio.asc()).limit(200).all()
    return jsonify([a.to_dict() for a in agendamentos]), 200


@agenda_bp.get("/<int:agendamento_id>")
@jwt_required()
def obter_agendamento(agendamento_id):
    agendamento = Agendamento.query.get(agendamento_id)
    if agendamento is None:
        return _erro("Agendamento nao encontrado.", 404)
    return jsonify(agendamento.to_dict()), 200


@agenda_bp.post("")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def criar_agendamento():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    try:
        paciente_id = _parse_inteiro(dados.get("paciente_id"), "paciente_id")
        profissional_id = _parse_inteiro(dados.get("profissional_id"), "profissional_id")
        cadeira_id = _parse_inteiro(dados.get("cadeira_id"), "cadeira_id", obrigatorio=False)
        inicio = _parse_datetime(dados.get("inicio"), "inicio")
        fim = _parse_datetime(dados.get("fim"), "fim")
    except ValueError as exc:
        return _erro(str(exc), 400)

    if fim <= inicio:
        return _erro("O campo 'fim' deve ser posterior ao campo 'inicio'.", 400)

    status = dados.get("status", "agendado")
    if status not in Agendamento.STATUS_VALIDOS:
        return _erro(f"status invalido. Valores aceitos: {', '.join(Agendamento.STATUS_VALIDOS)}.", 400)

    if Paciente.query.get(paciente_id) is None:
        return _erro("paciente_id informado nao corresponde a um paciente existente.", 400)

    profissional = Profissional.query.get(profissional_id)
    if profissional is None:
        return _erro("profissional_id informado nao corresponde a um profissional existente.", 400)
    if not profissional.ativo:
        return _erro("Nao e possivel agendar com um profissional inativo.", 400)

    if cadeira_id is not None and CadeiraConsultorio.query.get(cadeira_id) is None:
        return _erro("cadeira_id informado nao corresponde a uma cadeira existente.", 400)

    conflito = _verificar_conflito(profissional_id, cadeira_id, inicio, fim)
    if conflito:
        return _erro(conflito, 409)

    agendamento = Agendamento(
        paciente_id=paciente_id,
        profissional_id=profissional_id,
        cadeira_id=cadeira_id,
        inicio=inicio,
        fim=fim,
        status=status,
    )

    try:
        db.session.add(agendamento)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="criar",
            tabela="agendamentos",
            registro_id=agendamento.id,
            antes=None,
            depois=agendamento.to_dict(),
        )
    except IntegrityError:
        db.session.rollback()
        return _erro("Nao foi possivel criar o agendamento devido a dados invalidos.", 400)

    return jsonify(agendamento.to_dict()), 201


@agenda_bp.put("/<int:agendamento_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def atualizar_agendamento(agendamento_id):
    agendamento = Agendamento.query.get(agendamento_id)
    if agendamento is None:
        return _erro("Agendamento nao encontrado.", 404)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    estado_antes = agendamento.to_dict()

    novo_paciente_id = agendamento.paciente_id
    novo_profissional_id = agendamento.profissional_id
    nova_cadeira_id = agendamento.cadeira_id
    novo_inicio = agendamento.inicio
    novo_fim = agendamento.fim

    try:
        if "paciente_id" in dados:
            novo_paciente_id = _parse_inteiro(dados.get("paciente_id"), "paciente_id")
        if "profissional_id" in dados:
            novo_profissional_id = _parse_inteiro(dados.get("profissional_id"), "profissional_id")
        if "cadeira_id" in dados:
            nova_cadeira_id = _parse_inteiro(dados.get("cadeira_id"), "cadeira_id", obrigatorio=False)
        if "inicio" in dados:
            novo_inicio = _parse_datetime(dados.get("inicio"), "inicio")
        if "fim" in dados:
            novo_fim = _parse_datetime(dados.get("fim"), "fim")
    except ValueError as exc:
        return _erro(str(exc), 400)

    if novo_fim <= novo_inicio:
        return _erro("O campo 'fim' deve ser posterior ao campo 'inicio'.", 400)

    if "paciente_id" in dados and Paciente.query.get(novo_paciente_id) is None:
        return _erro("paciente_id informado nao corresponde a um paciente existente.", 400)

    if "profissional_id" in dados:
        profissional = Profissional.query.get(novo_profissional_id)
        if profissional is None:
            return _erro("profissional_id informado nao corresponde a um profissional existente.", 400)
        if not profissional.ativo:
            return _erro("Nao e possivel agendar com um profissional inativo.", 400)

    if "cadeira_id" in dados and nova_cadeira_id is not None:
        if CadeiraConsultorio.query.get(nova_cadeira_id) is None:
            return _erro("cadeira_id informado nao corresponde a uma cadeira existente.", 400)

    novo_status = agendamento.status
    if "status" in dados:
        novo_status = dados["status"]
        if novo_status not in Agendamento.STATUS_VALIDOS:
            return _erro(
                f"status invalido. Valores aceitos: {', '.join(Agendamento.STATUS_VALIDOS)}.", 400
            )

    horario_ou_recursos_mudaram = (
        novo_profissional_id != agendamento.profissional_id
        or nova_cadeira_id != agendamento.cadeira_id
        or novo_inicio != agendamento.inicio
        or novo_fim != agendamento.fim
    )
    if horario_ou_recursos_mudaram:
        conflito = _verificar_conflito(
            novo_profissional_id,
            nova_cadeira_id,
            novo_inicio,
            novo_fim,
            ignorar_agendamento_id=agendamento.id,
        )
        if conflito:
            return _erro(conflito, 409)

    agendamento.paciente_id = novo_paciente_id
    agendamento.profissional_id = novo_profissional_id
    agendamento.cadeira_id = nova_cadeira_id
    agendamento.inicio = novo_inicio
    agendamento.fim = novo_fim
    agendamento.status = novo_status

    try:
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="atualizar",
            tabela="agendamentos",
            registro_id=agendamento.id,
            antes=estado_antes,
            depois=agendamento.to_dict(),
        )
    except IntegrityError:
        db.session.rollback()
        return _erro("Nao foi possivel atualizar o agendamento devido a dados invalidos.", 400)

    return jsonify(agendamento.to_dict()), 200


@agenda_bp.put("/<int:agendamento_id>/status")
@jwt_required()
@require_perfil(PERFIS_STATUS_AGENDA)
def atualizar_status_agendamento(agendamento_id):
    """
    Endpoint dedicado para mudanca rapida de status do agendamento
    (ex.: recepcao confirma presenca, dentista marca 'em_atendimento' ou
    'concluido', paciente falta -> 'faltou').
    """
    agendamento = Agendamento.query.get(agendamento_id)
    if agendamento is None:
        return _erro("Agendamento nao encontrado.", 404)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or "status" not in dados:
        return _erro("O campo 'status' e obrigatorio.", 400)

    novo_status = dados["status"]
    if novo_status not in Agendamento.STATUS_VALIDOS:
        return _erro(f"status invalido. Valores aceitos: {', '.join(Agendamento.STATUS_VALIDOS)}.", 400)

    estado_antes = agendamento.to_dict()
    agendamento.status = novo_status

    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="atualizar_status",
        tabela="agendamentos",
        registro_id=agendamento.id,
        antes=estado_antes,
        depois=agendamento.to_dict(),
    )

    return jsonify(agendamento.to_dict()), 200


@agenda_bp.delete("/<int:agendamento_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def excluir_agendamento(agendamento_id):
    agendamento = Agendamento.query.get(agendamento_id)
    if agendamento is None:
        return _erro("Agendamento nao encontrado.", 404)

    estado_antes = agendamento.to_dict()
    db.session.delete(agendamento)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="excluir",
        tabela="agendamentos",
        registro_id=agendamento_id,
        antes=estado_antes,
        depois=None,
    )

    return jsonify({"mensagem": "Agendamento excluido com sucesso."}), 200


@agenda_bp.post("/<int:agendamento_id>/lembrete")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def enviar_lembrete_agendamento(agendamento_id):
    """
    Dispara o envio (stub -- ver app/utils/notificacoes.py) de um lembrete
    de consulta para o paciente do agendamento informado.
    """
    agendamento = Agendamento.query.get(agendamento_id)
    if agendamento is None:
        return _erro("Agendamento nao encontrado.", 404)

    canal = request.args.get("canal", "whatsapp")

    try:
        notificacao = enviar_lembrete(agendamento, canal=canal)
    except ValueError as exc:
        return _erro(str(exc), 400)

    return jsonify({
        "mensagem": "Lembrete enviado (simulado) com sucesso.",
        "notificacao": notificacao.to_dict(),
    }), 201


# ---------------------------------------------------------------------
# Endpoints auxiliares de apoio a tela de agenda: cadeiras/consultorios
# (somente leitura) e bloqueios de agenda (CRUD basico).
# ---------------------------------------------------------------------

@agenda_bp.get("/cadeiras")
@jwt_required()
def listar_cadeiras():
    cadeiras = CadeiraConsultorio.query.order_by(CadeiraConsultorio.nome.asc()).all()
    return jsonify([c.to_dict() for c in cadeiras]), 200


@agenda_bp.get("/bloqueios")
@jwt_required()
def listar_bloqueios():
    profissional_id = request.args.get("profissional_id", type=int)
    query = BloqueioAgenda.query
    if profissional_id is not None:
        query = query.filter(BloqueioAgenda.profissional_id == profissional_id)
    bloqueios = query.order_by(BloqueioAgenda.inicio.asc()).all()
    return jsonify([b.to_dict() for b in bloqueios]), 200


@agenda_bp.post("/bloqueios")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def criar_bloqueio():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    try:
        profissional_id = _parse_inteiro(dados.get("profissional_id"), "profissional_id")
        inicio = _parse_datetime(dados.get("inicio"), "inicio")
        fim = _parse_datetime(dados.get("fim"), "fim")
    except ValueError as exc:
        return _erro(str(exc), 400)

    if fim <= inicio:
        return _erro("O campo 'fim' deve ser posterior ao campo 'inicio'.", 400)

    if Profissional.query.get(profissional_id) is None:
        return _erro("profissional_id informado nao corresponde a um profissional existente.", 400)

    motivo = dados.get("motivo")
    if motivo is not None and not isinstance(motivo, str):
        return _erro("O campo 'motivo', quando informado, deve ser um texto.", 400)

    bloqueio = BloqueioAgenda(
        profissional_id=profissional_id,
        inicio=inicio,
        fim=fim,
        motivo=motivo.strip() if motivo else None,
    )
    db.session.add(bloqueio)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="criar",
        tabela="bloqueios_agenda",
        registro_id=bloqueio.id,
        antes=None,
        depois=bloqueio.to_dict(),
    )

    return jsonify(bloqueio.to_dict()), 201


@agenda_bp.delete("/bloqueios/<int:bloqueio_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_AGENDA)
def excluir_bloqueio(bloqueio_id):
    bloqueio = BloqueioAgenda.query.get(bloqueio_id)
    if bloqueio is None:
        return _erro("Bloqueio nao encontrado.", 404)

    estado_antes = bloqueio.to_dict()
    db.session.delete(bloqueio)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="excluir",
        tabela="bloqueios_agenda",
        registro_id=bloqueio_id,
        antes=estado_antes,
        depois=None,
    )

    return jsonify({"mensagem": "Bloqueio excluido com sucesso."}), 200
