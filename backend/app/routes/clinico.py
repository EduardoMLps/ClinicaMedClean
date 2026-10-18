"""
Blueprint 'clinico' -- prontuario clinico e odontograma (RF04, RF05, RF06, RF07).

Rotas expostas sob o prefixo /api/v1:
    GET  /api/v1/prontuarios/<paciente_id>            -> lista prontuarios do paciente
    POST /api/v1/prontuarios/<paciente_id>             -> cria um novo prontuario
    POST /api/v1/prontuarios/<prontuario_id>/evolucoes -> registra uma evolucao clinica
    GET  /api/v1/odontograma/<paciente_id>             -> retorna os 32 dentes (5 faces cada)
    PUT  /api/v1/odontograma/<paciente_id>             -> atualiza uma ou mais faces
    POST /api/v1/exames                                -> upload de exame/anexo do paciente
    POST /api/v1/receitas                              -> emite receita a partir do prontuario
    POST /api/v1/atestados                             -> emite atestado a partir do prontuario

Todas as rotas de leitura de prontuario/odontograma exigem JWT valido +
perfil clinico autorizado (PERFIS_LEITURA_CLINICA), pois retornam dados
clinicos sensiveis (diagnosticos, evolucoes, historico odontologico).
Todas as rotas de escrita exigem JWT valido + perfil autorizado, e toda
escrita em prontuarios/evolucoes/odontograma/exames/receitas/atestados
chama registrar_auditoria (grava em log_auditoria).
"""

import os
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_current_user, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.clinico import (
    FACES_VALIDAS,
    Atestado,
    EvolucaoClinica,
    ExameAnexo,
    Odontograma,
    OdontogramaHistorico,
    Prontuario,
    Receita,
)
from app.utils.auth_decorators import require_perfil
from app.utils.security import registrar_auditoria, registrar_leitura

