"""
Testes automatizados das correcoes de seguranca do backend (versao 4.0.1).

Rodam com SQLite em memoria, sem MySQL/nginx:
    cd backend
    pip install -r requirements.txt pytest
    python -m pytest ../tests/test_backend_seguranca.py -q
"""

import os
import secrets
import sys
from datetime import date

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

SENHA = "Clinica#Forte2026"


class ConfigTeste:
    TESTING = True
    SECRET_KEY = secrets.token_urlsafe(48)
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_TOKEN_LOCATION = ["headers"]
    CORS_ORIGINS = ["http://localhost:5173"]
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_ENABLED = True
    TRUSTED_PROXY_COUNT = 0
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    AUDIT_LOG_RETENCAO_DIAS = 30
    ENV = "testing"


@pytest.fixture()
def app():
    from app import create_app
    from app.extensions import db, limiter
    from app.models.auth import Perfil, Usuario
    from app.models.pacientes import Endereco, Especialidade, Paciente, Profissional
    from app.utils.security import hash_senha

    aplicacao = create_app(ConfigTeste)
    with aplicacao.app_context():
        limiter.reset()
        db.create_all()
        perfis = {}
        for i, nome in enumerate(["administrador", "dentista", "recepcao", "financeiro"], 1):
            perfis[nome] = Perfil(id=i, nome=nome)
            db.session.add(perfis[nome])
        db.session.add(Especialidade(id=1, nome="Clinica geral"))
        db.session.add(Profissional(id=1, nome="Dra. Ana", especialidade_id=1, registro_conselho="CRO-1"))
        db.session.add(Profissional(id=2, nome="Dr. Beto", especialidade_id=1, registro_conselho="CRO-2"))
        db.session.flush()
        hash_ = hash_senha(SENHA)
        usuarios = [
            (1, "Admin", "admin@t.local", "administrador", None),
            (2, "Ana Dentista", "ana@t.local", "dentista", 1),
            (3, "Sem Vinculo", "semvinc@t.local", "dentista", None),
            (4, "Rita Recepcao", "rita@t.local", "recepcao", None),
            (5, "Fabio Financeiro", "fabio@t.local", "financeiro", None),
        ]
        for uid, nome, email, perfil, prof in usuarios:
            db.session.add(Usuario(id=uid, nome=nome, email=email, senha_hash=hash_,
                                   perfil_id=perfis[perfil].id, ativo=True, profissional_id=prof))
        db.session.add(Paciente(id=1, nome="Paciente Um", cpf="12345678901",
                                data_nascimento=date(1990, 5, 1), telefone="11999990000"))
        db.session.add(Endereco(id=1, paciente_id=1, logradouro="Rua A, 1", cidade="Sao Paulo",
                                uf="SP", cep="01000-000"))
        db.session.commit()
        yield aplicacao
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, senha=SENHA):
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------- B2
@pytest.mark.parametrize("segredo", ["TROCAR_ESTE_VALOR", "curto", "a" * 50,
                                     "change-me-please-change-me-please-123456"])
def test_b2_recusa_segredo_fraco(segredo):
    from app import create_app

    class Fraca(ConfigTeste):
        JWT_SECRET_KEY = segredo

    with pytest.raises(RuntimeError, match="Segredos inseguros"):
        create_app(Fraca)


def test_b2_recusa_segredos_iguais():
    from app import create_app

    igual = secrets.token_urlsafe(48)

    class Igual(ConfigTeste):
        SECRET_KEY = igual
        JWT_SECRET_KEY = igual

    with pytest.raises(RuntimeError, match="diferentes"):
        create_app(Igual)


# --------------------------------------------------------------------- B3
def test_b3_logout_revoga_access_e_refresh(client):
    t = login(client, "admin@t.local")
    assert client.get("/api/v1/auth/me", headers=auth(t["access_token"])).status_code == 200
    r = client.post("/api/v1/auth/logout", headers=auth(t["access_token"]),
                    json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(t["access_token"])).status_code == 401
    assert client.post("/api/v1/auth/refresh", headers=auth(t["refresh_token"])).status_code == 401


