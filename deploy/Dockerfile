# Demo pública (ADR-0023/0024): base inmutable y bandeja efímera sólo con clave.
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
COPY deploy/iniciar_puente.py ./deploy/iniciar_puente.py
RUN uv sync --frozen --no-dev

# El arranque crea una copia nueva en /tmp sólo cuando hay clave. Nunca modifica demo.db.
CMD ["uv", "run", "--no-sync", "python", "deploy/iniciar_puente.py"]
