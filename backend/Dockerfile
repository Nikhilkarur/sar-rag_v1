# syntax=docker/dockerfile:1
# ---- Aegis API (FastAPI + Postgres + ChromaDB) ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Embedding model cache lives on a volume so it's downloaded once, not per container
    HF_HOME=/data/hf_cache \
    CHROMA_PERSIST_DIR=/data/chroma_data

WORKDIR /app

# CPU-only torch first: avoids pulling multi-GB CUDA wheels via sentence-transformers.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install -r requirements.txt

# Unprivileged runtime user
RUN groupadd --system --gid 10001 aegis \
 && useradd --system --uid 10001 --gid aegis --home-dir /app --shell /usr/sbin/nologin aegis

COPY --chown=aegis:aegis . .
RUN mkdir -p /data/hf_cache /data/chroma_data /app/storage/clients \
 && chown -R aegis:aegis /data /app/storage \
 && chmod +x docker/entrypoint.sh

USER aegis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["./docker/entrypoint.sh"]
# X-Forwarded-For is only trusted from FORWARDED_ALLOW_IPS (uvicorn default: 127.0.0.1) so
# callers cannot spoof their IP past the per-IP ingest rate limit.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
