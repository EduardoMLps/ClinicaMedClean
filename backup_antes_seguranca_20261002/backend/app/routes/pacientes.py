"""
Rotas de pacientes (RF01, RF19): CRUD completo de pacientes, com suporte a
responsavel_id para menores de idade e captura de consentimento_lgpd_id
no cadastro.

Blueprint: 'pacientes', prefixo /api/v1/pacientes
"""

import re
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.pacientes import Endereco, Paciente
from app.utils.auth_decorators import require_perfil
from app.utils.security import registrar_auditoria

pacientes_bp = Blueprint("pacientes", __name__, url_prefix="/api/v1/pacientes")

# Perfis autorizados a criar/alterar pacientes. Exclusao e restrita a
# administrador por ser uma operacao mais sensivel (dados pessoais/LGPD).
PERFIS_ESCRITA_PACIENTE = ["administrador", "recepcao"]
PERFIS_EXCLUSAO_PACIENTE = ["administrador"]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CEP_REGEX = re.compile(r"^\d{5}-?\d{3}$")
UF_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}


def _erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def _usuario_atual_id():
    """Extrai o id do usuario autenticado a partir do JWT, com fallback seguro."""
    try:
        identidade = get_jwt_identity()
        return int(identidade) if identidade is not None else None
    except (TypeError, ValueError, RuntimeError):
        return None


def _mensagem_integridade(exc, mensagem_padrao):
    """
    Traduz erros de integridade do banco (FK/UNIQUE) em mensagens claras.

    A checagem por texto e tolerante a diferencas de redacao entre
    dialetos (ex.: MySQL inclui o nome da constraint, ex.
    'uq_pacientes_cpf', enquanto outros bancos podem so citar a coluna),
    para que a mensagem amigavel seja exibida em qualquer ambiente.
    """
    texto = str(getattr(exc, "orig", exc)).lower()
    if "uq_pacientes_cpf" in texto or ("cpf" in texto and ("duplicate" in texto or "unique" in texto)):
        return "Ja existe um paciente cadastrado com este CPF."
    if "fk_pacientes_responsavel" in texto or "responsavel_id" in texto:
        return "responsavel_id informado nao corresponde a um paciente existente."
    if "fk_pacientes_consentimento" in texto or "consentimento_lgpd_id" in texto:
        return "consentimento_lgpd_id informado nao corresponde a um consentimento existente."
    return mensagem_padrao


def _calcular_idade(data_nasc):
    hoje = date.today()
    return hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))


