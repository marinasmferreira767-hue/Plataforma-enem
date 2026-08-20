"""
extrair_questoes.py — importa provas em PDF para o banco.db
===========================================================

Lê um PDF com o CADERNO DE QUESTÕES e outro com o GABARITO, cruza enunciado +
alternativas com a resposta correta e grava tudo na tabela `questoes`.

USO RÁPIDO (modo automático)
----------------------------
1. Coloque os PDFs na pasta questoes_pdf/ seguindo a convenção de nome:

       enem_2023_dia1_caderno.pdf
       enem_2023_dia1_gabarito.pdf

   Qualquer par com o mesmo prefixo funciona: <prefixo>_caderno.pdf e
   <prefixo>_gabarito.pdf.

2. Rode:

       python extrair_questoes.py

USO MANUAL (um par específico)
------------------------------
    python extrair_questoes.py \
        --caderno  questoes_pdf/enem_2023_dia1_caderno.pdf \
        --gabarito questoes_pdf/enem_2023_dia1_gabarito.pdf \
        --ano 2023 --prova "ENEM 2023 - Dia 1"

OUTRAS OPÇÕES
-------------
    --disciplina "Matemática"   força a disciplina de todas as questões
    --sem-enem                  desliga o mapeamento por faixa de número do ENEM
    --dry-run                   mostra o que seria importado sem gravar
    --pasta outra_pasta/        muda a pasta varrida no modo automático

DEPENDÊNCIA
-----------
    pip install pdfplumber
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("Instale a dependência primeiro:  pip install pdfplumber")

BASE_DIR = Path(__file__).resolve().parent
DB_PADRAO = BASE_DIR / "banco.db"
PASTA_PADRAO = BASE_DIR / "questoes_pdf"

# Faixas de numeração do ENEM (usadas quando --disciplina não é informada)
FAIXAS_ENEM = [
    (1, 45, "Linguagens"),
    (46, 90, "Ciências Humanas"),
    (91, 135, "Ciências da Natureza"),
    (136, 180, "Matemática"),
]

PALAVRAS_CHAVE = {
    "Matemática": ["equação", "triângulo", "porcentagem", "gráfico da função", "probabilidade",
                   "média aritmética", "volume", "área do", "juros", "razão entre"],
    "Ciências da Natureza": ["célula", "átomo", "molécula", "energia cinética", "reação química",
                             "ecossistema", "força resultante", "ph ", "dna", "velocidade média"],
    "Ciências Humanas": ["século", "revolução", "governo", "sociedade", "território",
                         "cidadania", "colonial", "urbaniz", "geopolít", "constituição"],
    "Linguagens": ["texto", "poema", "linguagem", "verbo", "narrador", "crônica",
                   "personagem", "figura de linguagem", "oração", "modernismo"],
}


# ──────────────────────────────────────────────────────────────────────────────
# BANCO
# ──────────────────────────────────────────────────────────────────────────────

def conectar(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS questoes(
               id         INTEGER PRIMARY KEY AUTOINCREMENT,
               fonte      TEXT NOT NULL,
               numero     INTEGER,
               ano        INTEGER,
               prova      TEXT,
               disciplina TEXT,
               enunciado  TEXT NOT NULL,
               alt_a TEXT, alt_b TEXT, alt_c TEXT, alt_d TEXT, alt_e TEXT,
               gabarito   TEXT NOT NULL,
               criado_em  TEXT NOT NULL,
               UNIQUE(fonte, numero)
           )"""
    )
    conn.commit()
    return conn


# ──────────────────────────────────────────────────────────────────────────────
# LEITURA DO PDF
# ──────────────────────────────────────────────────────────────────────────────

def ler_pdf(caminho: Path) -> str:
    partes: list[str] = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            partes.append(pagina.extract_text() or "")
    return "\n".join(partes)


