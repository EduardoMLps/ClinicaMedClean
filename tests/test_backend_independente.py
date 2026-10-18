"""Testes independentes de ataque ao backend (02/10/2026). Rodar: cd backend; python -m pytest ../tests/test_backend_independente.py -q"""
import sys, os, re, base64, json
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(D,"tests"))
from test_backend_seguranca import app, client, login, auth, SENHA  # reaproveita só o banco de teste
import pytest

def test_alg_none_recusado(client):
    h=base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b'=').decode()
    p=base64.urlsafe_b64encode(json.dumps({"sub":"1","perfil":"administrador","type":"access","jti":"z","exp":9999999999}).encode()).rstrip(b'=').decode()
    assert client.get("/api/v1/usuarios", headers=auth(f"{h}.{p}.")).status_code==401

def test_sem_token_401(client):
    for u in ["/api/v1/pacientes","/api/v1/usuarios","/api/v1/prontuarios/1","/api/v1/relatorios/financeiro"]:
        assert client.get(u).status_code in (401,404), u

def test_refresh_nao_serve_como_access(client):
    t=login(client,"admin@t.local")
    assert client.get("/api/v1/usuarios", headers=auth(t["refresh_token"])).status_code in (401,422)

@pytest.mark.parametrize("email",["rita@t.local","fabio@t.local","ana@t.local"])
def test_nao_admin_nao_gerencia_usuarios(client,email):
    t=login(client,email)["access_token"]
    assert client.get("/api/v1/usuarios", headers=auth(t)).status_code==403
    assert client.post("/api/v1/usuarios", headers=auth(t), json={"nome":"X","email":"x@t.local","senha":"Clinica#Forte2026","perfil_nome":"administrador"}).status_code==403
    assert client.put("/api/v1/usuarios/1", headers=auth(t), json={"ativo":False}).status_code==403

def test_financeiro_sem_prontuario(client):
    t=login(client,"fabio@t.local")["access_token"]
    assert client.get("/api/v1/prontuarios/1", headers=auth(t)).status_code==403
    assert client.get("/api/v1/odontograma/1", headers=auth(t)).status_code==403

def test_usuario_desativado_nao_loga(client):
    adm=login(client,"admin@t.local")["access_token"]
    client.delete("/api/v1/usuarios/5", headers=auth(adm))
    r=client.post("/api/v1/auth/login", json={"email":"fabio@t.local","senha":SENHA})
    assert r.status_code in (401,403) and "access_token" not in (r.get_json() or {})

@pytest.mark.parametrize("q",["' OR '1'='1","%' OR 1=1 --","\"; DROP TABLE pacientes; --","%","_"])
def test_injecao_sql_na_busca(client,q):
    t=login(client,"rita@t.local")["access_token"]
    r=client.get("/api/v1/pacientes", headers=auth(t), query_string={"q":q})
    assert r.status_code==200 and r.get_json()["dados"]==[]
    assert len(client.get("/api/v1/pacientes", headers=auth(t)).get_json()["dados"])==1

def test_xss_guardado_como_texto_e_json(client):
    t=login(client,"admin@t.local")["access_token"]
    r=client.put("/api/v1/usuarios/4", headers=auth(t), json={"nome":"<script>alert(1)</script>"})
    assert r.status_code in (200,400)
    r=client.get("/api/v1/usuarios", headers=auth(t))
    assert r.mimetype=="application/json"
    assert r.headers.get("X-Content-Type-Options")=="nosniff"

def test_forca_bruta_varios_emails(client):
    cods=[client.post("/api/v1/auth/login", json={"email":f"n{i}@t.local","senha":"errada"}).status_code for i in range(30)]
    assert 429 in cods, cods

def test_respostas_de_erro_sem_detalhe_interno(client):
    t=login(client,"admin@t.local")["access_token"]
    r=client.post("/api/v1/pacientes", headers=auth(t), data="{lixo", content_type="application/json")
    corpo=r.get_data(as_text=True)
    assert r.status_code<500 and "Traceback" not in corpo and "sqlalchemy" not in corpo.lower()

def test_compose_sem_portas_e_sem_seed():
    c=open(os.path.join(D,"docker-compose.yml")).read()
    assert not re.search(r'["\']?\d*:?3306:3306', c), "porta MySQL publicada"
    assert not re.search(r'["\']?\d*:?5000:5000', c), "porta API publicada"
    ativas=[l for l in c.splitlines() if "seed_demo" in l and not l.strip().startswith("#")]
    assert not ativas, ativas