def _parse_data_nascimento(valor):
    if not valor or not isinstance(valor, str):
        raise ValueError("O campo 'data_nascimento' e obrigatorio (formato AAAA-MM-DD).")
    try:
        data_nasc = datetime.strptime(valor.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("O campo 'data_nascimento' e invalido. Use o formato AAAA-MM-DD.")
    if data_nasc > date.today():
        raise ValueError("O campo 'data_nascimento' nao pode ser uma data futura.")
    return data_nasc


def _validar_payload_paciente(dados, parcial=False):
    """
    Valida e normaliza o payload de entrada para criacao (parcial=False) ou
    atualizacao (parcial=True) de um paciente.

    Retorna (dict_normalizado, None) em caso de sucesso, ou (None, mensagem_erro).
    """
    if not isinstance(dados, dict):
        return None, "Corpo da requisicao deve ser um JSON valido."

    normalizado = {}

    # nome (obrigatorio na criacao)
    if not parcial or "nome" in dados:
        nome = dados.get("nome")
        if not nome or not isinstance(nome, str) or not nome.strip():
            return None, "O campo 'nome' e obrigatorio e deve ser um texto nao vazio."
        normalizado["nome"] = nome.strip()

    # data_nascimento (obrigatorio na criacao) -- usada para validar idade/RF01
    data_nasc = None
    if not parcial or "data_nascimento" in dados:
        try:
            data_nasc = _parse_data_nascimento(dados.get("data_nascimento"))
        except ValueError as exc:
            return None, str(exc)
        normalizado["data_nascimento"] = data_nasc

    # cpf (opcional)
    if "cpf" in dados:
        cpf_bruto = dados.get("cpf")
        if cpf_bruto:
            cpf_digitos = re.sub(r"\D", "", str(cpf_bruto))
            if len(cpf_digitos) != 11:
                return None, "O campo 'cpf' e invalido: deve conter 11 digitos."
            normalizado["cpf"] = cpf_digitos
        else:
            normalizado["cpf"] = None

    # telefone (opcional)
    if "telefone" in dados:
        telefone = dados.get("telefone")
        normalizado["telefone"] = telefone.strip() if isinstance(telefone, str) and telefone.strip() else None

    # email (opcional)
    if "email" in dados:
        email = dados.get("email")
        if email:
            email = str(email).strip()
            if not EMAIL_REGEX.match(email):
                return None, "O campo 'email' e invalido."
            normalizado["email"] = email
        else:
            normalizado["email"] = None

    # responsavel_id (opcional, obrigatorio se paciente for menor de idade)
    if "responsavel_id" in dados:
        responsavel_bruto = dados.get("responsavel_id")
        if responsavel_bruto is None:
            normalizado["responsavel_id"] = None
        else:
            try:
                normalizado["responsavel_id"] = int(responsavel_bruto)
            except (TypeError, ValueError):
                return None, "O campo 'responsavel_id' deve ser um numero inteiro."

    # consentimento_lgpd_id (opcional -- captura do consentimento LGPD no cadastro)
    if "consentimento_lgpd_id" in dados:
        consentimento_bruto = dados.get("consentimento_lgpd_id")
        if consentimento_bruto is None:
            normalizado["consentimento_lgpd_id"] = None
        else:
            try:
                normalizado["consentimento_lgpd_id"] = int(consentimento_bruto)
            except (TypeError, ValueError):
                return None, "O campo 'consentimento_lgpd_id' deve ser um numero inteiro."

    # Regra de negocio (RF01): paciente menor de idade precisa de responsavel.
    if data_nasc is not None:
        idade = _calcular_idade(data_nasc)
        responsavel_informado = normalizado.get("responsavel_id")
        if idade < Paciente.IDADE_MAIORIDADE and not responsavel_informado:
            return None, (
                "Paciente menor de idade (idade calculada a partir de "
                "data_nascimento) requer o campo 'responsavel_id' com o id "
                "de um paciente responsavel ja cadastrado."
            )

    return normalizado, None


@pacientes_bp.get("")
@jwt_required()
def listar_pacientes():
    """Lista pacientes com busca opcional por nome (?q=) e paginacao."""
    termo_busca = (request.args.get("q") or "").strip()
    pagina = request.args.get("pagina", 1, type=int) or 1
    por_pagina = request.args.get("por_pagina", 20, type=int) or 20
    por_pagina = min(max(por_pagina, 1), 100)

    query = Paciente.query
    if termo_busca:
        query = query.filter(Paciente.nome.ilike(f"%{termo_busca}%"))

    query = query.order_by(Paciente.nome.asc())
    paginacao = query.paginate(page=pagina, per_page=por_pagina, error_out=False)

    return jsonify({
        "dados": [p.to_dict() for p in paginacao.items],
        "pagina": paginacao.page,
        "por_pagina": paginacao.per_page,
        "total": paginacao.total,
        "total_paginas": paginacao.pages,
    }), 200


@pacientes_bp.get("/<int:paciente_id>")
@jwt_required()
def obter_paciente(paciente_id):
    paciente = Paciente.query.get(paciente_id)
    if paciente is None:
        return _erro("Paciente nao encontrado.", 404)
    return jsonify(paciente.to_dict(incluir_enderecos=True)), 200


@pacientes_bp.post("")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PACIENTE)
def criar_paciente():
    dados_entrada = request.get_json(silent=True)
    normalizado, erro = _validar_payload_paciente(dados_entrada, parcial=False)
    if erro:
        return _erro(erro, 400)

    if normalizado.get("responsavel_id") is not None:
        responsavel = Paciente.query.get(normalizado["responsavel_id"])
        if responsavel is None:
            return _erro("responsavel_id informado nao corresponde a um paciente existente.", 400)

    paciente = Paciente(
        nome=normalizado["nome"],
        cpf=normalizado.get("cpf"),
        data_nascimento=normalizado["data_nascimento"],
        responsavel_id=normalizado.get("responsavel_id"),
        telefone=normalizado.get("telefone"),
        email=normalizado.get("email"),
        consentimento_lgpd_id=normalizado.get("consentimento_lgpd_id"),
    )

    try:
        db.session.add(paciente)
        db.session.flush()  # forca o INSERT agora, para capturar erros de FK/UNIQUE cedo

        # pacientes contem dados pessoais sensiveis (LGPD) -- toda escrita e auditada.
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="criar",
            tabela="pacientes",
            registro_id=paciente.id,
            antes=None,
            depois=paciente.to_dict(),
        )
    except IntegrityError as exc:
        db.session.rollback()
        return _erro(_mensagem_integridade(exc, "Nao foi possivel cadastrar o paciente."), 400)

    return jsonify(paciente.to_dict()), 201


