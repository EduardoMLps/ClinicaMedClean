"""
Models SQLAlchemy do modulo de acesso e seguranca (RF17, RF18).

Mapeamento 1:1 com as tabelas definidas em database/schema.sql:
    - perfis
    - usuarios
    - permissoes
    - log_auditoria
"""

from datetime import datetime

from app.extensions import db

# BIGINT UNSIGNED AUTO_INCREMENT em MySQL (producao, conforme schema.sql).
# O .with_variant garante que, em SQLite (usado em testes automatizados),
# a coluna vire INTEGER PRIMARY KEY -- unico tipo que o SQLite trata como
# alias de rowid autoincrementavel. Isso nao altera o DDL gerado para MySQL.
_ID_PK = db.BigInteger().with_variant(db.Integer, "sqlite")


class Perfil(db.Model):
    """Perfil de acesso (administrador, dentista, recepcao, financeiro, ...)."""

    __tablename__ = "perfis"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)

    usuarios = db.relationship(
        "Usuario", back_populates="perfil", lazy="select"
    )
    permissoes = db.relationship(
        "Permissao",
        back_populates="perfil",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}

    def __repr__(self):
        return f"<Perfil id={self.id} nome={self.nome!r}>"


class Usuario(db.Model):
    """Usuario com acesso de login ao sistema."""

    __tablename__ = "usuarios"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil_id = db.Column(
        db.BigInteger,
        db.ForeignKey("perfis.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # B9: profissional (dentista) que este usuario representa. Registros
    # clinicos feitos por ele saem sempre em nome deste profissional.
    profissional_id = db.Column(
        db.BigInteger,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )

    perfil = db.relationship("Perfil", back_populates="usuarios", lazy="joined")
    logs_auditoria = db.relationship(
        "LogAuditoria", back_populates="usuario", lazy="select"
    )

    def to_dict(self, incluir_perfil=True):
        """Serializa o usuario para JSON. NUNCA inclui senha_hash."""
        dados = {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "perfil_id": self.perfil_id,
            "ativo": bool(self.ativo),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "profissional_id": self.profissional_id,
        }
        if incluir_perfil and self.perfil is not None:
            dados["perfil_nome"] = self.perfil.nome
        return dados

    def __repr__(self):
        return f"<Usuario id={self.id} email={self.email!r}>"


class Permissao(db.Model):
    """Permissao granular (leitura/escrita) de um perfil sobre um recurso."""

    __tablename__ = "permissoes"
    __table_args__ = (
        db.UniqueConstraint(
            "perfil_id", "recurso", name="uq_permissoes_perfil_recurso"
        ),
    )

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    perfil_id = db.Column(
        db.BigInteger,
        db.ForeignKey("perfis.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    recurso = db.Column(db.String(100), nullable=False)
    pode_ler = db.Column(db.Boolean, nullable=False, default=False)
    pode_escrever = db.Column(db.Boolean, nullable=False, default=False)

    perfil = db.relationship("Perfil", back_populates="permissoes")

    def to_dict(self):
        return {
            "id": self.id,
            "perfil_id": self.perfil_id,
            "recurso": self.recurso,
            "pode_ler": bool(self.pode_ler),
            "pode_escrever": bool(self.pode_escrever),
        }

    def __repr__(self):
        return f"<Permissao perfil_id={self.perfil_id} recurso={self.recurso!r}>"


class LogAuditoria(db.Model):
    """Trilha de auditoria de alteracoes em qualquer tabela do sistema."""

    __tablename__ = "log_auditoria"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    acao = db.Column(db.String(50), nullable=False)
    tabela = db.Column(db.String(100), nullable=False)
    registro_id = db.Column(db.BigInteger, nullable=True)
    dados_antes = db.Column(db.JSON, nullable=True)
    dados_depois = db.Column(db.JSON, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario = db.relationship("Usuario", back_populates="logs_auditoria")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "acao": self.acao,
            "tabela": self.tabela,
            "registro_id": self.registro_id,
            "dados_antes": self.dados_antes,
            "dados_depois": self.dados_depois,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self):
        return f"<LogAuditoria id={self.id} tabela={self.tabela!r} acao={self.acao!r}>"


class TokenRevogado(db.Model):
    """
    JWT revogado antes de expirar (logout). Correcao B3.

    Guarda apenas o identificador unico do token (jti), nunca o token.
    Linhas com expira_em no passado podem ser apagadas a qualquer momento.
    """

    __tablename__ = "tokens_revogados"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(64), nullable=False, unique=True)
    usuario_id = db.Column(db.BigInteger, nullable=True)
    tipo = db.Column(db.String(10), nullable=False, default="access")
    expira_em = db.Column(db.DateTime, nullable=False)
    revogado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class RevogacaoSessaoUsuario(db.Model):
    """
    Marco de "encerrar todas as sessoes" de um usuario. Correcao B3.

    Todo token emitido antes de `revogado_em` passa a ser recusado. Atualizado
    quando o usuario troca de senha, de perfil, e desativado ou sai de todos
    os dispositivos.
    """

    __tablename__ = "revogacoes_sessao_usuario"

    usuario_id = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    revogado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
