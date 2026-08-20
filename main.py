"""Nota Mil — API + servidor do front.

Rodar:  uvicorn main:app --reload
Docs:   http://localhost:8000/api/docs
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ia
import seed_questoes
from db import agora, conectar, consultar, consultar_um, executar, init_db
from security import (
    conferir_senha,
    criar_sessao,
    encerrar_sessao,
    hash_senha,
    limpar_sessoes_expiradas,
    usuario_da_sessao,
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title="Nota Mil API",
    description="Backend da plataforma de estudos com IA para ENEM e vestibulares.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.on_event("startup")
def iniciar() -> None:
    init_db()
    criadas = seed_questoes.semear()
    limpar_sessoes_expiradas()
    if criadas:
        print(f"[nota-mil] banco inicial com {criadas} questões")
    print(f"[nota-mil] IA: {ia.provedor() or 'desativada (sem chave de API)'}")


# ──────────────────────────────────────────────────────────────────────────────
# MODELOS
# ──────────────────────────────────────────────────────────────────────────────

class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    email: str
    senha: str = Field(min_length=6, max_length=128)


class Login(BaseModel):
    email: str
    senha: str


class RedacaoEntrada(BaseModel):
    tema: str = Field(min_length=5, max_length=300)
    texto: str = Field(min_length=200, max_length=20000)


class RespostaEntrada(BaseModel):
    resposta: str = Field(pattern="^[A-Ea-e]$")
    segundos: int = 0


class GerarQuestoes(BaseModel):
    disciplina: str = Field(min_length=2, max_length=60)
    topico: str = Field(min_length=3, max_length=200)
    quantidade: int = Field(default=3, ge=1, le=5)


# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def usuario_atual(authorization: str | None = Header(default=None)) -> dict:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = usuario_da_sessao(token)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre novamente.")
    return user


RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


@app.post("/api/auth/cadastro", status_code=201)
async def cadastrar(dados: Cadastro):
    email = dados.email.strip().lower()
    if not RE_EMAIL.match(email):
        raise HTTPException(422, "E-mail inválido.")
    if consultar_um("SELECT id FROM usuarios WHERE email=?", (email,)):
        raise HTTPException(409, "Esse e-mail já está cadastrado.")

    h, salt = await run_in_threadpool(hash_senha, dados.senha)
    uid = executar(
        "INSERT INTO usuarios(nome,email,senha_hash,salt,criado_em) VALUES(?,?,?,?,?)",
        (dados.nome.strip(), email, h, salt, agora()),
    )
    token = criar_sessao(uid)
    return {"token": token, "usuario": {"id": uid, "nome": dados.nome.strip(), "email": email}}


@app.post("/api/auth/login")
async def login(dados: Login):
    row = consultar_um("SELECT * FROM usuarios WHERE email=?", (dados.email.strip().lower(),))
    ok = row and await run_in_threadpool(
        conferir_senha, dados.senha, row["senha_hash"], row["salt"]
    )
    if not ok:
        raise HTTPException(401, "E-mail ou senha incorretos.")
    token = criar_sessao(row["id"])
    return {
        "token": token,
        "usuario": {"id": row["id"], "nome": row["nome"], "email": row["email"]},
    }


@app.get("/api/auth/eu")
def eu(user: dict = Depends(usuario_atual)):
    return {"usuario": user, "ia_ativa": ia.disponivel()}


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        encerrar_sessao(authorization[7:].strip())
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# REDAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/redacoes")
async def corrigir(dados: RedacaoEntrada, user: dict = Depends(usuario_atual)):
    if not ia.disponivel():
        raise HTTPException(503, "Correção por IA indisponível: nenhuma chave de API configurada.")
    if len(dados.texto.split()) < 50:
        raise HTTPException(422, "A redação precisa ter pelo menos 50 palavras.")

    try:
        r = await run_in_threadpool(ia.corrigir_redacao, dados.tema.strip(), dados.texto.strip())
    except ValueError as e:
        raise HTTPException(502, f"A IA devolveu uma resposta inesperada: {e}")
    except Exception as e:
        raise HTTPException(502, f"Falha ao consultar a IA: {e}")

    rid = executar(
        """INSERT INTO redacoes
           (usuario_id,tema,texto,nota_final,c1,c2,c3,c4,c5,feedback_json,criado_em)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], dados.tema.strip(), dados.texto.strip(), r["nota_final"],
         r["notas"][1], r["notas"][2], r["notas"][3], r["notas"][4], r["notas"][5],
         json.dumps(r, ensure_ascii=False), agora()),
    )
    r["id"] = rid
    r["tema"] = dados.tema.strip()
    r["criado_em"] = agora()
    return r