@pacientes_bp.put("/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PACIENTE)
def atualizar_paciente(paciente_id):
    paciente = Paciente.query.get(paciente_id)
    if paciente is None:
        return _erro("Paciente nao encontrado.", 404)

    dados_entrada = request.get_json(silent=True)
    normalizado, erro = _validar_payload_paciente(dados_entrada, parcial=True)
    if erro:
        return _erro(erro, 400)
    if not normalizado:
        return _erro("Nenhum campo valido informado para atualizacao.", 400)

    if "responsavel_id" in normalizado and normalizado["responsavel_id"] is not None:
        if normalizado["responsavel_id"] == paciente_id:
            return _erro("Um paciente nao pode ser responsavel por si mesmo.", 400)
        if Paciente.query.get(normalizado["responsavel_id"]) is None:
            return _erro("responsavel_id informado nao corresponde a um paciente existente.", 400)

    estado_antes = paciente.to_dict()
    for campo, valor in normalizado.items():
        setattr(paciente, campo, valor)

    try:
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="atualizar",
            tabela="pacientes",
            registro_id=paciente.id,
            antes=estado_antes,
            depois=paciente.to_dict(),
        )
    except IntegrityError as exc:
        db.session.rollback()
        return _erro(_mensagem_integridade(exc, "Nao foi possivel atualizar o paciente."), 400)

    return jsonify(paciente.to_dict()), 200


