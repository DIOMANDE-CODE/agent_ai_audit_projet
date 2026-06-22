# syntax=docker/dockerfile:1.4
FROM python:3.12-slim

LABEL maintainer="DIOMANDE DROH MARTIAL"

# ── Python ────────────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── Streamlit (production) ────────────────────────────────────────────────────
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# Utilisateur non-root (créé avant COPY pour --chown)
RUN useradd --create-home --no-log-init --shell /bin/bash appuser

# Dépendances — couche séparée du code pour maximiser le cache Docker
COPY --chown=appuser:appuser requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --compile -r requirements.txt

# Code source
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8501

# Vérification de santé via l'endpoint natif de Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" \
    || exit 1

CMD ["streamlit", "run", "app.py"]