def test_b3_usuario_desativado_perde_acesso_na_hora(client):
    adm = login(client, "admin@t.local")["access_token"]
    rita = login(client, "rita@t.local")["access_token"]
    assert client.get("/api/v1/pacientes", headers=auth(rita)).status_code == 200
    assert client.delete("/api/v1/usuarios/4", headers=auth(adm)).status_code == 200
    assert client.get("/api/v1/pacientes", headers=auth(rita)).status_code == 401


def test_b3_troca_de_perfil_invalida_token_antigo(client):
    adm = login(client, "admin@t.local")["access_token"]
    fabio = login(client, "fabio@t.local")["access_token"]
    r = client.put("/api/v1/usuarios/5", headers=auth(adm), json={"perfil_nome": "recepcao"})
    assert r.status_code == 200
    assert client.get("/api/v1/pacientes", headers=auth(fabio)).status_code == 401


def test_b3_troca_de_senha_encerra_sessoes(client):
    t = login(client, "rita@t.local")["access_token"]
    r = client.post("/api/v1/auth/alterar-senha", headers=auth(t),
                    json={"senha_atual": SENHA, "nova_senha": "Agenda#Nova2026x"})
    assert r.status_code == 200, r.get_json()
    assert client.get("/api/v1/auth/me", headers=auth(t)).status_code == 401
    login(client, "rita@t.local", "Agenda#Nova2026x")


def test_b3_token_forjado_com_outro_segredo_recusado(client):
    import jwt as pyjwt

    falso = pyjwt.encode({"sub": "1", "perfil": "administrador", "type": "access",
                          "jti": "x", "fresh": False, "iat": 0, "nbf": 0, "exp": 9999999999},
                         "TROCAR_ESTE_VALOR", algorithm="HS256")
    assert client.get("/api/v1/usuarios", headers=auth(falso)).status_code == 401


# --------------------------------------------------------------- B4 + B5
def test_b4_dentista_ve_cpf_mascarado_e_sem_endereco(client):
    t = login(client, "ana@t.local")["access_token"]
    lista = client.get("/api/v1/pacientes", headers=auth(t)).get_json()["dados"]
    assert lista[0]["cpf"] == "***.456.789-**"
    ficha = client.get("/api/v1/pacientes/1", headers=auth(t)).get_json()
    assert ficha["cpf"] == "***.456.789-**"
    assert "enderecos" not in ficha
    assert client.get("/api/v1/pacientes/1/enderecos", headers=auth(t)).status_code == 403


@pytest.mark.parametrize("email", ["admin@t.local", "rita@t.local", "fabio@t.local"])
def test_b4_perfis_autorizados_veem_cpf_completo(client, email):
    t = login(client, email)["access_token"]
    ficha = client.get("/api/v1/pacientes/1", headers=auth(t)).get_json()
    assert ficha["cpf"] == "12345678901"
    assert ficha["enderecos"][0]["cidade"] == "Sao Paulo"


def test_b5_leitura_de_prontuario_e_ficha_fica_auditada(client, app):
    from app.models.auth import LogAuditoria

    t = login(client, "ana@t.local")["access_token"]
    assert client.get("/api/v1/prontuarios/1", headers=auth(t)).status_code == 200
    assert client.get("/api/v1/odontograma/1", headers=auth(t)).status_code == 200
    assert client.get("/api/v1/pacientes/1", headers=auth(t)).status_code == 200
    with app.app_context():
        leituras = {(l.tabela, l.usuario_id) for l in LogAuditoria.query.filter_by(acao="ler")}
    assert {("prontuarios", 2), ("odontograma", 2), ("pacientes", 2)} <= leituras


def test_b5_recepcao_continua_sem_acesso_ao_prontuario(client):
    t = login(client, "rita@t.local")["access_token"]
    assert client.get("/api/v1/prontuarios/1", headers=auth(t)).status_code == 403


