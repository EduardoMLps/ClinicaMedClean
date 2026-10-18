"""
Models SQLAlchemy do modulo de estoque (RF14).

Mapeamento 1:1 com as tabelas definidas em database/schema.sql:
    - produtos_estoque
    - movimentacoes_estoque
"""

from datetime import datetime

from app.extensions import db

# BIGINT UNSIGNED AUTO_INCREMENT em MySQL (producao, conforme schema.sql).
# O .with_variant garante que, em SQLite (usado em testes automatizados),
# a coluna vire INTEGER PRIMARY KEY -- unico tipo que o SQLite trata como
# alias de rowid autoincrementavel. Isso nao altera o DDL gerado para MySQL.
_ID_PK = db.BigInteger().with_variant(db.Integer, "sqlite")
_FK_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")

TIPOS_MOVIMENTACAO_ESTOQUE = ("entrada", "saida")


class ProdutoEstoque(db.Model):
    """Produto/material de consumo controlado pelo estoque da clinica (RF14)."""

    __tablename__ = "produtos_estoque"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    quantidade_minima = db.Column(db.Integer, nullable=False, default=0)
    unidade = db.Column(db.String(20), nullable=False)

    movimentacoes = db.relationship(
        "MovimentacaoEstoque",
        back_populates="produto",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="MovimentacaoEstoque.criado_em.desc()",
    )

    @property
    def abaixo_do_minimo(self):
        """True quando a quantidade atual esta no ou abaixo do minimo definido (RF14)."""
        return self.quantidade <= self.quantidade_minima

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "quantidade": self.quantidade,
            "quantidade_minima": self.quantidade_minima,
            "unidade": self.unidade,
            "abaixo_do_minimo": self.abaixo_do_minimo,
        }

    def __repr__(self):
        return f"<ProdutoEstoque id={self.id} nome={self.nome!r} quantidade={self.quantidade}>"


class MovimentacaoEstoque(db.Model):
    """Movimentacao de entrada ou saida de um produto do estoque (RF14)."""

    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (
        db.CheckConstraint("quantidade > 0", name="chk_movimentacoes_quantidade"),
    )

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    produto_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("produtos_estoque.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    tipo = db.Column(
        db.Enum(*TIPOS_MOVIMENTACAO_ESTOQUE, name="tipo_movimentacao_estoque"),
        nullable=False,
    )
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    produto = db.relationship("ProdutoEstoque", back_populates="movimentacoes")

    def to_dict(self):
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "tipo": self.tipo,
            "quantidade": self.quantidade,
            "motivo": self.motivo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self):
        return (
            f"<MovimentacaoEstoque id={self.id} produto_id={self.produto_id} "
            f"tipo={self.tipo!r} quantidade={self.quantidade}>"
        )