def ler_tabelas(caminho: Path) -> list[list[list[str]]]:
    tabelas: list[list[list[str]]] = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            for t in pagina.extract_tables() or []:
                tabelas.append([[(cel or "").strip() for cel in linha] for linha in t])
    return tabelas


def limpar(texto: str) -> str:
    """Remove ruído típico de caderno de prova: cabeçalhos, rodapés, hifenização."""
    linhas = []
    for linha in texto.splitlines():
        l = linha.strip()
        if not l:
            continue
        if re.fullmatch(r"[\d\s\-–|•*]+", l):                  # números de página soltos
            continue
        if re.search(r"(ENEM|INEP|MINISTÉRIO DA EDUCAÇÃO|CADERNO|LC\s*-\s*\d|"
                     r"www\.|Página\s+\d+|folha de respostas)", l, re.I) and len(l) < 90:
            continue
        linhas.append(l)
    txt = "\n".join(linhas)
    txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)                  # junta palavras hifenizadas
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt


# ──────────────────────────────────────────────────────────────────────────────
# PARSER DO CADERNO
# ──────────────────────────────────────────────────────────────────────────────

RE_QUESTAO = re.compile(r"QUEST[ÃA]O\s*0*(\d{1,3})\b", re.IGNORECASE)

# Passe 1 (estrito): exige delimitador — "A)", "(A)", "A.", "A -", "A:"
RE_ALT_ESTRITO = re.compile(r"^\s*\(?([A-Ea-e])(?:\)|\]|[\.\-–—:])\s*(?=\S)")
# Passe 2 (tolerante): aceita a letra sozinha — "A texto da alternativa"
RE_ALT_TOLERANTE = re.compile(r"^\s*\(?([A-Ea-e])\)?\s*[\)\.\-–—:]?\s+(?=\S)")


def blocos_de_questoes(texto: str) -> list[tuple[int, str]]:
    """Fatia o caderno em blocos (número da questão, conteúdo bruto)."""
    marcas = list(RE_QUESTAO.finditer(texto))
    blocos: list[tuple[int, str]] = []
    for i, m in enumerate(marcas):
        ini = m.end()
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        blocos.append((int(m.group(1)), texto[ini:fim].strip()))
    return blocos


def _tentar_separar(linhas: list[str], regex: re.Pattern) -> tuple[str, dict[str, str]]:
    """Procura marcadores A→E em ordem. A exigência de ordem evita confundir uma
    linha do enunciado iniciada por 'A ' com a alternativa A."""
    esperada = "A"
    inicio_alt: int | None = None
    marcadores: list[tuple[int, str]] = []

    for i, linha in enumerate(linhas):
        m = regex.match(linha)
        if m and m.group(1).upper() == esperada:
            marcadores.append((i, esperada))
            if inicio_alt is None:
                inicio_alt = i
            if esperada == "E":
                break
            esperada = chr(ord(esperada) + 1)

    if len(marcadores) < 4 or not inicio_alt:      # inicio_alt == 0 => sem enunciado
        return "", {}

    enunciado = "\n".join(linhas[:inicio_alt]).strip()
    if len(enunciado) < 25:
        return "", {}

    alternativas: dict[str, str] = {}
    for idx, (linha_i, letra) in enumerate(marcadores):
        fim = marcadores[idx + 1][0] if idx + 1 < len(marcadores) else len(linhas)
        corpo = [regex.sub("", linhas[linha_i], count=1)] + linhas[linha_i + 1: fim]
        alternativas[letra] = " ".join(p.strip() for p in corpo if p.strip()).strip()

    return enunciado, alternativas


def separar_alternativas(bloco: str) -> tuple[str, dict[str, str]]:
    """Divide o bloco em enunciado + dicionário {'A': texto, ...}.

    Faz duas passagens: primeiro exigindo o delimitador ('A)', 'A.', 'A -'),
    que é o formato dos cadernos oficiais; se falhar, aceita a letra isolada.
    """
    linhas = bloco.splitlines()

    for regex in (RE_ALT_ESTRITO, RE_ALT_TOLERANTE):
        enunciado, alts = _tentar_separar(linhas, regex)
        if len(alts) >= 4:
            return enunciado, alts

    return bloco.strip(), {}