clinico_bp = Blueprint("clinico", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------
# Constantes de dominio
# ---------------------------------------------------------------------------

PERFIS_ESCRITA_CLINICA = ["administrador", "dentista"]
PERFIS_ESCRITA_EXAMES = ["administrador", "dentista", "recepcao"]

# Prontuarios e odontograma contem dados clinicos sensiveis (diagnosticos,
# evolucoes, historico odontologico). A leitura e restrita aos mesmos
# perfis autorizados a escrever nesses dados -- perfis nao-clinicos
# (recepcao, financeiro) nao tem motivo de negocio para ver esse conteudo.
PERFIS_LEITURA_CLINICA = ["administrador", "dentista"]

# Os 32 dentes permanentes em notacao FDI (RF06: "retorna os 32 dentes").
DENTES_PERMANENTES = (
    11, 12, 13, 14, 15, 16, 17, 18,
    21, 22, 23, 24, 25, 26, 27, 28,
    31, 32, 33, 34, 35, 36, 37, 38,
    41, 42, 43, 44, 45, 46, 47, 48,
)
# Dentes deciduos (infantis) tambem validos conforme CHECK do schema
# (dente_fdi BETWEEN 11 AND 85), permitidos na escrita do odontograma
# mesmo que a grade padrao de leitura mostre apenas os 32 permanentes.
DENTES_DECIDUOS = (
    51, 52, 53, 54, 55,
    61, 62, 63, 64, 65,
    71, 72, 73, 74, 75,
    81, 82, 83, 84, 85,
)
DENTES_VALIDOS = set(DENTES_PERMANENTES) | set(DENTES_DECIDUOS)

SITUACAO_PADRAO = "higido"
TAMANHO_MAXIMO_SITUACAO = 60

EXTENSOES_PERMITIDAS_EXAME = {"pdf", "jpg", "jpeg", "png"}
TAMANHO_MAXIMO_EXAME_BYTES = 10 * 1024 * 1024  # 10 MB

# Assinaturas (magic bytes) minimas dos formatos aceitos, para reduzir o
# risco de um arquivo malicioso disfarcado com extensao permitida.
_ASSINATURAS_ARQUIVO = {
    "pdf": (b"%PDF-",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _identidade_do_ator() -> int:
    """Extrai o id (int) do usuario autenticado a partir do JWT."""
    return int(get_jwt_identity())


class ErroProfissional(Exception):
    def __init__(self, mensagem, status):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _profissional_do_ator(valor_informado, rotulo="profissional_id"):
    """
    B9: define em nome de qual profissional o registro clinico sera feito.

    - Usuario vinculado a um profissional: usa SEMPRE o profissional dele.
      Se o corpo trouxer outro profissional_id, recusa com 403.
    - Administrador sem vinculo: pode informar o profissional_id (registro
      feito em nome de alguem, fica no log de auditoria com o id do admin).
    - Demais usuarios sem vinculo: recusa com 403.

    Retorna o id do profissional ou levanta ErroProfissional.
    """
    usuario = get_current_user()
    if usuario is not None and usuario.profissional_id:
        if valor_informado not in (None, "") and valor_informado != usuario.profissional_id:
            raise ErroProfissional(
                "Voce so pode registrar atendimentos em seu proprio nome.", 403
            )
        if not _profissional_existe(usuario.profissional_id):
            raise ErroProfissional(
                "O profissional vinculado ao seu usuario esta inativo. "
                "Fale com o administrador.",
                403,
            )
        return usuario.profissional_id

    perfil = usuario.perfil.nome if usuario is not None and usuario.perfil else None
    if perfil != "administrador":
        raise ErroProfissional(
            "Seu usuario nao esta vinculado a um profissional. Peca ao "
            "administrador para fazer o vinculo em Usuarios.",
            403,
        )

    profissional_id, erro = _validar_inteiro_positivo(valor_informado, rotulo)
    if erro:
        raise ErroProfissional(erro, 400)
    if not _profissional_existe(profissional_id):
        raise ErroProfissional(
            f"Profissional com id {profissional_id} nao encontrado ou inativo.", 400
        )
    return profissional_id


def _paciente_existe(paciente_id) -> bool:
    """
    Verifica se o paciente existe, via consulta parametrizada (sem
    concatenacao de string). O model Paciente pertence a outro modulo
    do sistema, por isso a checagem e feita diretamente na tabela.
    """
    resultado = db.session.execute(
        db.text("SELECT id FROM pacientes WHERE id = :paciente_id"),
        {"paciente_id": paciente_id},
    ).first()
    return resultado is not None


def _profissional_existe(profissional_id) -> bool:
    """Verifica se o profissional existe e esta ativo, via consulta parametrizada."""
    resultado = db.session.execute(
        db.text(
            "SELECT id FROM profissionais WHERE id = :profissional_id AND ativo = 1"
        ),
        {"profissional_id": profissional_id},
    ).first()
    return resultado is not None


def _validar_inteiro_positivo(valor, nome_campo):
    """Retorna (valor_int, None) ou (None, mensagem_de_erro)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, f"Campo '{nome_campo}' e obrigatorio e deve ser um numero inteiro."
    if valor <= 0:
        return None, f"Campo '{nome_campo}' deve ser um numero inteiro positivo."
    return valor, None


def _montar_grade_odontograma(paciente_id):
    """Monta a grade dos 32 dentes permanentes, cada um com as 5 faces e a
    situacao atual (ou 'higido' caso nunca tenha sido registrada)."""
    registros = Odontograma.query.filter_by(paciente_id=paciente_id).all()
    mapa = {(r.dente_fdi, r.face): r for r in registros}

    dentes = []
    for dente in DENTES_PERMANENTES:
        faces = {}
        for face in FACES_VALIDAS:
            registro = mapa.get((dente, face))
            if registro is not None:
                faces[face] = {
                    "odontograma_id": registro.id,
                    "situacao": registro.situacao,
                    "registrado_em": registro.registrado_em.isoformat()
                    if registro.registrado_em
                    else None,
                    "profissional_id": registro.profissional_id,
                }
            else:
                faces[face] = {
                    "odontograma_id": None,
                    "situacao": SITUACAO_PADRAO,
                    "registrado_em": None,
                    "profissional_id": None,
                }
        dentes.append({"dente_fdi": dente, "faces": faces})

    return {"paciente_id": paciente_id, "dentes": dentes}


# ---------------------------------------------------------------------------
# Prontuario (RF04)
# ---------------------------------------------------------------------------


@clinico_bp.get("/prontuarios/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_LEITURA_CLINICA)
def listar_prontuarios(paciente_id):
    if not _paciente_existe(paciente_id):
        return jsonify({"erro": f"Paciente com id {paciente_id} nao encontrado."}), 404

    prontuarios = (
        Prontuario.query.filter_by(paciente_id=paciente_id)
        .order_by(Prontuario.criado_em.desc())
        .all()
    )
    # B5 (LGPD): toda leitura de prontuario fica registrada.
    registrar_leitura(
        _identidade_do_ator(),
        "prontuarios",
        registro_id=paciente_id,
        detalhes={"paciente_id": paciente_id, "prontuarios": [p.id for p in prontuarios]},
    )
    return (
        jsonify(
            {
                "paciente_id": paciente_id,
                "prontuarios": [p.to_dict(incluir_evolucoes=True) for p in prontuarios],
                "total": len(prontuarios),
            }
        ),
        200,
    )


@clinico_bp.post("/prontuarios/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CLINICA)
def criar_prontuario(paciente_id):
    if not _paciente_existe(paciente_id):
        return jsonify({"erro": f"Paciente com id {paciente_id} nao encontrado."}), 404

    # Dentista vinculado nao precisa enviar nada: o profissional e o dele (B9).
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    try:
        profissional_id = _profissional_do_ator(payload.get("profissional_id"))
    except ErroProfissional as exc:
        return jsonify({"erro": exc.mensagem}), exc.status

    novo_prontuario = Prontuario(paciente_id=paciente_id, profissional_id=profissional_id)
    db.session.add(novo_prontuario)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="prontuarios",
        registro_id=novo_prontuario.id,
        antes=None,
        depois=novo_prontuario.to_dict(),
    )

    return jsonify(novo_prontuario.to_dict()), 201


@clinico_bp.post("/prontuarios/<int:prontuario_id>/evolucoes")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CLINICA)
def criar_evolucao(prontuario_id):
    prontuario = Prontuario.query.get(prontuario_id)
    if prontuario is None:
        return jsonify({"erro": f"Prontuario com id {prontuario_id} nao encontrado."}), 404

    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    erros = []

    texto = payload.get("texto")
    if not texto or not isinstance(texto, str) or not texto.strip():
        erros.append("Campo 'texto' e obrigatorio e deve ser texto nao vazio.")

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    # B9: o profissional da evolucao e o do usuario logado, nao o do corpo.
    try:
        profissional_id = _profissional_do_ator(payload.get("profissional_id"))
    except ErroProfissional as exc:
        return jsonify({"erro": exc.mensagem}), exc.status

    nova_evolucao = EvolucaoClinica(
        prontuario_id=prontuario.id,
        profissional_id=profissional_id,
        texto=texto.strip(),
    )
    db.session.add(nova_evolucao)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="evolucoes_clinicas",
        registro_id=nova_evolucao.id,
        antes=None,
        depois=nova_evolucao.to_dict(),
    )

    return jsonify(nova_evolucao.to_dict()), 201


# ---------------------------------------------------------------------------
# Odontograma (RF06)
# ---------------------------------------------------------------------------


@clinico_bp.get("/odontograma/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_LEITURA_CLINICA)
def obter_odontograma(paciente_id):
    if not _paciente_existe(paciente_id):
        return jsonify({"erro": f"Paciente com id {paciente_id} nao encontrado."}), 404

    registrar_leitura(_identidade_do_ator(), "odontograma", registro_id=paciente_id)
    return jsonify(_montar_grade_odontograma(paciente_id)), 200


def _validar_alteracao_odontograma(item, indice):
    """Valida um item de alteracao do odontograma. Retorna (dados, erros)."""
    erros = []
    if not isinstance(item, dict):
        return None, [f"Item {indice}: deve ser um objeto JSON."]

    dente_fdi = item.get("dente_fdi")
    if isinstance(dente_fdi, bool) or not isinstance(dente_fdi, int):
        erros.append(f"Item {indice}: campo 'dente_fdi' e obrigatorio e deve ser inteiro.")
    elif dente_fdi not in DENTES_VALIDOS:
        erros.append(f"Item {indice}: dente_fdi {dente_fdi} nao e um codigo FDI valido.")

    face = item.get("face")
    if not isinstance(face, str) or face not in FACES_VALIDAS:
        erros.append(
            f"Item {indice}: campo 'face' e obrigatorio e deve ser um de {FACES_VALIDAS}."
        )

    situacao = item.get("situacao")
    if not situacao or not isinstance(situacao, str) or not situacao.strip():
        erros.append(f"Item {indice}: campo 'situacao' e obrigatorio e deve ser texto nao vazio.")
    elif len(situacao.strip()) > TAMANHO_MAXIMO_SITUACAO:
        erros.append(
            f"Item {indice}: campo 'situacao' deve ter no maximo "
            f"{TAMANHO_MAXIMO_SITUACAO} caracteres."
        )

    profissional_id = None
    try:
        profissional_id = _profissional_do_ator(item.get("profissional_id"))
    except ErroProfissional as exc:
        if exc.status == 403:
            raise
        erros.append(f"Item {indice}: {exc.mensagem}")

    if erros:
        return None, erros

    return (
        {
            "dente_fdi": dente_fdi,
            "face": face,
            "situacao": situacao.strip(),
            "profissional_id": profissional_id,
        },
        [],
    )


@clinico_bp.put("/odontograma/<int:paciente_id>")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CLINICA)
def atualizar_odontograma(paciente_id):
    if not _paciente_existe(paciente_id):
        return jsonify({"erro": f"Paciente com id {paciente_id} nao encontrado."}), 404

    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    if isinstance(payload.get("alteracoes"), list):
        itens_brutos = payload["alteracoes"]
    elif "dente_fdi" in payload:
        itens_brutos = [payload]
    else:
        return (
            jsonify(
                {
                    "erro": "Informe 'dente_fdi'/'face'/'situacao'/'profissional_id' "
                    "no corpo, ou uma lista em 'alteracoes'."
                }
            ),
            400,
        )

    if not itens_brutos:
        return jsonify({"erro": "Nenhuma alteracao informada."}), 400

    itens_validados = []
    todos_erros = []
    for indice, item in enumerate(itens_brutos):
        try:
            dados, erros = _validar_alteracao_odontograma(item, indice)
        except ErroProfissional as exc:
            return jsonify({"erro": exc.mensagem}), exc.status
        if erros:
            todos_erros.extend(erros)
        else:
            itens_validados.append(dados)

    if todos_erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": todos_erros}), 400

    ator_id = _identidade_do_ator()
    auditorias_pendentes = []

    for item in itens_validados:
        registro_existente = Odontograma.query.filter_by(
            paciente_id=paciente_id, dente_fdi=item["dente_fdi"], face=item["face"]
        ).first()

        if registro_existente is not None:
            # Grava o valor anterior no historico ANTES de sobrescrever.
            historico = OdontogramaHistorico(
                odontograma_id=registro_existente.id,
                situacao_anterior=registro_existente.situacao,
            )
            db.session.add(historico)

            estado_antes = registro_existente.to_dict()
            registro_existente.situacao = item["situacao"]
            registro_existente.profissional_id = item["profissional_id"]
            registro_existente.registrado_em = datetime.utcnow()
            db.session.flush()

            auditorias_pendentes.append(
                {
                    "acao": "atualizar",
                    "registro_id": registro_existente.id,
                    "antes": estado_antes,
                    "depois": registro_existente.to_dict(),
                }
            )
        else:
            novo_registro = Odontograma(
                paciente_id=paciente_id,
                dente_fdi=item["dente_fdi"],
                face=item["face"],
                situacao=item["situacao"],
                profissional_id=item["profissional_id"],
            )
            db.session.add(novo_registro)
            db.session.flush()

            auditorias_pendentes.append(
                {
                    "acao": "criar",
                    "registro_id": novo_registro.id,
                    "antes": None,
                    "depois": novo_registro.to_dict(),
                }
            )

    db.session.commit()

    for auditoria in auditorias_pendentes:
        registrar_auditoria(
            usuario_id=ator_id,
            acao=auditoria["acao"],
            tabela="odontograma",
            registro_id=auditoria["registro_id"],
            antes=auditoria["antes"],
            depois=auditoria["depois"],
        )

    return jsonify(_montar_grade_odontograma(paciente_id)), 200


# ---------------------------------------------------------------------------
# Exames e anexos (RF05)
# ---------------------------------------------------------------------------


def _extensao_do_arquivo(nome_arquivo: str) -> str:
    if "." not in nome_arquivo:
        return ""
    return nome_arquivo.rsplit(".", 1)[-1].lower()


def _assinatura_valida(stream, extensao: str) -> bool:
    """Confere os bytes iniciais do arquivo contra a assinatura esperada da
    extensao, como camada extra de defesa contra arquivos disfarcados."""
    assinaturas = _ASSINATURAS_ARQUIVO.get(extensao)
    if not assinaturas:
        return True
    stream.seek(0)
    cabecalho = stream.read(16)
    stream.seek(0)
    return any(cabecalho.startswith(assinatura) for assinatura in assinaturas)


@clinico_bp.post("/exames")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_EXAMES)
def enviar_exame():
    paciente_id_bruto = request.form.get("paciente_id")
    tipo = request.form.get("tipo")

    erros = []

    try:
        paciente_id = int(paciente_id_bruto)
        if paciente_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        paciente_id = None
        erros.append("Campo 'paciente_id' e obrigatorio e deve ser um numero inteiro positivo.")

    if paciente_id is not None and not _paciente_existe(paciente_id):
        erros.append(f"Paciente com id {paciente_id} nao encontrado.")

    if not tipo or not isinstance(tipo, str) or not tipo.strip():
        erros.append("Campo 'tipo' e obrigatorio (ex.: 'radiografia', 'foto', 'laudo').")

    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        erros.append("Arquivo 'arquivo' e obrigatorio.")
    else:
        nome_seguro = secure_filename(arquivo.filename)
        extensao = _extensao_do_arquivo(nome_seguro)
        if extensao not in EXTENSOES_PERMITIDAS_EXAME:
            erros.append(
                "Extensao de arquivo nao permitida. "
                f"Extensoes aceitas: {sorted(EXTENSOES_PERMITIDAS_EXAME)}."
            )
        else:
            arquivo.stream.seek(0, os.SEEK_END)
            tamanho_bytes = arquivo.stream.tell()
            arquivo.stream.seek(0)

            if tamanho_bytes <= 0:
                erros.append("Arquivo vazio nao e permitido.")
            elif tamanho_bytes > TAMANHO_MAXIMO_EXAME_BYTES:
                erros.append(
                    f"Arquivo excede o tamanho maximo permitido de "
                    f"{TAMANHO_MAXIMO_EXAME_BYTES // (1024 * 1024)}MB."
                )
            elif not _assinatura_valida(arquivo.stream, extensao):
                erros.append(
                    "Conteudo do arquivo nao corresponde a extensao informada."
                )

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    extensao = _extensao_do_arquivo(secure_filename(arquivo.filename))
    nome_no_disco = f"{uuid.uuid4().hex}.{extensao}"

    pasta_upload = current_app.config.get(
        "UPLOAD_FOLDER_EXAMES",
        os.path.join(current_app.root_path, "..", "uploads", "exames"),
    )
    pasta_upload = os.path.abspath(pasta_upload)
    os.makedirs(pasta_upload, exist_ok=True)

    caminho_completo = os.path.join(pasta_upload, nome_no_disco)
    # Nunca executamos o conteudo do arquivo -- apenas gravamos os bytes em
    # disco, com nome gerado (uuid) e extensao restrita a lista branca.
    arquivo.save(caminho_completo)

    novo_exame = ExameAnexo(
        paciente_id=paciente_id,
        tipo=tipo.strip(),
        arquivo_url=f"/uploads/exames/{nome_no_disco}",
    )
    db.session.add(novo_exame)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="exames_anexos",
        registro_id=novo_exame.id,
        antes=None,
        depois=novo_exame.to_dict(),
    )

    return jsonify(novo_exame.to_dict()), 201


# ---------------------------------------------------------------------------
# Receitas e atestados (RF07)
# ---------------------------------------------------------------------------


@clinico_bp.post("/receitas")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CLINICA)
def criar_receita():
    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    erros = []

    prontuario_id, erro = _validar_inteiro_positivo(
        payload.get("prontuario_id"), "prontuario_id"
    )
    if erro:
        erros.append(erro)

    texto = payload.get("texto")
    if not texto or not isinstance(texto, str) or not texto.strip():
        erros.append("Campo 'texto' e obrigatorio e deve ser texto nao vazio.")

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    prontuario = Prontuario.query.get(prontuario_id)
    if prontuario is None:
        return jsonify({"erro": f"Prontuario com id {prontuario_id} nao encontrado."}), 404

    nova_receita = Receita(prontuario_id=prontuario.id, texto=texto.strip())
    db.session.add(nova_receita)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="receitas",
        registro_id=nova_receita.id,
        antes=None,
        depois=nova_receita.to_dict(),
    )

    return jsonify(nova_receita.to_dict()), 201


@clinico_bp.post("/atestados")
@jwt_required()
@require_perfil(PERFIS_ESCRITA_CLINICA)
def criar_atestado():
    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"erro": "Corpo da requisicao deve ser um JSON valido."}), 400

    erros = []

    prontuario_id, erro = _validar_inteiro_positivo(
        payload.get("prontuario_id"), "prontuario_id"
    )
    if erro:
        erros.append(erro)

    texto = payload.get("texto")
    if not texto or not isinstance(texto, str) or not texto.strip():
        erros.append("Campo 'texto' e obrigatorio e deve ser texto nao vazio.")

    dias_afastamento = payload.get("dias_afastamento", 0)
    if isinstance(dias_afastamento, bool) or not isinstance(dias_afastamento, int):
        erros.append("Campo 'dias_afastamento' deve ser um numero inteiro.")
    elif dias_afastamento < 0:
        erros.append("Campo 'dias_afastamento' nao pode ser negativo.")

    if erros:
        return jsonify({"erro": "Dados invalidos.", "detalhes": erros}), 400

    prontuario = Prontuario.query.get(prontuario_id)
    if prontuario is None:
        return jsonify({"erro": f"Prontuario com id {prontuario_id} nao encontrado."}), 404

    novo_atestado = Atestado(
        prontuario_id=prontuario.id,
        texto=texto.strip(),
        dias_afastamento=dias_afastamento,
    )
    db.session.add(novo_atestado)
    db.session.commit()

    registrar_auditoria(
        usuario_id=_identidade_do_ator(),
        acao="criar",
        tabela="atestados",
        registro_id=novo_atestado.id,
        antes=None,
        depois=novo_atestado.to_dict(),
    )

    return jsonify(novo_atestado.to_dict()), 201
