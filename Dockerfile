# ─── Imagem base ────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    DB_PATH=/tmp/banco.db

WORKDIR /app

# curl serve para o HEALTHCHECK. Instalação mínima para caber no free.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ─── Dependências Python (camada cacheada) ──────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Código ─────────────────────────────────────────────────────────────────
COPY . .

# Ajusta permissões para rodar como usuário não-root
RUN chown -R nobody:nogroup /app

USER nobody

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/api/status" || exit 1

# Um worker: o plano free do Render só tem 512 MB de RAM.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips='*'"]
