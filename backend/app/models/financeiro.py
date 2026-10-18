"""
Models SQLAlchemy do modulo de orcamento e financeiro (RF08-RF13).

Mapeamento 1:1 com as tabelas definidas em database/schema.sql:
    - procedimentos
    - orcamentos
    - orcamento_itens
    - planos_tratamento
    - convenios
    - tabela_precos_convenio
    - contas_receber
    - contas_pagar
    - pagamentos
    - comissoes_profissionais

Observacao: as tabelas 'pacientes' e 'profissionais' pertencem a outros
modulos do sistema (RF01/RF02) e seus models SQLAlchemy nao sao definidos
aqui para evitar redeclaracao conflitante da mesma tabela em dois pontos
do codigo. As chaves estrangeiras abaixo apontam para essas tabelas pelo
nome (string), exatamente como no schema.sql; a validacao de existencia
dos ids de paciente/profissional e feita em app/routes/financeiro.py via
consulta parametrizada (sem concatenacao de string), seguindo o mesmo
padrao usado em app/routes/clinico.py.
"""

from datetime import datetime

from app.extensions import db

# BIGINT UNSIGNED AUTO_INCREMENT em MySQL (producao, conforme schema.sql).
# O .with_variant garante que, em SQLite (usado em testes automatizados),
# a coluna vire INTEGER PRIMARY KEY -- unico tipo que o SQLite trata como
# alias de rowid autoincrementavel. Isso nao altera o DDL gerado para MySQL.
_ID_PK = db.BigInteger().with_variant(db.Integer, "sqlite")
_FK_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")

# DECIMAL(10,2)/DECIMAL(5,2) do MySQL mapeados para db.Numeric, preservando
# precisao decimal exata (nunca usar float para dinheiro).
_MONEY = db.Numeric(10, 2)
_PERCENTUAL = db.Numeric(5, 2)


def _num(valor):
    """Converte um Numeric/Decimal do SQLAlchemy para float, seguro para JSON."""
    return float(valor) if valor is not None else None


class Procedimento(db.Model):
    """Catalogo de procedimentos odontologicos (RF08)."""

    __tablename__ = "procedimentos"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    preco = db.Column(_MONEY, nullable=False, default=0)

    itens_orcamento = db.relationship(
        "OrcamentoItem", back_populates="procedimento", lazy="select"
    )
    precos_convenio = db.relationship(
        "TabelaPrecosConvenio", back_populates="procedimento", lazy="select"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "preco": _num(self.preco),
        }

    def __repr__(self):
        return f"<Procedimento id={self.id} nome={self.nome!r}>"


class Orcamento(db.Model):
    """Orcamento proposto ao paciente (RF08, RF09)."""

    __tablename__ = "orcamentos"

    STATUS_VALIDOS = ("pendente", "aprovado", "recusado")

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_orcamento"),
        nullable=False,
        default="pendente",
    )
    total = db.Column(_MONEY, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    itens = db.relationship(
        "OrcamentoItem",
        back_populates="orcamento",
        lazy="select",
        cascade="all, delete-orphan",
    )
    planos_tratamento = db.relationship(
        "PlanoTratamento", back_populates="orcamento", lazy="select"
    )
    contas_receber = db.relationship(
        "ContaReceber", back_populates="orcamento", lazy="select"
    )
    pagamentos = db.relationship(
        "Pagamento", back_populates="orcamento", lazy="select"
    )
    comissoes = db.relationship(
        "ComissaoProfissional",
        back_populates="orcamento",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self, incluir_itens=False):
        dados = {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "status": self.status,
            "total": _num(self.total),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_itens:
            dados["itens"] = [item.to_dict() for item in self.itens]
        return dados

    def __repr__(self):
        return f"<Orcamento id={self.id} paciente_id={self.paciente_id} status={self.status!r}>"


class OrcamentoItem(db.Model):
    """Item de um orcamento: um procedimento e sua quantidade (RF08)."""

    __tablename__ = "orcamento_itens"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    orcamento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("orcamentos.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    procedimento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("procedimentos.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    quantidade = db.Column(db.SmallInteger, nullable=False, default=1)
    valor_unit = db.Column(_MONEY, nullable=False)

    orcamento = db.relationship("Orcamento", back_populates="itens")
    procedimento = db.relationship(
        "Procedimento", back_populates="itens_orcamento", lazy="joined"
    )

    def to_dict(self):
        subtotal = None
        if self.valor_unit is not None and self.quantidade is not None:
            subtotal = float(self.valor_unit) * int(self.quantidade)
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "procedimento_id": self.procedimento_id,
            "procedimento_nome": self.procedimento.nome if self.procedimento else None,
            "quantidade": self.quantidade,
            "valor_unit": _num(self.valor_unit),
            "subtotal": subtotal,
        }

    def __repr__(self):
        return f"<OrcamentoItem id={self.id} orcamento_id={self.orcamento_id}>"


class PlanoTratamento(db.Model):
    """Plano de tratamento originado de um orcamento aprovado (RF09)."""

    __tablename__ = "planos_tratamento"

    STATUS_VALIDOS = ("planejado", "em_andamento", "concluido", "cancelado")

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    orcamento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("orcamentos.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_plano_tratamento"),
        nullable=False,
        default="planejado",
    )
    iniciado_em = db.Column(db.DateTime, nullable=True)

    orcamento = db.relationship("Orcamento", back_populates="planos_tratamento")

    def to_dict(self):
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "paciente_id": self.paciente_id,
            "status": self.status,
            "iniciado_em": self.iniciado_em.isoformat() if self.iniciado_em else None,
        }

    def __repr__(self):
        return f"<PlanoTratamento id={self.id} orcamento_id={self.orcamento_id}>"


