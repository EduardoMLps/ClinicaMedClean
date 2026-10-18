"""
Utilitario de notificacoes ao paciente (RF19 - stub de lembrete de consulta).

IMPORTANTE: enviar_lembrete() NAO realiza nenhuma chamada de rede real.
Ela apenas registra, na tabela 'notificacoes_enviadas', que um lembrete
"seria" enviado, simulando o efeito de uma integracao real, para que o
restante do sistema (historico de comunicacao com o paciente, relatorios
de envio, etc.) tenha dados consistentes para exibir.

A integracao de fato com um provedor de mensageria (WhatsApp Business API,
gateway de SMS, servico de e-mail transacional) fica para uma fase futura
do projeto. Quando essa integracao for implementada, o bloco marcado
abaixo deve ser substituido pela chamada real ao provedor escolhido,
mantendo a mesma assinatura da funcao para nao quebrar quem ja a chama
(hoje, app/routes/agenda.py).
"""

from datetime import datetime

from app.extensions import db

CANAIS_VALIDOS = ("whatsapp", "sms", "email")


class NotificacaoEnviada(db.Model):
    """
    Mapeamento da tabela 'notificacoes_enviadas' (MODULO 8 do schema.sql:
    COMUNICACAO / CONFIGURACAO / LGPD).

    Definido aqui, proximo da funcao que a utiliza, pois o modulo de
    comunicacao/LGPD completo ainda nao foi implementado por outro time.
    Se/quando esse modulo ganhar seu proprio arquivo de models, este
    mapeamento devera ser movido para la (mantendo o mesmo __tablename__)
    para evitar duplicidade de mapeamento da mesma tabela.
    """

    __tablename__ = "notificacoes_enviadas"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    paciente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("pacientes.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    canal = db.Column(db.Enum(*CANAIS_VALIDOS, name="canal_notificacao"), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    enviado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "paciente_id": self.paciente_id,
            "canal": self.canal,
            "mensagem": self.mensagem,
            "enviado_em": self.enviado_em.isoformat() if self.enviado_em else None,
        }


def enviar_lembrete(agendamento, canal="whatsapp"):
    """
    STUB de envio de lembrete de consulta ao paciente de um agendamento.

    NAO realiza nenhuma integracao real com WhatsApp/SMS/E-mail -- apenas
    grava um registro em 'notificacoes_enviadas' simulando o envio.

    Parametros:
        agendamento: instancia de app.models.pacientes.Agendamento, ja
                     persistida (precisa ter paciente associado).
        canal: 'whatsapp' (padrao), 'sms' ou 'email'.

    Retorna a instancia de NotificacaoEnviada criada e persistida.

    Levanta ValueError se o agendamento for invalido/sem paciente, ou se
    o canal informado nao for suportado.
    """
    if agendamento is None:
        raise ValueError("E necessario informar um agendamento para enviar o lembrete.")
    if canal not in CANAIS_VALIDOS:
        raise ValueError(f"Canal invalido. Valores aceitos: {', '.join(CANAIS_VALIDOS)}.")

    paciente = agendamento.paciente
    if paciente is None:
        raise ValueError("O agendamento informado nao possui um paciente associado.")

    profissional = agendamento.profissional
    data_formatada = (
        agendamento.inicio.strftime("%d/%m/%Y as %H:%M")
        if agendamento.inicio
        else "data a confirmar"
    )

    mensagem = (
        f"Ola {paciente.nome}, este e um lembrete da sua consulta odontologica "
        f"marcada para {data_formatada}"
        + (f", com Dr(a). {profissional.nome}" if profissional else "")
        + ". Em caso de duvidas ou necessidade de reagendamento, entre em "
        "contato com a clinica."
    )

    # ---------------------------------------------------------------
    # NOTA (implementacao futura, fora do escopo atual): este bloco deve
    # ser substituido pela chamada real ao provedor de mensageria
    # (WhatsApp Business API / gateway de SMS / servico de e-mail),
    # incluindo tratamento de falha de entrega, confirmacao de leitura,
    # reenvio, etc. Por ora, apenas simulamos o envio gravando o registro
    # abaixo.
    # ---------------------------------------------------------------
    notificacao = NotificacaoEnviada(
        paciente_id=paciente.id,
        canal=canal,
        mensagem=mensagem,
        enviado_em=datetime.utcnow(),
    )
    db.session.add(notificacao)
    db.session.commit()
    return notificacao
