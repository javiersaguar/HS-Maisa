# Demo pública de Albertitos (ADR-0023): el puente de la consola y el chat, de sólo lectura, sobre deploy/demo.db.
# Una imagen para los dos servicios de render.yaml; cada uno arranca con su propio comando.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    ALBERTITOS_HOST=0.0.0.0 \
    ALBERTITOS_DB=/app/deploy/demo.db

RUN pip install --no-cache-dir uv==0.8.*
WORKDIR /app

# Dependencias primero (capa en caché mientras no cambie el lock)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY deploy/demo.db ./deploy/demo.db
RUN uv sync --frozen --no-dev

# Por defecto, el puente (sin --bandeja: la demo pública no escribe ni gasta LLM al subir PDF)
CMD ["uv", "run", "--no-sync", "python", "-m", "albertitos.console.api", "--db", "/app/deploy/demo.db"]
