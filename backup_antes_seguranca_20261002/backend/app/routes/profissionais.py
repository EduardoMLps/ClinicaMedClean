"""
Rotas de leitura de profissionais e especialidades.

Endpoint pequeno, adicionado durante a verificacao final do projeto: o
frontend (telas de Agenda e Prontuario) precisa popular selects de
"profissional responsavel", e nenhum dos modulos de backend expunha uma
rota para listar os profissionais cadastrados (o model ja existia em
app/models/pacientes.py, usado internamente por agenda/clinico/financeiro
para validacao de profissional_id, mas sem rota GET propria).

Blueprint: 'profissionais', prefixo /api/v1/profissionais
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.models.pacientes import Especialidade, Profissional

profissionais_bp = Blueprint("profissionais", __name__, url_prefix="/api/v1/profissionais")


@profissionais_bp.get("")
@jwt_required()
def listar_profissionais():
    """Lista profissionais ativos (ou todos, com ?incluir_inativos=1)."""
    incluir_inativos = request.args.get("incluir_inativos") in ("1", "true", "True")

    query = Profissional.query
    if not incluir_inativos:
        query = query.filter(Profissional.ativo.is_(True))

    profissionais = query.order_by(Profissional.nome.asc()).all()
    return jsonify([p.to_dict() for p in profissionais]), 200


@profissionais_bp.get("/especialidades")
@jwt_required()
def listar_especialidades():
    especialidades = Especialidade.query.order_by(Especialidade.nome.asc()).all()
    return jsonify([e.to_dict() for e in especialidades]), 200
