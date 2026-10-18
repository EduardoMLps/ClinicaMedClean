"""
Pacote de models SQLAlchemy do backend.

Os models sao importados aqui para garantir que fiquem registrados no
metadata do SQLAlchemy (db.metadata) assim que o pacote app.models for
importado -- essencial para autogeracao de migracoes (Flask-Migrate/Alembic)
e para evitar erros de "table not found" causados por import ausente.
"""

from app.models.auth import LogAuditoria, Perfil, Permissao, Usuario
from app.models.clinico import (
    Atestado,
    EvolucaoClinica,
    ExameAnexo,
    Odontograma,
    OdontogramaHistorico,
    Prontuario,
    Receita,
)
from app.models.estoque import MovimentacaoEstoque, ProdutoEstoque
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

__all__ = [
    "Perfil",
    "Usuario",
    "Permissao",
    "LogAuditoria",
    "Prontuario",
    "EvolucaoClinica",
    "Odontograma",
    "OdontogramaHistorico",
    "ExameAnexo",
    "Receita",
    "Atestado",
    "ProdutoEstoque",
    "MovimentacaoEstoque",
    "Procedimento",
    "Orcamento",
    "OrcamentoItem",
    "PlanoTratamento",
    "Convenio",
    "TabelaPrecosConvenio",
    "ContaReceber",
    "ContaPagar",
    "Pagamento",
    "ComissaoProfissional",
]
