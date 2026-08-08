# syntax=docker/dockerfile:1

# ---- build ----------------------------------------------------------------
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Dependencies as their own layer: they change far less often than your source,
# so this cache survives most edits.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

COPY src/ ./src/
RUN uv sync --locked --no-dev

# ---- runtime --------------------------------------------------------------
# slim, deliberately NOT distroless: no shell means no HealthCmd, and the health
# check is how deployment knows whether the release worked.
FROM python:3.13-slim

RUN useradd --create-home --uid 10001 app

# Stage 5 adds one line here — `RUN install -d -o app -g app /var/lib/hello-ockap` — when the
# service becomes stateful. It is not here yet on purpose: there is no volume to mount until
# then, and a mount path created for a volume that does not exist teaches nothing.

WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000
CMD ["python", "-m", "hello_ockap"]