# --------------------------------------------------------------------- B9
def _criar_prontuario(client, token, **extra):
    return client.post("/api/v1/prontuarios/1", headers=auth(token), json=extra)


def test_b9_evolucao_sai_em_nome_do_dentista_logado(client):
    t = login(client, "ana@t.local")["access_token"]
    pront = _criar_prontuario(client, t).get_json()
    assert pront["profissional_id"] == 1
    r = client.post(f"/api/v1/prontuarios/{pront['id']}/evolucoes", headers=auth(t),
                    json={"texto": "Restauracao 36"})
    assert r.status_code == 201 and r.get_json()["profissional_id"] == 1


def test_b9_dentista_nao_registra_em_nome_de_outro(client):
    t = login(client, "ana@t.local")["access_token"]
    pront = _criar_prontuario(client, t).get_json()
    r = client.post(f"/api/v1/prontuarios/{pront['id']}/evolucoes", headers=auth(t),
                    json={"texto": "x", "profissional_id": 2})
    assert r.status_code == 403
    r = client.put("/api/v1/odontograma/1", headers=auth(t),
                   json={"dente_fdi": 11, "face": "V", "situacao": "carie", "profissional_id": 2})
    assert r.status_code == 403


def test_b9_dentista_sem_vinculo_e_bloqueado(client):
    t = login(client, "semvinc@t.local")["access_token"]
    assert _criar_prontuario(client, t, profissional_id=1).status_code == 403


def test_b9_admin_pode_registrar_informando_profissional(client):
    t = login(client, "admin@t.local")["access_token"]
    r = _criar_prontuario(client, t, profissional_id=2)
    assert r.status_code == 201 and r.get_json()["profissional_id"] == 2


def test_b9_admin_vincula_usuario_a_profissional(client):
    t = login(client, "admin@t.local")["access_token"]
    r = client.put("/api/v1/usuarios/3", headers=auth(t), json={"profissional_id": 2})
    assert r.status_code == 200 and r.get_json()["profissional_id"] == 2


# --------------------------------------------------------------------- B6
def test_b6_limite_de_login(client):
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "admin@t.local", "senha": "errada"})
    r = client.post("/api/v1/auth/login", json={"email": "admin@t.local", "senha": "errada"})
    assert r.status_code == 429


def test_b6_proxyfix_usa_ip_real_quando_configurado():
    from app import create_app

    class ComProxy(ConfigTeste):
        TRUSTED_PROXY_COUNT = 1

    app = create_app(ComProxy)

    @app.get("/_ip")
    def _ip():
        from flask import request
        return request.remote_addr

    c = app.test_client()
    assert c.get("/_ip", headers={"X-Forwarded-For": "200.1.2.3"}).text == "200.1.2.3"


def test_b6_sem_proxy_ignora_cabecalho_forjado():
    from app import create_app

    app = create_app(ConfigTeste)

    @app.get("/_ip")
    def _ip():
        from flask import request
        return request.remote_addr

    c = app.test_client()
    assert c.get("/_ip", headers={"X-Forwarded-For": "200.1.2.3"}).text != "200.1.2.3"


# ----------------------------------------------------------- B10 a B14
def test_b10_requisicao_grande_recusada(client):
    t = login(client, "admin@t.local")["access_token"]
    r = client.post("/api/v1/pacientes", headers=auth(t),
                    data=b"x" * (2 * 1024 * 1024), content_type="application/json")
    assert r.status_code == 413


def test_b11_login_mesma_resposta_para_email_inexistente(client):
    a = client.post("/api/v1/auth/login", json={"email": "naoexiste@t.local", "senha": "x"})
    b = client.post("/api/v1/auth/login", json={"email": "rita@t.local", "senha": "x"})
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json()


