"""
Models SQLAlchemy do modulo de pacientes e agenda (RF01, RF02, RF03-stub, RF19).

Mapeamento 1:1 com as tabelas definidas em database/schema.sql:
    - especialidades
    - profissionais
    - pacientes
    - enderecos
    - cadeiras_consultorio
    - agendamentos
    - bloqueios_agenda
"""

from datetime import date, datetime

from app.extensions import db


class Especialidade(db.Model):
    """Especialidade odontologica (ortodontia, endodontia, etc.)."""

    __tablename__ = "especialidades"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

    profissionais = db.relationship(
        "Profissional", back_populates="especialidade", lazy="select"
    )

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}

    def __repr__(self):
        return f"<Especialidade id={self.id} nome={self.nome!r}>"


class Profissional(db.Model):
    """Profissional (dentista) da clinica."""

    __tablename__ = "profissionais"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    especialidade_id = db.Column(
        db.BigInteger,
        db.ForeignKey("especialidades.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    registro_conselho = db.Column(db.String(30), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    especialidade = db.relationship(
        "Especialidade", back_populates="profissionais", lazy="joined"
    )
    agendamentos = db.relationship(
        "Agendamento", back_populates="profissional", lazy="select"
    )
    bloqueios = db.relationship(
        "BloqueioAgenda",
        back_populates="profissional",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "especialidade_id": self.especialidade_id,
            "especialidade_nome": self.especialidade.nome if self.especialidade else None,
            "registro_conselho": self.registro_conselho,
            "ativo": bool(self.ativo),
        }

    def __repr__(self):
        return f"<Profissional id={self.id} nome={self.nome!r}>"


class Paciente(db.Model):
    """Paciente da clinica (RF01). Pode ter um responsavel (para menores de idade)."""

    __tablename__ = "pacientes"

    IDADE_MAIORIDADE = 18

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    data_nascimento = db.Column(db.Date, nullable=False)
    responsavel_id = db.Column(
        db.BigInteger,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    # A FK real (a nivel de banco) para consentimentos_lgpd(id) ja e criada
    # via ALTER TABLE em schema.sql (dependencia circular pacientes <->
    # consentimentos_lgpd). O modelo ConsentimentoLGPD pertence ao modulo de
    # LGPD/comunicacao (fora do escopo deste arquivo); por isso, aqui a
    # coluna e mapeada SEM db.ForeignKey(...) apontando para uma tabela cujo
    # model nao existe neste modulo -- isso evita que db.create_all()/testes
    # deste modulo quebrem por causa de uma tabela que nao lhe pertence. A
    # integridade referencial continua garantida pelo MySQL (schema.sql).
    consentimento_lgpd_id = db.Column(db.BigInteger, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    responsavel = db.relationship(
        "Paciente",
        remote_side=[id],
        backref=db.backref("dependentes", lazy="select"),
    )
    enderecos = db.relationship(
        "Endereco",
        back_populates="paciente",
        lazy="select",
        cascade="all, delete-orphan",
    )
    agendamentos = db.relationship(
        "Agendamento", back_populates="paciente", lazy="select"
    )

    @property
    def idade(self):
        """Calcula a idade atual do paciente a partir de data_nascimento."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        nasc = self.data_nascimento
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))

    @property
    def eh_menor_de_idade(self):
        idade_atual = self.idade
        return idade_atual is not None and idade_atual < self.IDADE_MAIORIDADE

    def to_dict(self, incluir_enderecos=False):
        dados = {
            "id": self.id,
            "nome": self.nome,
            "cpf": self.cpf,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "idade": self.idade,
            "menor_de_idade": self.eh_menor_de_idade,
            "responsavel_id": self.responsavel_id,
            "telefone": self.telefone,
            "email": self.email,
            "consentimento_lgpd_id": self.consentimento_lgpd_id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_enderecos:
            dados["enderecos"] = [e.to_dict() for e in self.enderecos]
        return dados

    def __repr__(self):
        return f"<Paciente id={self.id} nome={self.nome!r}>"


class Endereco(db.Model):
    """Endereco de um paciente."""

    __tablename__ = "enderecos"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    logradouro = db.Column(db.String(200), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(9), nullable=False)

    paciente = db.relationship("Paciente", back_populates="enderecos")

    def to_dict(self):
        return {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "logradouro": self.logradouro,
            "cidade": self.cidade,
            "uf": self.uf,
            "cep": self.cep,
        }

    def __repr__(self):
        return f"<Endereco id={self.id} paciente_id={self.paciente_id}>"


class CadeiraConsultorio(db.Model):
    """Cadeira/consultorio fisico da clinica."""

    __tablename__ = "cadeiras_consultorio"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(50), nullable=False)

    agendamentos = db.relationship(
        "Agendamento", back_populates="cadeira", lazy="select"
    )

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}

    def __repr__(self):
        return f"<CadeiraConsultorio id={self.id} nome={self.nome!r}>"


class Agendamento(db.Model):
    """Agendamento de consulta (RF02). Vincula paciente + profissional (+ cadeira)."""

    __tablename__ = "agendamentos"

    STATUS_VALIDOS = (
        "agendado",
        "confirmado",
        "em_atendimento",
        "concluido",
        "faltou",
        "cancelado",
    )
    # Status que efetivamente "ocupam" a agenda do profissional/cadeira
    # para fins de checagem de conflito de horario.
    STATUS_ATIVOS = ("agendado", "confirmado", "em_atendimento")

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    profissional_id = db.Column(
        db.BigInteger,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    cadeira_id = db.Column(
        db.BigInteger,
        db.ForeignKey("cadeiras_consultorio.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.Enum(*STATUS_VALIDOS, name="status_agendamento"),
        nullable=False,
        default="agendado",
    )

    paciente = db.relationship("Paciente", back_populates="agendamentos")
    profissional = db.relationship("Profissional", back_populates="agendamentos")
    cadeira = db.relationship("CadeiraConsultorio", back_populates="agendamentos")

    def to_dict(self):
        return {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "paciente_nome": self.paciente.nome if self.paciente else None,
            "profissional_id": self.profissional_id,
            "profissional_nome": self.profissional.nome if self.profissional else None,
            "cadeira_id": self.cadeira_id,
            "cadeira_nome": self.cadeira.nome if self.cadeira else None,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fim": self.fim.isoformat() if self.fim else None,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Agendamento id={self.id} profissional_id={self.profissional_id} inicio={self.inicio}>"


class BloqueioAgenda(db.Model):
    """Bloqueio de agenda (ferias, folgas, eventos) de um profissional."""

    __tablename__ = "bloqueios_agenda"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    profissional_id = db.Column(
        db.BigInteger,
        db.ForeignKey("profissionais.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)

    profissional = db.relationship("Profissional", back_populates="bloqueios")

    def to_dict(self):
        return {
            "id": self.id,
            "profissional_id": self.profissional_id,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fim": self.fim.isoformat() if self.fim else None,
            "motivo": self.motivo,
        }

    def __repr__(self):
        return f"<BloqueioAgenda id={self.id} profissional_id={self.profissional_id}>"
