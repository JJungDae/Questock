# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c

FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM ${PYTHON_IMAGE} AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUESTOCK_SOURCE_MODE=unconfigured

RUN groupadd --system questock \
    && useradd --system --gid questock --home-dir /app --no-create-home questock

WORKDIR /app
COPY --from=builder --chown=questock:questock /app/.venv /app/.venv
COPY --chown=questock:questock app ./app
COPY --chown=questock:questock data ./data
COPY --chown=questock:questock streamlit_app.py ./

USER questock
EXPOSE 8000 8501

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