def parse_caderno(caminho: Path) -> dict[int, dict]:
    texto = limpar(ler_pdf(caminho))
    questoes: dict[int, dict] = {}

    for numero, bloco in blocos_de_questoes(texto):
        enunciado, alts = separar_alternativas(bloco)
        if len(alts) < 4 or len(enunciado) < 25:
            continue
        questoes[numero] = {"numero": numero, "enunciado": enunciado, "alternativas": alts}

    return questoes


# ──────────────────────────────────────────────────────────────────────────────
# PARSER DO GABARITO
# ──────────────────────────────────────────────────────────────────────────────

RE_PAR = re.compile(r"\b(\d{1,3})\s*[\-–—.:\)]?\s*([A-Ea-e])\b")


def parse_gabarito(caminho: Path) -> dict[int, str]:
    """Lê o gabarito em tabela ou em texto corrido ('1 - A', '01 C', '1) A')."""
    gab: dict[int, str] = {}

    # 1) tenta as tabelas do PDF, formato mais confiável
    for tabela in ler_tabelas(caminho):
        for linha in tabela:
            celulas = [c for c in linha if c]
            for i, cel in enumerate(celulas):
                if re.fullmatch(r"0*\d{1,3}", cel) and i + 1 < len(celulas):
                    prox = celulas[i + 1].strip().upper()
                    if re.fullmatch(r"[A-E]", prox):
                        gab[int(cel)] = prox
                for n, letra in RE_PAR.findall(cel):
                    gab.setdefault(int(n), letra.upper())

    # 2) complementa com o texto corrido
    texto = ler_pdf(caminho)
    for n, letra in RE_PAR.findall(texto):
        n = int(n)
        if 1 <= n <= 250:
            gab.setdefault(n, letra.upper())

    return gab


# ──────────────────────────────────────────────────────────────────────────────
# CLASSIFICAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def disciplina_por_numero(numero: int) -> str | None:
    for ini, fim, nome in FAIXAS_ENEM:
        if ini <= numero <= fim:
            return nome
    return None


def disciplina_por_texto(texto: str) -> str:
    t = texto.lower()
    placar = {d: sum(t.count(p) for p in palavras) for d, palavras in PALAVRAS_CHAVE.items()}
    melhor = max(placar, key=placar.get)
    return melhor if placar[melhor] > 0 else "Outra"


