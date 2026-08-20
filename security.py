"""Hash de senha (PBKDF2-SHA256) e sessões por token opaco."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from db import agora, conectar, consultar_um, executar

ITERACOES = 240_000
DIAS_SESSAO = 30


def hash_senha(senha: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), ITERACOES)
    return dk.hex(), salt


def conferir_senha(senha: str, senha_hash: str, salt: str) -> bool:
    calc, _ = hash_senha(senha, salt)
    return hmac.compare_digest(calc, senha_hash)


def criar_sessao(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expira = (datetime.now() + timedelta(days=DIAS_SESSAO)).strftime("%Y-%m-%d %H:%M:%S")
    executar(
        "INSERT INTO sessoes(token,usuario_id,criado_em,expira_em) VALUES(?,?,?,?)",
        (token, usuario_id, agora(), expira),
    )
    return token


def usuario_da_sessao(token: str | None):
    if not token:
        return None
    row = consultar_um(
        """SELECT u.id, u.nome, u.email, s.expira_em
             FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token = ?""",
        (token,),
    )
    if not row:
        return None
    if row["expira_em"] < agora():
        encerrar_sessao(token)
        return None
    return {"id": row["id"], "nome": row["nome"], "email": row["email"]}


def encerrar_sessao(token: str) -> None:
    executar("DELETE FROM sessoes WHERE token = ?", (token,))


def limpar_sessoes_expiradas() -> None:
    with conectar() as c:
        c.execute("DELETE FROM sessoes WHERE expira_em < ?", (agora(),))
