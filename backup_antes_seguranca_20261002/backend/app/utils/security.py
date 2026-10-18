"""
Utilitarios de seguranca: hashing de senha (bcrypt) e registro de
auditoria (log_auditoria) para operacoes de escrita em tabelas sensiveis
(prontuarios, pagamentos, usuarios, etc.), conforme padrao do time.
"""

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
        dados_antes=antes,
        dados_depois=depois,
    )
    db.session.add(log)
    db.session.commit()
    return log
