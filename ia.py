"""Camada de IA: correção de redação e explicação de questões.

Detecta automaticamente a chave disponível. Anthropic tem prioridade; se só houver
chave da OpenAI, usa a OpenAI. Sem nenhuma chave, os endpoints de IA respondem 503
e o restante da plataforma continua funcionando normalmente.
"""

from __future__ import annotations

import json
import os
import re

MODELO_ANTHROPIC = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MODELO_OPENAI = os.environ.get("OPENAI_MODEL", "gpt-4o")

COMPETENCIAS = {
    1: "Domínio da norma culta",
    2: "Compreender o tema e aplicar repertório",
    3: "Selecionar e organizar argumentos",
    4: "Coesão e mecanismos linguísticos",
    5: "Proposta de intervenção",
}

VALORES_VALIDOS = (0, 40, 80, 120, 160, 200)


class IAIndisponivel(RuntimeError):
    pass


def provedor() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def disponivel() -> bool:
    return provedor() is not None


def chamar(system: str, prompt: str, max_tokens: int = 3200) -> str:
    p = provedor()

    if p == "anthropic":
        from anthropic import Anthropic

        cliente = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = cliente.messages.create(
            model=MODELO_ANTHROPIC,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    if p == "openai":
        from openai import OpenAI

        cliente = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = cliente.chat.completions.create(
            model=MODELO_OPENAI,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    raise IAIndisponivel(
        "Nenhuma chave de API configurada. Defina ANTHROPIC_API_KEY ou OPENAI_API_KEY."
    )


def extrair_json(texto: str) -> dict:
    limpo = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        ini, fim = limpo.find("{"), limpo.rfind("}")
        if ini == -1 or fim == -1:
            raise ValueError("A IA não devolveu um JSON válido.")
        return json.loads(limpo[ini : fim + 1])


def normalizar_nota(v) -> int:
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        return 0
    v = max(0, min(200, v))
    return min(VALORES_VALIDOS, key=lambda x: abs(x - v))


# ── Correção de redação ───────────────────────────────────────────────────────

SYSTEM_CORRETOR = """Você é um corretor oficial de redações do ENEM, com anos de banca.
É rigoroso, técnico e justo: aplica exatamente a matriz de referência do INEP e não infla notas.
Responde SEMPRE e SOMENTE com um objeto JSON válido, sem markdown e sem texto fora do JSON."""

PROMPT_CORRETOR = """Corrija a redação abaixo segundo as 5 competências oficiais do ENEM.

TEMA PROPOSTO:
{tema}

REDAÇÃO DO ALUNO:
\"\"\"{texto}\"\"\"

REGRAS:
- Cada competência vale 0, 40, 80, 120, 160 ou 200 — use apenas esses valores.
- C1: domínio da modalidade escrita formal.
- C2: compreensão do tema, tipo dissertativo-argumentativo e repertório sociocultural produtivo.
  Fuga total ao tema zera esta competência.
- C3: seleção, relação e organização de fatos, opiniões e argumentos.
- C4: mecanismos linguísticos de coesão.
- C5: proposta de intervenção com agente, ação, meio, finalidade e detalhamento,
  respeitando os direitos humanos.
- Zere a redação inteira em caso de fuga total ao tema, texto com menos de 7 linhas,
  desrespeito aos direitos humanos ou não atendimento ao tipo textual.
- Cite trechos reais do aluno nos comentários. Seja específico, nunca genérico.

Responda EXATAMENTE neste JSON:
{{
  "competencias": [
    {{"numero": 1, "nota": 0, "comentario": "análise técnica de 2 a 4 frases citando trechos"}},
    {{"numero": 2, "nota": 0, "comentario": "..."}},
    {{"numero": 3, "nota": 0, "comentario": "..."}},
    {{"numero": 4, "nota": 0, "comentario": "..."}},
    {{"numero": 5, "nota": 0, "comentario": "..."}}
  ],
  "resumo": "diagnóstico geral em um parágrafo curto",
  "pontos_fortes": ["3 a 5 itens objetivos"],
  "pontos_a_melhorar": ["3 a 5 orientações acionáveis"],
  "reescritas": [
    {{"trecho_original": "trecho literal da redação",
      "sugestao": "versão reescrita",
      "motivo": "por que a nova versão é melhor"}}
  ]
}}
Inclua de 2 a 4 itens em "reescritas"."""


def corrigir_redacao(tema: str, texto: str) -> dict:
    bruto = chamar(SYSTEM_CORRETOR, PROMPT_CORRETOR.format(tema=tema, texto=texto), 3500)
    dados = extrair_json(bruto)

    comps, notas = [], {}
    for n in range(1, 6):
        item = next(
            (c for c in dados.get("competencias", []) if int(c.get("numero", 0)) == n), {}
        )
        nota = normalizar_nota(item.get("nota", 0))
        notas[n] = nota
        comps.append(
            {
                "numero": n,
                "titulo": COMPETENCIAS[n],
                "nota": nota,
                "comentario": item.get("comentario", "—"),
            }
        )

    return {
        "competencias": comps,
        "notas": notas,
        "nota_final": sum(notas.values()),
        "resumo": dados.get("resumo", ""),
        "pontos_fortes": dados.get("pontos_fortes", [])[:6],
        "pontos_a_melhorar": dados.get("pontos_a_melhorar", [])[:6],
        "reescritas": dados.get("reescritas", [])[:4],
    }


# ── Explicação de questão ─────────────────────────────────────────────────────

SYSTEM_PROFESSOR = (
    "Você é um professor particular experiente, didático e direto, "
    "especialista em ENEM e vestibulares brasileiros."
)


def explicar_questao(q, resposta_aluno: str | None = None) -> str:
    alternativas = "\n".join(
        f"{L}) {q['alt_' + L.lower()]}" for L in "ABCDE" if q.get("alt_" + L.lower())
    )
    prompt = f"""Explique esta questão de {q.get('disciplina') or 'vestibular'} para um aluno do ensino médio.

ENUNCIADO:
{q['enunciado']}

ALTERNATIVAS:
{alternativas}

GABARITO OFICIAL: {q['gabarito']}

Estruture em markdown, sem repetir o enunciado, exatamente assim:
**O que a questão cobra** — conteúdo e habilidade avaliada, 1 ou 2 frases.
**Resolução passo a passo** — o raciocínio completo até o gabarito, com cálculos quando houver.
**Por que as outras alternativas estão erradas** — uma linha objetiva por distrator.
**Dica de prova** — um macete prático para questões parecidas.
Máximo de 350 palavras."""
    return chamar(SYSTEM_PROFESSOR, prompt, 1500)


# ── Geração de questões ──────────────────────────────────────────────────────

SYSTEM_ELABORADOR = """Você é um elaborador de questões objetivas de vestibular no padrão ENEM.
Suas questões são inéditas, tecnicamente precisas e contextualizadas: partem sempre de uma situação,
texto, dado ou problema, e cobram uma habilidade específica. As alternativas erradas são plausíveis
(refletem erros conceituais comuns), nunca absurdas. Você responde SEMPRE e SOMENTE com JSON válido,
sem markdown e sem texto fora do JSON."""

PROMPT_ELABORADOR = """Elabore {n} questões inéditas, no padrão ENEM, sobre o tópico abaixo.

DISCIPLINA: {disciplina}
TÓPICO: {topico}
NÍVEL: {nivel}

REGRAS OBRIGATÓRIAS:
- Cada questão tem exatamente 5 alternativas (A, B, C, D, E) e uma única correta.
- O enunciado começa com um contexto (texto, dado, gráfico descrito em palavras, situação-problema).
- Os distratores refletem erros conceituais reais que o aluno cometeria; nada de "todas as anteriores".
- A explicação mostra o raciocínio até a resposta e, em uma linha, por que cada distrator está errado.
- Nada de referências a imagens, tabelas ou anexos que não estejam no próprio enunciado em palavras.
- Nunca cite direitos autorais, gabaritos oficiais ou provas anteriores.

Responda EXATAMENTE neste JSON:
{{
  "questoes": [
    {{
      "enunciado": "texto completo do enunciado, com contexto e pergunta",
      "alternativas": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
      "gabarito": "A",
      "explicacao": "resolução em 3 a 6 frases, encerrando com por que os distratores estão errados"
    }}
  ]
}}"""


def gerar_questoes(disciplina: str, topico: str, quantidade: int = 3, nivel: str = "ENEM") -> list[dict]:
    quantidade = max(1, min(quantidade, 5))
    bruto = chamar(
        SYSTEM_ELABORADOR,
        PROMPT_ELABORADOR.format(n=quantidade, disciplina=disciplina, topico=topico, nivel=nivel),
        3200,
    )
    dados = extrair_json(bruto)
    questoes = []
    for q in dados.get("questoes", [])[:quantidade]:
        alts = q.get("alternativas") or {}
        gab = str(q.get("gabarito", "")).strip().upper()[:1]
        if gab not in "ABCDE" or not all(alts.get(L) for L in "ABCDE"):
            continue
        questoes.append({
            "enunciado": str(q.get("enunciado", "")).strip(),
            "alternativas": {L: str(alts[L]).strip() for L in "ABCDE"},
            "gabarito": gab,
            "explicacao": str(q.get("explicacao", "")).strip(),
        })
    if not questoes:
        raise ValueError("A IA não devolveu nenhuma questão válida.")
    return questoes
