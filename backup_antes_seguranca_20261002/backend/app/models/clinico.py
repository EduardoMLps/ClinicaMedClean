"""
Models SQLAlchemy do modulo clinico: prontuario e odontograma (RF04, RF05,
RF06, RF07).

Mapeamento 1:1 com as tabelas definidas em database/schema.sql:
    - prontuarios
    - evolucoes_clinicas
    - odontograma
    - odontograma_historico
    - exames_anexos
    - receitas
    - atestados

Observacao: as tabelas 'pacientes' e 'profissionais' pertencem a outros
modulos do sistema (RF01/RF02) e seus models SQLAlchemy nao sao definidos
aqui para evitar redeclaracao conflitante da mesma tabela em dois pontos
do codigo. As chaves estrangeiras abaixo apontam para essas tabelas pelo
nome (string), exatamente como no schema.sql; a validacao de existencia
dos ids de paciente/profissional e feita em app/routes/clinico.py via
consulta parametrizada (sem concatenacao de string).
"""

from datetime import datetime

from app.extensions import db

# BIGINT UNSIGNED AUTO_INCREMENT em MySQL (producao, conforme schema.sql).
# O .with_variant garante que, em SQLite (usado em testes automatizados),
# a coluna vire INTEGER PRIMARY KEY -- unico tipo que o SQLite trata como
# alias de rowid autoincrementavel. Isso nao altera o DDL gerado para MySQL.
_ID_PK = db.BigInteger().with_variant(db.Integer, "sqlite")
_FK_BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")

FACES_VALIDAS = ("oclusal", "mesial", "distal", "vestibular", "lingual")


class Prontuario(db.Model):
    """Prontuario clinico do paciente (RF04)."""

    __tablename__ = "prontuarios"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    profissional_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    evolucoes = db.relationship(
        "EvolucaoClinica",
        back_populates="prontuario",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="EvolucaoClinica.criado_em.desc()",
    )
    receitas = db.relationship(
        "Receita",
        back_populates="prontuario",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="Receita.emitido_em.desc()",
    )
    atestados = db.relationship(
        "Atestado",
        back_populates="prontuario",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="Atestado.emitido_em.desc()",
    )

    def to_dict(self, incluir_evolucoes=False):
        dados = {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "profissional_id": self.profissional_id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_evolucoes:
            dados["evolucoes"] = [e.to_dict() for e in self.evolucoes]
        return dados

    def __repr__(self):
        return f"<Prontuario id={self.id} paciente_id={self.paciente_id}>"


class EvolucaoClinica(db.Model):
    """Evolucao clinica (registro de atendimento) dentro do prontuario (RF04)."""

    __tablename__ = "evolucoes_clinicas"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    prontuario_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("prontuarios.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    profissional_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    prontuario = db.relationship("Prontuario", back_populates="evolucoes")

    def to_dict(self):
        return {
            "id": self.id,
            "prontuario_id": self.prontuario_id,
            "profissional_id": self.profissional_id,
            "texto": self.texto,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self):
        return f"<EvolucaoClinica id={self.id} prontuario_id={self.prontuario_id}>"


class Odontograma(db.Model):
    """Situacao atual de uma face de um dente do paciente (RF06)."""

    __tablename__ = "odontograma"
    __table_args__ = (
        db.CheckConstraint(
            "dente_fdi BETWEEN 11 AND 85", name="chk_odontograma_dente_fdi"
        ),
    )

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    dente_fdi = db.Column(db.SmallInteger, nullable=False)
    face = db.Column(db.Enum(*FACES_VALIDAS, name="face_odontograma"), nullable=False)
    situacao = db.Column(db.String(60), nullable=False)
    registrado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    profissional_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    historico = db.relationship(
        "OdontogramaHistorico",
        back_populates="odontograma",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="OdontogramaHistorico.alterado_em.desc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "dente_fdi": self.dente_fdi,
            "face": self.face,
            "situacao": self.situacao,
            "registrado_em": self.registrado_em.isoformat() if self.registrado_em else None,
            "profissional_id": self.profissional_id,
        }

    def __repr__(self):
        return (
            f"<Odontograma id={self.id} paciente_id={self.paciente_id} "
            f"dente_fdi={self.dente_fdi} face={self.face!r}>"
        )


class OdontogramaHistorico(db.Model):
    """Historico de alteracoes do odontograma: valor anterior antes de sobrescrever (RF06)."""

    __tablename__ = "odontograma_historico"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    odontograma_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("odontograma.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    situacao_anterior = db.Column(db.String(60), nullable=False)
    alterado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    odontograma = db.relationship("Odontograma", back_populates="historico")

    def to_dict(self):
        return {
            "id": self.id,
            "odontograma_id": self.odontograma_id,
            "situacao_anterior": self.situacao_anterior,
            "alterado_em": self.alterado_em.isoformat() if self.alterado_em else None,
        }

    def __repr__(self):
        return f"<OdontogramaHistorico id={self.id} odontograma_id={self.odontograma_id}>"


class ExameAnexo(db.Model):
    """Exame ou anexo (radiografia, foto, laudo) do paciente (RF05)."""

    __tablename__ = "exames_anexos"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    tipo = db.Column(db.String(60), nullable=False)
    arquivo_url = db.Column(db.String(500), nullable=False)
    enviado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "tipo": self.tipo,
            "arquivo_url": self.arquivo_url,
            "enviado_em": self.enviado_em.isoformat() if self.enviado_em else None,
        }

    def __repr__(self):
        return f"<ExameAnexo id={self.id} paciente_id={self.paciente_id} tipo={self.tipo!r}>"


class Receita(db.Model):
    """Receita emitida a partir do prontuario (RF07)."""

    __tablename__ = "receitas"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    prontuario_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("prontuarios.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    texto = db.Column(db.Text, nullable=False)
    emitido_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    prontuario = db.relationship("Prontuario", back_populates="receitas")

    def to_dict(self):
        return {
            "id": self.id,
            "prontuario_id": self.prontuario_id,
            "texto": self.texto,
            "emitido_em": self.emitido_em.isoformat() if self.emitido_em else None,
        }

    def __repr__(self):
        return f"<Receita id={self.id} prontuario_id={self.prontuario_id}>"


class Atestado(db.Model):
    """Atestado emitido a partir do prontuario (RF07)."""

    __tablename__ = "atestados"

    id = db.Column(_ID_PK, primary_key=True, autoincrement=True)
    prontuario_id = db.Column(
        _FK_BIGINT,
        db.ForeignKey("prontuarios.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    texto = db.Column(db.Text, nullable=False)
    dias_afastamento = db.Column(db.SmallInteger, nullable=False, default=0)
    emitido_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    prontuario = db.relationship("Prontuario", back_populates="atestados")

    def to_dict(self):
        return {
            "id": self.id,
            "prontuario_id": self.prontuario_id,
            "texto": self.texto,
            "dias_afastamento": self.dias_afastamento,
            "emitido_em": self.emitido_em.isoformat() if self.emitido_em else None,
        }

    def __repr__(self):
        return f"<Atestado id={self.id} prontuario_id={self.prontuario_id}>"
