FROM ghcr.io/astral-sh/uv:python3.14-alpine AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project --no-editable
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-editable --reinstall-package billbo

FROM python:3.14-alpine
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN adduser -S -H app
COPY --from=build /app/.venv ./.venv
COPY alembic.ini ./
COPY alembic ./alembic
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health')"]
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-server-header"]