@pytest.mark.parametrize("senha", ["curta1", "semnumeroaqui", "1234567890", "Rita12345678"])
def test_b12_politica_de_senha(client, senha):
    t = login(client, "admin@t.local")["access_token"]
    r = client.post("/api/v1/usuarios", headers=auth(t), json={
        "nome": "Rita Nova", "email": "rita.nova@t.local", "senha": senha, "perfil_nome": "recepcao"})
    assert r.status_code == 400


def test_b12_senha_boa_aceita(client):
    t = login(client, "admin@t.local")["access_token"]
    r = client.post("/api/v1/usuarios", headers=auth(t), json={
        "nome": "Nova Pessoa", "email": "nova@t.local", "senha": "Sorriso#Bonito42",
        "perfil_nome": "recepcao"})
    assert r.status_code == 201, r.get_json()


def test_b13_log_de_auditoria_guarda_cpf_mascarado(client, app):
    from app.models.auth import LogAuditoria

    t = login(client, "rita@t.local")["access_token"]
    r = client.put("/api/v1/pacientes/1", headers=auth(t), json={"cpf": "98765432100"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["cpf"] == "98765432100"  # a recepcao ve o CPF completo
    with app.app_context():
        log = LogAuditoria.query.filter_by(tabela="pacientes", acao="atualizar").first()
        assert log.dados_antes["cpf"] == "***.456.789-**"
        assert log.dados_depois["cpf"] == "***.654.321-**"


def test_b13_limpeza_de_logs_antigos(app):
    from datetime import datetime, timedelta

    from app.extensions import db
    from app.models.auth import LogAuditoria
    from app.utils.security import limpar_logs_auditoria_antigos

    with app.app_context():
        db.session.add(LogAuditoria(acao="ler", tabela="x", criado_em=datetime.utcnow() - timedelta(days=40)))
        db.session.add(LogAuditoria(acao="ler", tabela="y"))
        db.session.commit()
        assert limpar_logs_auditoria_antigos(30) == 1
        assert LogAuditoria.query.filter_by(tabela="y").count() == 1


def test_b14_busca_trata_curinga_como_texto(client):
    t = login(client, "rita@t.local")["access_token"]
    assert client.get("/api/v1/pacientes?q=%25", headers=auth(t)).get_json()["total"] == 0
    assert client.get("/api/v1/pacientes?q=Um", headers=auth(t)).get_json()["total"] == 1


def test_b14_cors_sem_credenciais_e_so_origem_permitida(client):
    r = client.options("/api/v1/pacientes", headers={
        "Origin": "https://site-malicioso.com", "Access-Control-Request-Method": "GET"})
    assert "Access-Control-Allow-Origin" not in r.headers
    r = client.options("/api/v1/pacientes", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert r.headers.get("Access-Control-Allow-Credentials") is None


def test_b7_cabecalhos_de_seguranca_na_api(client):
    r = client.get("/api/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Frame-Options"] == "DENY"


# ------------------------------------------------- regressao basica
def test_fluxo_normal_continua_funcionando(client):
    t = login(client, "rita@t.local")["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth(t)).status_code == 200
    assert client.get("/api/v1/pacientes", headers=auth(t)).status_code == 200
    r = client.post("/api/v1/auth/refresh", headers=auth(login(client, "rita@t.local")["refresh_token"]))
    assert r.status_code == 200


@pytest.mark.parametrize("email", ["admin@t.local", "ana@t.local", "rita@t.local", "fabio@t.local"])
def test_nenhuma_rota_get_da_erro_500(app, client, email):
    tok = login(client, email)["access_token"]
    falhas = []
    for regra in app.url_map.iter_rules():
        if "GET" not in regra.methods or not regra.rule.startswith("/api"):
            continue
        url = regra.rule
        for arg in regra.arguments:
            url = url.replace(f"<int:{arg}>", "1").replace(f"<{arg}>", "1")
        r = client.get(url, headers=auth(tok))
        if r.status_code >= 500:
            falhas.append((url, r.status_code))
    assert falhas == []