class Convenio(db.Model):
    """Convenio odontologico aceito pela clinica (RF10)."""

    __tablename__ = "convenios"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False, unique=True)

    tabela_precos = db.relationship(
        "TabelaPrecosConvenio",
        back_populates="convenio",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}

    def __repr__(self):
        return f"<Convenio id={self.id} nome={self.nome!r}>"


class TabelaPrecosConvenio(db.Model):
    """Preco negociado de um procedimento para um convenio especifico (RF10)."""

    __tablename__ = "tabela_precos_convenio"
    __table_args__ = (
        db.UniqueConstraint(
            "convenio_id", "procedimento_id", name="uq_tabela_precos_convenio_procedimento"
        ),
    )

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    convenio_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("convenios.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    procedimento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("procedimentos.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    preco = db.Column(_MONEY, nullable=False)

    convenio = db.relationship("Convenio", back_populates="tabela_precos")
    procedimento = db.relationship(
        "Procedimento", back_populates="precos_convenio", lazy="joined"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "convenio_id": self.convenio_id,
            "procedimento_id": self.procedimento_id,
            "procedimento_nome": self.procedimento.nome if self.procedimento else None,
            "preco": _num(self.preco),
        }

    def __repr__(self):
        return f"<TabelaPrecosConvenio convenio_id={self.convenio_id} procedimento_id={self.procedimento_id}>"


class ContaReceber(db.Model):
    """Conta a receber: parcela gerada a partir de um orcamento aprovado (RF09, RF11)."""

    __tablename__ = "contas_receber"

    STATUS_VALIDOS = ("pendente", "pago", "atrasado", "cancelado")

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    orcamento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("orcamentos.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    valor = db.Column(_MONEY, nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_conta_receber"),
        nullable=False,
        default="pendente",
    )

    orcamento = db.relationship("Orcamento", back_populates="contas_receber")

    def to_dict(self):
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "paciente_id": self.paciente_id,
            "valor": _num(self.valor),
            "vencimento": self.vencimento.isoformat() if self.vencimento else None,
            "status": self.status,
        }

    def __repr__(self):
        return f"<ContaReceber id={self.id} paciente_id={self.paciente_id} status={self.status!r}>"


class ContaPagar(db.Model):
    """Conta a pagar: despesa da clinica (RF12)."""

    __tablename__ = "contas_pagar"

    STATUS_VALIDOS = ("pendente", "pago", "atrasado", "cancelado")

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(_MONEY, nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_conta_pagar"),
        nullable=False,
        default="pendente",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "valor": _num(self.valor),
            "vencimento": self.vencimento.isoformat() if self.vencimento else None,
            "status": self.status,
        }

    def __repr__(self):
        return f"<ContaPagar id={self.id} descricao={self.descricao!r}>"


class Pagamento(db.Model):
    """Pagamento efetivamente recebido do paciente (RF11)."""

    __tablename__ = "pagamentos"

    FORMAS_VALIDAS = ("dinheiro", "cartao", "pix", "convenio")

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    orcamento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("orcamentos.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    valor = db.Column(_MONEY, nullable=False)
    forma = db.Column(db.Enum(*FORMAS_VALIDAS, name="forma_pagamento"), nullable=False)
    pago_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    orcamento = db.relationship("Orcamento", back_populates="pagamentos")

    def to_dict(self):
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "valor": _num(self.valor),
            "forma": self.forma,
            "pago_em": self.pago_em.isoformat() if self.pago_em else None,
        }

    def __repr__(self):
        return f"<Pagamento id={self.id} orcamento_id={self.orcamento_id} valor={self.valor}>"


class ComissaoProfissional(db.Model):
    """Comissao de um profissional sobre um orcamento executado/pago (RF13)."""

    __tablename__ = "comissoes_profissionais"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    profissional_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    orcamento_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("orcamentos.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    percentual = db.Column(_PERCENTUAL, nullable=False)
    valor_calculado = db.Column(_MONEY, nullable=False)

    orcamento = db.relationship("Orcamento", back_populates="comissoes")

    def to_dict(self):
        return {
            "id": self.id,
            "profissional_id": self.profissional_id,
            "orcamento_id": self.orcamento_id,
            "percentual": _num(self.percentual),
            "valor_calculado": _num(self.valor_calculado),
        }

    def __repr__(self):
        return (
            f"<ComissaoProfissional id={self.id} profissional_id={self.profissional_id} "
            f"orcamento_id={self.orcamento_id}>"
        )
