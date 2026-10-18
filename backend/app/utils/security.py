"""
Utilitarios de seguranca: hashing de senha (bcrypt) e registro de
auditoria (log_auditoria) para operacoes de escrita em tabelas sensiveis
(prontuarios, pagamentos, usuarios, etc.), conforme padrao do time.
"""

import re
from datetime import datetime, timedelta

import bcrypt

from app.extensions import db


def hash_senha(senha: str) -> str:
    """
    Gera o hash bcrypt de uma senha em texto puro.

    Levanta ValueError se a senha nao for uma string valida e nao vazia.
    """
    if not senha or not isinstance(senha, str):
        raise ValueError("A senha informada para hashing e invalida.")

    senha_bytes = senha.encode("utf-8")
    hash_bytes = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """
    Compara uma senha em texto puro com um hash bcrypt previamente
    armazenado. Retorna False (nunca levanta excecao) para qualquer
    entrada invalida ou hash corrompido/incompativel.
    """
    if not senha or not isinstance(senha, str):
        return False
    if not hash_armazenado or not isinstance(hash_armazenado, str):
        return False

    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def registrar_auditoria(usuario_id, acao, tabela, registro_id=None, antes=None, depois=None):
    """
    Grava um registro na tabela log_auditoria.

    Parametros:
        usuario_id  (int|None): id do usuario que executou a acao (pode ser
                                 None para acoes automaticas do sistema).
        acao        (str): ex. 'criar', 'atualizar', 'excluir', 'login'.
        tabela      (str): nome da tabela afetada, ex. 'usuarios'.
        registro_id (int|None): id do registro afetado na tabela indicada.
        antes       (dict|None): estado do registro antes da alteracao.
        depois      (dict|None): estado do registro depois da alteracao.

    Retorna a instancia de LogAuditoria criada e ja persistida.
    """
    # Import tardio para evitar dependencia circular entre
    # app.utils.security e app.models.auth.
    from app.models.auth import LogAuditoria

    if not acao or not isinstance(acao, str):
        raise ValueError("O campo 'acao' e obrigatorio para registrar auditoria.")
    if not tabela or not isinstance(tabela, str):
        raise ValueError("O campo 'tabela' e obrigatorio para registrar auditoria.")

    log = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        tabela=tabela,
        registro_id=registro_id,
        dados_antes=_sanitizar_para_log(antes),
        dados_depois=_sanitizar_para_log(depois),
    )
    db.session.add(log)
    db.session.commit()
    return log


# Hash bcrypt de uma senha aleatoria descartavel. Usado no login quando o
# e-mail nao existe, para que a resposta demore o mesmo que um e-mail
# valido com senha errada (B11: evita descobrir e-mails pelo tempo).
HASH_FICTICIO_PARA_TEMPO = bcrypt.hashpw(b"medflow-hash-ficticio", bcrypt.gensalt()).decode()


def consumir_tempo_de_verificacao(senha):
    """Executa uma verificacao bcrypt descartavel (resultado ignorado)."""
    verificar_senha(senha or "x", HASH_FICTICIO_PARA_TEMPO)


# ---------------------------------------------------------------------------
# Politica de senha (B12)
# ---------------------------------------------------------------------------

TAMANHO_MINIMO_SENHA = 10

_SENHAS_COMUNS = {
    "1234567890", "12345678910", "0123456789", "senha12345", "senha123456",
    "password123", "qwertyuiop", "abcdefghij", "abc1234567", "admin12345",
    "administrador", "clinica123", "medflow123", "teste12345", "mudar12345",
    "brasil12345", "dentista123", "odonto12345", "testesenha123!",
}


def validar_politica_senha(senha, email=None, nome=None):
    """
    Retorna a lista de problemas da senha (vazia se estiver de acordo):
    minimo de 10 caracteres, letras e numeros, nao ser uma senha comum e
    nao conter o e-mail ou o nome do usuario.
    """
    problemas = []
    if not isinstance(senha, str) or not senha:
        return ["Informe uma senha."]
    if len(senha) < TAMANHO_MINIMO_SENHA:
        problemas.append(f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if len(senha.encode("utf-8")) > 72:
        # Limite do algoritmo bcrypt (o bcrypt 5 recusa senhas maiores).
        problemas.append("A senha deve ter no maximo 72 caracteres.")
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        problemas.append("A senha deve ter letras e numeros.")
    minuscula = senha.lower()
    if minuscula in _SENHAS_COMUNS or len(set(senha)) < 5:
        problemas.append("Essa senha e muito comum ou facil de adivinhar.")
    if email and isinstance(email, str):
        local = email.split("@")[0].lower()
        if len(local) >= 4 and local in minuscula:
            problemas.append("A senha nao pode conter o e-mail do usuario.")
    if nome and isinstance(nome, str):
        for parte in nome.lower().split():
            if len(parte) >= 4 and parte in minuscula:
                problemas.append("A senha nao pode conter o nome do usuario.")
                break
    return problemas


# ---------------------------------------------------------------------------
# Dados pessoais: mascaramento (B4, B13)
# ---------------------------------------------------------------------------


def mascarar_cpf(cpf):
    """'12345678901' -> '***.456.789-**'. Mantem None/vazio como esta."""
    if not cpf:
        return cpf
    digitos = re.sub(r"\D", "", str(cpf))
    if len(digitos) != 11:
        return "***"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


_CHAVES_CPF = {"cpf", "cpf_paciente", "cpf_responsavel", "cpf_cnpj", "documento"}


def _sanitizar_para_log(dados):
    """B13: o log de auditoria guarda o CPF mascarado, nunca completo."""
    if isinstance(dados, dict):
        return {
            chave: (mascarar_cpf(valor) if chave in _CHAVES_CPF and isinstance(valor, str)
                    else _sanitizar_para_log(valor))
            for chave, valor in dados.items()
        }
    if isinstance(dados, list):
        return [_sanitizar_para_log(item) for item in dados]
    return dados


def limpar_logs_auditoria_antigos(dias):
    """B13: remove registros de auditoria com mais de `dias` dias."""
    from app.models.auth import LogAuditoria

    if not dias or int(dias) < 1:
        raise ValueError("Informe um prazo de retencao valido (em dias).")
    limite = datetime.utcnow() - timedelta(days=int(dias))
    apagados = LogAuditoria.query.filter(LogAuditoria.criado_em < limite).delete(
        synchronize_session=False
    )
    db.session.commit()
    return apagados


def registrar_leitura(usuario_id, tabela, registro_id=None, detalhes=None):
    """
    B5 (LGPD): registra que um usuario LEU dados sensiveis (prontuario,
    odontograma, ficha completa do paciente). Grava em log_auditoria com
    acao='ler'. Falha de gravacao nao impede a leitura, mas e logada.
    """
    try:
        registrar_auditoria(
            usuario_id=usuario_id,
            acao="ler",
            tabela=tabela,
            registro_id=registro_id,
            antes=None,
            depois=detalhes,
        )
    except Exception:  # pragma: no cover - nao bloquear atendimento
        import logging

        db.session.rollback()
        logging.getLogger(__name__).exception(
            "Falha ao registrar leitura em log_auditoria (%s/%s).", tabela, registro_id
        )


def escapar_like(termo):
    """
    B14: escapa %, _ e \\ digitados pelo usuario em buscas com LIKE, para que
    sejam tratados como texto e nao como curinga. Use junto com
    `.ilike(f"%{escapar_like(t)}%", escape="\\\\")`.
    """
    return (
        str(termo)
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