@pacientes_bp.delete("/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_EXCLUSAO_PACIENTE)
def excluir_paciente(paciente_id):
    paciente = Paciente.query.get(paciente_id)
    if paciente is None:
        return _erro("Paciente nao encontrado.", 404)

    estado_antes = paciente.to_dict()
    try:
        db.session.delete(paciente)
        db.session.flush()
        registrar_auditoria(
            usuario_id=_usuario_atual_id(),
            acao="excluir",
            tabela="pacientes",
            registro_id=paciente_id,
            antes=estado_antes,
            depois=None,
        )
    except IntegrityError:
        db.session.rollback()
        return _erro(
            "Nao e possivel excluir este paciente pois existem registros "
            "vinculados (agendamentos, prontuarios, orcamentos, contas a "
            "receber, etc.). Considere manter o cadastro e apenas inativa-lo.",
            409,
        )

    return jsonify({"mensagem": "Paciente excluido com sucesso."}), 200


# ---------------------------------------------------------------------
# Sub-recurso: enderecos do paciente
# ---------------------------------------------------------------------

@pacientes_bp.get("/<int:paciente_id>/enderecos")
@jwt_required()
def listar_enderecos(paciente_id):
    paciente = Paciente.query.get(paciente_id)
    if paciente is None:
        return _erro("Paciente nao encontrado.", 404)
    return jsonify([e.to_dict() for e in paciente.enderecos]), 200


@pacientes_bp.post("/<int:paciente_id>/enderecos")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PACIENTE)
def criar_endereco(paciente_id):
    paciente = Paciente.query.get(paciente_id)
    if paciente is None:
        return _erro("Paciente nao encontrado.", 404)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    logradouro = (dados.get("logradouro") or "").strip()
    cidade = (dados.get("cidade") or "").strip()
    uf = (dados.get("uf") or "").strip().upper()
    cep = (dados.get("cep") or "").strip()

    if not logradouro:
        return _erro("O campo 'logradouro' e obrigatorio.", 400)
    if not cidade:
        return _erro("O campo 'cidade' e obrigatorio.", 400)
    if uf not in UF_VALIDAS:
        return _erro("O campo 'uf' deve ser a sigla de um estado brasileiro valido.", 400)
    if not CEP_REGEX.match(cep):
        return _erro("O campo 'cep' e invalido. Use o formato 00000-000.", 400)

    endereco = Endereco(paciente_id=paciente.id, logradouro=logradouro, cidade=cidade, uf=uf, cep=cep)
    db.session.add(endereco)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="criar",
        tabela="enderecos",
        registro_id=endereco.id,
        antes=None,
        depois=endereco.to_dict(),
    )

    return jsonify(endereco.to_dict()), 201


@pacientes_bp.put("/<int:paciente_id>/enderecos/<int:endereco_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PACIENTE)
def atualizar_endereco(paciente_id, endereco_id):
    endereco = Endereco.query.filter_by(id=endereco_id, paciente_id=paciente_id).first()
    if endereco is None:
        return _erro("Endereco nao encontrado para este paciente.", 404)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Corpo da requisicao deve ser um JSON valido.", 400)

    estado_antes = endereco.to_dict()

    if "logradouro" in dados:
        valor = (dados.get("logradouro") or "").strip()
        if not valor:
            return _erro("O campo 'logradouro' nao pode ser vazio.", 400)
        endereco.logradouro = valor

    if "cidade" in dados:
        valor = (dados.get("cidade") or "").strip()
        if not valor:
            return _erro("O campo 'cidade' nao pode ser vazio.", 400)
        endereco.cidade = valor

    if "uf" in dados:
        valor = (dados.get("uf") or "").strip().upper()
        if valor not in UF_VALIDAS:
            return _erro("O campo 'uf' deve ser a sigla de um estado brasileiro valido.", 400)
        endereco.uf = valor

    if "cep" in dados:
        valor = (dados.get("cep") or "").strip()
        if not CEP_REGEX.match(valor):
            return _erro("O campo 'cep' e invalido. Use o formato 00000-000.", 400)
        endereco.cep = valor

    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="atualizar",
        tabela="enderecos",
        registro_id=endereco.id,
        antes=estado_antes,
        depois=endereco.to_dict(),
    )

    return jsonify(endereco.to_dict()), 200


@pacientes_bp.delete("/<int:paciente_id>/enderecos/<int:endereco_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_PACIENTE)
def excluir_endereco(paciente_id, endereco_id):
    endereco = Endereco.query.filter_by(id=endereco_id, paciente_id=paciente_id).first()
    if endereco is None:
        return _erro("Endereco nao encontrado para este paciente.", 404)

    estado_antes = endereco.to_dict()
    db.session.delete(endereco)
    db.session.flush()
    registrar_auditoria(
        usuario_id=_usuario_atual_id(),
        acao="excluir",
        tabela="enderecos",
        registro_id=endereco_id,
        antes=estado_antes,
        depois=None,
    )

    return jsonify({"mensagem": "Endereco excluido com sucesso."}), 200
