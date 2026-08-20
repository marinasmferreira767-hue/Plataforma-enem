# Nota Mil

Plataforma de estudos com IA para ENEM e vestibulares. Correção de redação nas 5 competências
oficiais do INEP, banco de questões interativo com explicação da IA, gerador de questões inéditas
por tópico e painel de desempenho por aluno — tudo em uma SPA responsiva servida por FastAPI.

![desktop](https://img.shields.io/badge/desktop-1440px-6366F1) ![tablet](https://img.shields.io/badge/tablet-834px-6366F1) ![mobile](https://img.shields.io/badge/mobile-390px-6366F1) ![python](https://img.shields.io/badge/python-3.12-3776AB) ![fastapi](https://img.shields.io/badge/fastapi-0.115-009688) ![sqlite](https://img.shields.io/badge/sqlite-3-003B57)


## Sumário

- [O que tem dentro](#o-que-tem-dentro)
- [Rodando localmente](#rodando-localmente)
- [Publicando no Render (grátis)](#publicando-no-render-grátis)
- [Importando provas em PDF](#importando-provas-em-pdf)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Chaves de API](#chaves-de-api)
- [Limitações do plano free](#limitações-do-plano-free)


## O que tem dentro

- **Autenticação** — cadastro e login com senha PBKDF2-SHA256 (240 mil iterações) e sessão por token
- **Corretor de redação** — envia texto, IA devolve nota total, nota por competência, comentários, pontos fortes/fracos e reescritas com trecho original × versão sugerida
- **Banco de questões** — cartão-resposta interativo com teclas A–E + Enter, filtros por disciplina, explicação passo a passo gerada pela IA e cacheada no banco
- **Gerador de questões com IA** — aluno escolhe matéria e tópico, IA gera 1–5 questões inéditas com gabarito e explicação que ficam disponíveis no simulado
- **Painel de desempenho** — contagem regressiva para o ENEM, sequência de dias estudando, competência mais fraca, gráfico de evolução, radar das 5 competências e aproveitamento por disciplina
- **Histórico** — todas as correções ficam guardadas por aluno e podem ser reabertas por completo
- **Importador de PDFs** — script separado (`extrair_questoes.py`) que casa caderno + gabarito e alimenta o banco


## Rodando localmente

Pré-requisito: Python 3.12 ou superior.

```bash
git clone <seu-fork-ou-clone>
cd nota-mil
python -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                         # cole sua chave da IA no .env
uvicorn main:app --reload
```

Abra <http://localhost:8000>, crie uma conta e comece.

Sem chave de API a plataforma continua funcionando (login, banco de questões, gabarito, histórico); apenas a correção de redação, o gerador de questões e as explicações ficam indisponíveis — o app avisa isso na tela.


## Publicando no Render (grátis)

O passo a passo abaixo assume que você **nunca subiu nada no GitHub ou no Render** antes. Se já usa essas ferramentas, pule para o passo 4.

### 1. Subir o projeto no GitHub

1. Crie uma conta gratuita em <https://github.com>.
2. Clique em **New repository** no canto superior direito. Nome sugerido: `nota-mil`. Deixe **público** e **sem** README/gitignore (o projeto já tem os arquivos).
3. No terminal, dentro da pasta do projeto:

   ```bash
   git init
   git add .
   git commit -m "primeiro commit"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/nota-mil.git
   git push -u origin main
   ```

   Ao pedir credencial, o GitHub aceita username + [Personal Access Token](https://github.com/settings/tokens) (não a senha da conta).

### 2. Conseguir uma chave de API

Você precisa de **uma das duas** (a Anthropic tem prioridade se ambas estiverem configuradas):

- **Anthropic (recomendado)** — <https://console.anthropic.com>. Adicione US$ 5 de crédito e crie a chave em API Keys. Formato: `sk-ant-...`.
- **OpenAI** — <https://platform.openai.com/api-keys>. Formato: `sk-...`.

Guarde o valor completo em algum lugar — você vai colar no Render no passo seguinte.

### 3. Criar conta no Render

1. Acesse <https://render.com> e clique em **Get Started for Free**.
2. Autentique com sua conta GitHub e autorize o Render a ler os repositórios (dá para autorizar só o `nota-mil` se quiser).

### 4. Publicar via Blueprint

1. No painel do Render, clique em **New** → **Blueprint**.
2. Selecione o repositório `nota-mil`.
3. Render lê o arquivo `render.yaml` e mostra "Nota Mil" com plano **Free**. Clique **Apply**.
4. Na etapa de **Environment Variables**, preencha **uma** destas:
   - `ANTHROPIC_API_KEY` com a chave que você guardou, ou
   - `OPENAI_API_KEY` com a chave da OpenAI.

   As outras variáveis podem ficar em branco.
5. Clique em **Create Blueprint**. O primeiro deploy leva de 3 a 6 minutos.

### 5. Pronto

Quando o painel mostrar **Live**, seu link aparece no topo:

```
https://nota-mil-XXXX.onrender.com
```

Abra no navegador, crie uma conta e comece a usar. Cada `git push` para a branch `main` gera um novo deploy automaticamente.

> **Atenção:** no plano free o serviço "dorme" após 15 min sem tráfego e leva ~30 s para acordar na primeira requisição. É normal.


## Importando provas em PDF

O importador roda **localmente** — não sobe no Render. Depois de rodar, faça `git push` do `banco.db` atualizado.

Coloque os PDFs em `questoes_pdf/` seguindo o padrão de nomes:

```
questoes_pdf/
  enem_2023_dia1_caderno.pdf
  enem_2023_dia1_gabarito.pdf
```

Depois:

```bash
python extrair_questoes.py --dry-run          # confere sem gravar
python extrair_questoes.py                    # importa de verdade
```

Para um par específico com rótulo próprio:

```bash
python extrair_questoes.py \
  --caderno questoes_pdf/fuvest_2024_caderno.pdf \
  --gabarito questoes_pdf/fuvest_2024_gabarito.pdf \
  --ano 2024 --prova "FUVEST 2024" --sem-enem
```

No ENEM a disciplina é deduzida por faixa de numeração (1–45 Linguagens, 46–90 Humanas, 91–135 Natureza, 136–180 Matemática). Em outras provas use `--sem-enem` para classificar por palavras-chave.


## Estrutura do projeto

```
nota-mil/
  main.py                  # FastAPI: rotas de auth, redações, questões, geração, desempenho
  ia.py                    # camada de IA (Anthropic + OpenAI), prompts do corretor e gerador
  db.py                    # schema, conexão SQLite e migrações leves
  security.py              # hash de senha (PBKDF2) e tokens de sessão
  seed_questoes.py         # 16 questões iniciais para o app abrir com conteúdo
  extrair_questoes.py      # importador de provas em PDF (caderno + gabarito)
  requirements.txt

  web/
    index.html             # shell da SPA
    app.js                 # roteamento por hash, todas as views (~1200 linhas)
    app.css                # design system, ~950 linhas, sem framework

  Dockerfile               # imagem de produção (Python 3.12-slim, uvicorn)
  render.yaml              # blueprint do Render Free
  .env.example             # variáveis de ambiente para copiar em .env
  .dockerignore
  .gitignore

  questoes_pdf/            # PDFs de provas ficam aqui (não versionados)
  banco.db                 # SQLite criado no primeiro boot
```


## Chaves de API

| Variável            | Onde configurar                                      | Padrão               |
|---------------------|------------------------------------------------------|----------------------|
| `ANTHROPIC_API_KEY` | `.env` local ou variável de ambiente no Render       | —                    |
| `OPENAI_API_KEY`    | `.env` local ou variável de ambiente no Render       | —                    |
| `ANTHROPIC_MODEL`   | opcional — usar outro modelo Anthropic               | `claude-sonnet-4-6`  |
| `OPENAI_MODEL`      | opcional — usar outro modelo OpenAI                  | `gpt-4o`             |
| `DB_PATH`           | caminho do arquivo SQLite                            | `./banco.db`         |
| `PORT`              | porta HTTP (Render define automaticamente)           | `8000`               |


## Limitações do plano free

- **Serviço dorme** após 15 min sem tráfego. Primeira requisição depois disso demora ~30 s.
- **Sem disco persistente.** O `banco.db` fica em `/tmp/` e é apagado a cada redeploy. Contas de aluno, redações e questões geradas por IA se perdem. Serve muito bem para demonstração e teste; para vender de verdade migre para o plano Starter (US$ 7/mês) e monte um disco em `/data` no `render.yaml`.
- **512MB de RAM e 1 worker.** Basta para dezenas de usuários simultâneos.
- **750 horas grátis por mês por conta Render.** Suficiente para um serviço rodando 24/7.

Quando decidir migrar para o plano pago, edite `render.yaml` trocando `plan: free` por `plan: starter` e acrescente antes de `envVars`:

```yaml
    disk:
      name: nota-mil-dados
      mountPath: /data
      sizeGB: 1
```

E mude a variável `DB_PATH` de `/tmp/banco.db` para `/data/banco.db`. O banco passa a persistir entre deploys.