@app.get("/api/redacoes")
def listar_redacoes(user: dict = Depends(usuario_atual)):
    rows = consultar(
        """SELECT id,tema,nota_final,c1,c2,c3,c4,c5,criado_em,
                  length(texto) AS tamanho
             FROM redacoes WHERE usuario_id=? ORDER BY id DESC""",
        (user["id"],),
    )
    return [dict(r) for r in rows]


@app.get("/api/redacoes/{rid}")
def detalhe_redacao(rid: int, user: dict = Depends(usuario_atual)):
    row = consultar_um(
        "SELECT * FROM redacoes WHERE id=? AND usuario_id=?", (rid, user["id"])
    )
    if not row:
        raise HTTPException(404, "Redação não encontrada.")
    dados = json.loads(row["feedback_json"])
    dados.update({
        "id": row["id"], "tema": row["tema"], "texto": row["texto"],
        "criado_em": row["criado_em"], "nota_final": row["nota_final"],
    })
    return dados


@app.delete("/api/redacoes/{rid}")
def apagar_redacao(rid: int, user: dict = Depends(usuario_atual)):
    with conectar() as c:
        cur = c.execute("DELETE FROM redacoes WHERE id=? AND usuario_id=?", (rid, user["id"]))
        if cur.rowcount == 0:
            raise HTTPException(404, "Redação não encontrada.")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# QUESTÕES
# ──────────────────────────────────────────────────────────────────────────────

def _serializar_questao(r, revelar_gabarito: bool = False) -> dict:
    q = {
        "id": r["id"],
        "numero": r["numero"],
        "ano": r["ano"],
        "prova": r["prova"],
        "disciplina": r["disciplina"] or "Geral",
        "enunciado": r["enunciado"],
        "alternativas": [
            {"letra": L, "texto": r["alt_" + L.lower()]}
            for L in "ABCDE"
            if r["alt_" + L.lower()]
        ],
    }
    if revelar_gabarito:
        q["gabarito"] = r["gabarito"]
    return q


@app.get("/api/questoes/filtros")
def filtros(user: dict = Depends(usuario_atual)):
    disc = [r[0] for r in consultar(
        "SELECT DISTINCT disciplina FROM questoes WHERE disciplina IS NOT NULL ORDER BY disciplina"
    )]
    anos = [r[0] for r in consultar(
        "SELECT DISTINCT ano FROM questoes WHERE ano IS NOT NULL ORDER BY ano DESC"
    )]
    total = consultar_um("SELECT COUNT(*) t FROM questoes")["t"]
    return {"disciplinas": disc, "anos": anos, "total": total}


@app.get("/api/questoes")
def listar_questoes(
    user: dict = Depends(usuario_atual),
    disciplina: str | None = None,
    ano: int | None = None,
    nao_respondidas: bool = False,
    limite: int = Query(default=40, le=200),
):
    sql = "SELECT * FROM questoes WHERE 1=1"
    par: list = []
    if disciplina and disciplina != "Todas":
        sql += " AND disciplina=?"
        par.append(disciplina)
    if ano:
        sql += " AND ano=?"
        par.append(ano)
    if nao_respondidas:
        sql += " AND id NOT IN (SELECT questao_id FROM respostas WHERE usuario_id=?)"
        par.append(user["id"])
    sql += " ORDER BY disciplina, numero, id LIMIT ?"
    par.append(limite)

    rows = consultar(sql, tuple(par))
    respondidas = {
        r["questao_id"]: {"resposta": r["resposta"], "acertou": bool(r["acertou"])}
        for r in consultar(
            """SELECT questao_id, resposta, acertou FROM respostas
                WHERE usuario_id=? AND id IN
                      (SELECT MAX(id) FROM respostas WHERE usuario_id=? GROUP BY questao_id)""",
            (user["id"], user["id"]),
        )
    }

    saida = []
    for r in rows:
        q = _serializar_questao(r)
        q["ja_respondida"] = r["id"] in respondidas
        saida.append(q)
    return {"questoes": saida, "total": len(saida)}


