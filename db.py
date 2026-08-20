"""Camada de acesso ao SQLite.

O schema é o mesmo consumido pelo extrair_questoes.py, então provas importadas
por lá aparecem na plataforma sem nenhuma conversão.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "banco.db"))

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    salt       TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessoes(
    token      TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    criado_em  TEXT NOT NULL,
    expira_em  TEXT NOT NULL,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS redacoes(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL,
    tema          TEXT NOT NULL,
    texto         TEXT NOT NULL,
    nota_final    INTEGER NOT NULL,
    c1 INTEGER, c2 INTEGER, c3 INTEGER, c4 INTEGER, c5 INTEGER,
    feedback_json TEXT NOT NULL,
    criado_em     TEXT NOT NULL,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS questoes(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte      TEXT NOT NULL,
    numero     INTEGER,
    ano        INTEGER,
    prova      TEXT,
    disciplina TEXT,
    topico     TEXT,
    enunciado  TEXT NOT NULL,
    alt_a TEXT, alt_b TEXT, alt_c TEXT, alt_d TEXT, alt_e TEXT,
    gabarito   TEXT NOT NULL,
    explicacao TEXT,
    origem     TEXT NOT NULL DEFAULT 'importada',
    autor_id   INTEGER,
    criado_em  TEXT NOT NULL,
    UNIQUE(fonte, numero),
    FOREIGN KEY(autor_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS respostas(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    resposta   TEXT NOT NULL,
    acertou    INTEGER NOT NULL,
    segundos   INTEGER DEFAULT 0,
    criado_em  TEXT NOT NULL,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY(questao_id) REFERENCES questoes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS explicacoes(
    questao_id INTEGER PRIMARY KEY,
    texto      TEXT NOT NULL,
    criado_em  TEXT NOT NULL,
    FOREIGN KEY(questao_id) REFERENCES questoes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resp_user  ON respostas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_resp_q     ON respostas(questao_id);
CREATE INDEX IF NOT EXISTS idx_red_user   ON redacoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_q_disc     ON questoes(disciplina);
CREATE INDEX IF NOT EXISTS idx_sess_user  ON sessoes(usuario_id);
"""


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tentar_wal(conn: sqlite3.Connection) -> None:
    """WAL falha em NFS e alguns volumes montados; caímos para DELETE nesse caso."""
    try:
        modo = conn.execute("PRAGMA journal_mode = WAL;").fetchone()[0]
        if modo.lower() != "wal":
            conn.execute("PRAGMA journal_mode = DELETE;")
    except sqlite3.OperationalError:
        conn.execute("PRAGMA journal_mode = DELETE;")


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    """Conexão por operação. Escritas usam transação implícita com commit no fim."""
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def consultar(sql: str, par: tuple = ()) -> list[sqlite3.Row]:
    with conectar() as c:
        return c.execute(sql, par).fetchall()


def consultar_um(sql: str, par: tuple = ()) -> sqlite3.Row | None:
    with conectar() as c:
        return c.execute(sql, par).fetchone()


def executar(sql: str, par: tuple = ()) -> int:
    with conectar() as c:
        cur = c.execute(sql, par)
        return cur.lastrowid


def init_db() -> None:
    # garante que a pasta do arquivo existe (importante no Render, com disco em /data)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with conectar() as c:
        _tentar_wal(c)
        c.executescript(SCHEMA)

    # migrações leves — bancos criados por versões anteriores ganham as colunas novas
    with conectar() as c:
        def cols(tabela: str) -> set[str]:
            return {r["name"] for r in c.execute(f"PRAGMA table_info({tabela})")}

        for tabela, coluna, ddl in [
            ("respostas", "segundos",  "ALTER TABLE respostas ADD COLUMN segundos INTEGER DEFAULT 0"),
            ("questoes",  "topico",    "ALTER TABLE questoes ADD COLUMN topico TEXT"),
            ("questoes",  "explicacao","ALTER TABLE questoes ADD COLUMN explicacao TEXT"),
            ("questoes",  "origem",    "ALTER TABLE questoes ADD COLUMN origem TEXT NOT NULL DEFAULT 'importada'"),
            ("questoes",  "autor_id",  "ALTER TABLE questoes ADD COLUMN autor_id INTEGER"),
        ]:
            if coluna not in cols(tabela):
                c.execute(ddl)
