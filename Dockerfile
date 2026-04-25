# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11

# --------------------------------------------------------------------------- #
# Stage 1 — builder: produce wheels                                            #
# --------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir=/wheels .

# --------------------------------------------------------------------------- #
# Stage 2 — runtime: minimal image, non-root user                              #
# --------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/app/.local/bin:${PATH}"

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels rcs-middleware \
    && rm -rf /wheels

COPY --chown=app:app . /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status==200 else 1)" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