@app.post("/api/questoes/{qid}/responder")
def responder(qid: int, dados: RespostaEntrada, user: dict = Depends(usuario_atual)):
    q = consultar_um("SELECT * FROM questoes WHERE id=?", (qid,))
    if not q:
        raise HTTPException(404, "Questão não encontrada.")

    letra = dados.resposta.upper()
    acertou = int(letra == q["gabarito"].upper())
    executar(
        "INSERT INTO respostas(usuario_id,questao_id,resposta,acertou,segundos,criado_em) "
        "VALUES(?,?,?,?,?,?)",
        (user["id"], qid, letra, acertou, max(0, dados.segundos), agora()),
    )
    return {
        "acertou": bool(acertou),
        "gabarito": q["gabarito"].upper(),
        "sua_resposta": letra,
        "ia_ativa": ia.disponivel(),
    }


@app.post("/api/questoes/gerar")
async def gerar_questoes(dados: GerarQuestoes, user: dict = Depends(usuario_atual)):
    if not ia.disponivel():
        raise HTTPException(503, "Geração por IA indisponível: nenhuma chave de API configurada.")

    try:
        novas = await run_in_threadpool(
            ia.gerar_questoes, dados.disciplina.strip(), dados.topico.strip(), dados.quantidade
        )
    except ValueError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(502, f"Falha ao consultar a IA: {e}")

    from datetime import datetime as _dt
    fonte = f"ia:{user['id']}:{int(_dt.now().timestamp())}"

    ids = []
    for i, q in enumerate(novas, 1):
        rid = executar(
            """INSERT INTO questoes
               (fonte,numero,ano,prova,disciplina,topico,enunciado,
                alt_a,alt_b,alt_c,alt_d,alt_e,gabarito,explicacao,
                origem,autor_id,criado_em)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fonte, i, _dt.now().year, "Gerada por IA",
             dados.disciplina.strip(), dados.topico.strip(),
             q["enunciado"], q["alternativas"]["A"], q["alternativas"]["B"],
             q["alternativas"]["C"], q["alternativas"]["D"], q["alternativas"]["E"],
             q["gabarito"], q["explicacao"], "ia", user["id"], agora()),
        )
        ids.append(rid)

    linhas = consultar(
        f"SELECT * FROM questoes WHERE id IN ({','.join('?' * len(ids))}) ORDER BY numero",
        tuple(ids),
    )
    return {
        "questoes": [_serializar_questao(r) for r in linhas],
        "topico": dados.topico.strip(),
        "disciplina": dados.disciplina.strip(),
    }


@app.get("/api/questoes/{qid}/explicacao")
async def explicacao(qid: int, user: dict = Depends(usuario_atual)):
    cache = consultar_um("SELECT texto FROM explicacoes WHERE questao_id=?", (qid,))
    if cache:
        return {"texto": cache["texto"], "cache": True}

    if not ia.disponivel():
        raise HTTPException(503, "Explicação por IA indisponível: nenhuma chave de API configurada.")

    q = consultar_um("SELECT * FROM questoes WHERE id=?", (qid,))
    if not q:
        raise HTTPException(404, "Questão não encontrada.")

    try:
        texto = await run_in_threadpool(ia.explicar_questao, dict(q))
    except Exception as e:
        raise HTTPException(502, f"Falha ao consultar a IA: {e}")

    executar(
        "INSERT OR REPLACE INTO explicacoes(questao_id,texto,criado_em) VALUES(?,?,?)",
        (qid, texto, agora()),
    )
    return {"texto": texto, "cache": False}


# ──────────────────────────────────────────────────────────────────────────────
# DESEMPENHO
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/desempenho")
def desempenho(user: dict = Depends(usuario_atual)):
    uid = user["id"]

    reds = consultar(
        "SELECT id,nota_final,c1,c2,c3,c4,c5,criado_em FROM redacoes "
        "WHERE usuario_id=? ORDER BY id",
        (uid,),
    )
    evolucao = [
        {"n": i + 1, "nota": r["nota_final"], "data": r["criado_em"][:10]}
        for i, r in enumerate(reds)
    ]
    if reds:
        comp = [
            {
                "numero": n,
                "titulo": ia.COMPETENCIAS[n],
                "media": round(sum(r[f"c{n}"] or 0 for r in reds) / len(reds)),
            }
            for n in range(1, 6)
        ]
    else:
        comp = [{"numero": n, "titulo": ia.COMPETENCIAS[n], "media": 0} for n in range(1, 6)]

    fraca = min(comp, key=lambda c: c["media"]) if reds else None

    disc = [
        {
            "disciplina": r["disciplina"] or "Geral",
            "total": r["total"],
            "acertos": r["acertos"] or 0,
            "pct": round((r["acertos"] or 0) / r["total"] * 100, 1) if r["total"] else 0,
        }
        for r in consultar(
            """SELECT q.disciplina, COUNT(*) total, SUM(r.acertou) acertos
                 FROM respostas r JOIN questoes q ON q.id=r.questao_id
                WHERE r.usuario_id=?
             GROUP BY q.disciplina ORDER BY total DESC""",
            (uid,),
        )
    ]

    tot = consultar_um(
        "SELECT COUNT(*) total, COALESCE(SUM(acertou),0) acertos FROM respostas WHERE usuario_id=?",
        (uid,),
    )
    dias = consultar_um(
        "SELECT COUNT(DISTINCT date(criado_em)) d FROM respostas WHERE usuario_id=?", (uid,)
    )["d"]

    # sequência de dias seguidos até hoje (contando redações + respostas)
    datas = {
        r["d"] for r in consultar(
            "SELECT DISTINCT date(criado_em) d FROM respostas WHERE usuario_id=? "
            "UNION SELECT DISTINCT date(criado_em) FROM redacoes WHERE usuario_id=?",
            (uid, uid),
        )
    }
    from datetime import date, timedelta as _td
    streak = 0
    hoje = date.today()
    while hoje.isoformat() in datas or (streak == 0 and (hoje - _td(days=1)).isoformat() in datas):
        if hoje.isoformat() not in datas:
            hoje -= _td(days=1)
            continue
        streak += 1
        hoje -= _td(days=1)

    return {
        "redacoes": len(reds),
        "media_redacao": round(sum(r["nota_final"] for r in reds) / len(reds)) if reds else 0,
        "melhor_redacao": max((r["nota_final"] for r in reds), default=0),
        "questoes": tot["total"],
        "acertos": tot["acertos"],
        "taxa_acerto": round(tot["acertos"] / tot["total"] * 100, 1) if tot["total"] else 0,
        "dias_ativos": dias,
        "streak": streak,
        "evolucao": evolucao,
        "competencias": comp,
        "competencia_fraca": fraca,
        "disciplinas": disc,
    }


@app.get("/api/status")
def status_publico():
    total = consultar_um("SELECT COUNT(*) t FROM questoes")["t"]
    return {"ok": True, "ia_ativa": ia.disponivel(), "questoes": total}


# ──────────────────────────────────────────────────────────────────────────────
# FRONT
# ──────────────────────────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def erro_json(request, exc: HTTPException):
    return JSONResponse({"erro": exc.detail}, status_code=exc.status_code)


AMIGAVEL = {
    "nome": "Informe seu nome (mínimo de 2 letras).",
    "email": "Informe um e-mail válido.",
    "senha": "A senha precisa ter pelo menos 6 caracteres.",
    "tema": "Escreva o tema da redação.",
    "texto": "A redação precisa ter pelo menos 200 caracteres.",
    "resposta": "A resposta precisa ser uma letra de A a E.",
}


@app.exception_handler(RequestValidationError)
async def erro_validacao(request, exc: RequestValidationError):
    """O front espera sempre {"erro": "..."}; sem isto o Pydantic devolve uma lista."""
    campo = ""
    for e in exc.errors():
        loc = [str(p) for p in e.get("loc", []) if p != "body"]
        if loc:
            campo = loc[-1]
            break
    return JSONResponse(
        {"erro": AMIGAVEL.get(campo, "Confira os dados enviados e tente novamente.")},
        status_code=422,
    )


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def raiz():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        alvo = WEB_DIR / caminho
        if caminho and alvo.is_file():
            return FileResponse(alvo)
        return FileResponse(WEB_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=bool(os.environ.get("DEV")),
    )

BASE_DIR = Path(__file__).resolve().parent

@app.get("/", response_class=HTMLResponse)
def home():
    index_path = BASE_DIR / "index.html"
    web_index_path = BASE_DIR / "web" / "index.html"
    
    if web_index_path.exists():
        with open(web_index_path, "r", encoding="utf-8") as f:
            return f.read()
    elif index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Aplicação no ar! index.html não encontrado.</h1>"

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=bool(os.environ.get("DEV")),
    )