# ──────────────────────────────────────────────────────────────────────────────
# IMPORTAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def importar(conn: sqlite3.Connection, caderno: Path, gabarito: Path,
             ano: int | None, prova: str | None, disciplina: str | None,
             usar_faixas: bool, dry_run: bool) -> tuple[int, int]:
    print(f"\n▶ Caderno : {caderno.name}")
    print(f"▶ Gabarito: {gabarito.name}")

    questoes = parse_caderno(caderno)
    gab = parse_gabarito(gabarito)
    print(f"  · {len(questoes)} questões lidas · {len(gab)} respostas no gabarito")

    fonte = caderno.stem
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gravadas, sem_gabarito = 0, 0

    for numero in sorted(questoes):
        q = questoes[numero]
        resposta = gab.get(numero)
        if not resposta:
            sem_gabarito += 1
            continue

        if disciplina:
            disc = disciplina
        elif usar_faixas and disciplina_por_numero(numero):
            disc = disciplina_por_numero(numero)
        else:
            disc = disciplina_por_texto(q["enunciado"])

        alts = q["alternativas"]
        if dry_run:
            print(f"    [{numero:>3}] {disc:<20} gab {resposta} · {q['enunciado'][:60]}...")
            gravadas += 1
            continue

        conn.execute(
            """INSERT OR REPLACE INTO questoes
               (fonte,numero,ano,prova,disciplina,enunciado,alt_a,alt_b,alt_c,alt_d,alt_e,gabarito,criado_em)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fonte, numero, ano, prova or fonte, disc, q["enunciado"],
             alts.get("A"), alts.get("B"), alts.get("C"), alts.get("D"), alts.get("E"),
             resposta, agora),
        )
        gravadas += 1

    if not dry_run:
        conn.commit()

    print(f"  ✓ {gravadas} questões {'simuladas' if dry_run else 'gravadas'}"
          f" · {sem_gabarito} sem resposta no gabarito")
    return gravadas, sem_gabarito


def pares_da_pasta(pasta: Path) -> list[tuple[Path, Path]]:
    """Encontra pares <prefixo>_caderno.pdf + <prefixo>_gabarito.pdf."""
    pares = []
    for caderno in sorted(pasta.glob("*caderno*.pdf")):
        prefixo = re.sub(r"[_\-\s]*caderno.*$", "", caderno.stem, flags=re.I)
        candidatos = list(pasta.glob(f"{prefixo}*gabarito*.pdf"))
        if candidatos:
            pares.append((caderno, candidatos[0]))
        else:
            print(f"⚠ Sem gabarito correspondente para {caderno.name}")
    return pares


def ano_do_nome(nome: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", nome)
    return int(m.group(0)) if m else None


def main() -> None:
    p = argparse.ArgumentParser(description="Importa provas em PDF para o banco.db")
    p.add_argument("--caderno", type=Path, help="PDF do caderno de questões")
    p.add_argument("--gabarito", type=Path, help="PDF do gabarito")
    p.add_argument("--pasta", type=Path, default=PASTA_PADRAO, help="pasta varrida no modo automático")
    p.add_argument("--db", type=Path, default=DB_PADRAO, help="caminho do banco SQLite")
    p.add_argument("--ano", type=int, help="ano da prova")
    p.add_argument("--prova", type=str, help='rótulo da prova, ex.: "ENEM 2023 - Dia 1"')
    p.add_argument("--disciplina", type=str, help="força a disciplina de todas as questões")
    p.add_argument("--sem-enem", action="store_true",
                   help="não usar as faixas de numeração do ENEM para classificar")
    p.add_argument("--dry-run", action="store_true", help="apenas simula, sem gravar")
    args = p.parse_args()

    conn = conectar(args.db)
    usar_faixas = not args.sem_enem
    total = 0

    if args.caderno and args.gabarito:
        if not args.caderno.exists() or not args.gabarito.exists():
            sys.exit("Arquivo não encontrado. Confira os caminhos informados.")
        total, _ = importar(conn, args.caderno, args.gabarito,
                            args.ano or ano_do_nome(args.caderno.name), args.prova,
                            args.disciplina, usar_faixas, args.dry_run)
    else:
        args.pasta.mkdir(parents=True, exist_ok=True)
        pares = pares_da_pasta(args.pasta)
        if not pares:
            sys.exit(
                f"Nenhum par encontrado em {args.pasta}/.\n"
                "Nomeie os arquivos como <prova>_caderno.pdf e <prova>_gabarito.pdf, "
                "ou use --caderno e --gabarito."
            )
        for caderno, gabarito in pares:
            n, _ = importar(conn, caderno, gabarito,
                            args.ano or ano_do_nome(caderno.name),
                            args.prova or caderno.stem.replace("_", " ").title(),
                            args.disciplina, usar_faixas, args.dry_run)
            total += n

    restante = conn.execute("SELECT COUNT(*) FROM questoes").fetchone()[0]
    conn.close()
    print(f"\n✅ Importação concluída: {total} questões processadas. "
          f"Banco agora tem {restante} questões.\n")


if __name__ == "__main__":
    main()
