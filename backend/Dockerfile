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

# Unicode fonts for the SAR PDF (customer names in Devanagari/Arabic; Helvetica renders them as
# black boxes). Pinned to a notofonts commit and checksum-verified; fetched directly rather than
# via apt's fonts-noto. World-readable: ADD from a URL defaults to 0600 and we run as `aegis`.
ARG NOTO_FONTS=https://raw.githubusercontent.com/notofonts/notofonts.github.io/e3ff34c3178cb4012124c9e6390b9a3535ff2c3f/fonts
ADD --chmod=644 --checksum=sha256:478c558ea716033cd60c03438f628dfa75694dcf6b5f6d505a2f05fd2b4f3823 \
    ${NOTO_FONTS}/NotoSans/hinted/ttf/NotoSans-Regular.ttf /usr/share/fonts/truetype/noto/
ADD --chmod=644 --checksum=sha256:1df075a380fc7cb898acf64c1f7b3b4dd780de3caa860178bf929de35817a913 \
    ${NOTO_FONTS}/NotoSans/hinted/ttf/NotoSans-Bold.ttf /usr/share/fonts/truetype/noto/
ADD --chmod=644 --checksum=sha256:4e3c66638958c3e2ab5d37f47a8deb89fffeb7be9985c665a519bbc7ba762313 \
    ${NOTO_FONTS}/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Regular.ttf /usr/share/fonts/truetype/noto/
ADD --chmod=644 --checksum=sha256:6a09c8d797cfc803d32cdc731e809424d74cbaff59f503de34ade421a08e5bc2 \
    ${NOTO_FONTS}/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Bold.ttf /usr/share/fonts/truetype/noto/
ADD --chmod=644 --checksum=sha256:bdff3e5659d67e67def05b33f749683b9376ae819d65d3dd62ac4640b3aaef48 \
    ${NOTO_FONTS}/NotoSansArabic/hinted/ttf/NotoSansArabic-Regular.ttf /usr/share/fonts/truetype/noto/
ADD --chmod=644 --checksum=sha256:4e5462d2e8be880317b9f49b5b2da109ddb6a3563d91cc604b67f3535832a555 \
    ${NOTO_FONTS}/NotoSansArabic/hinted/ttf/NotoSansArabic-Bold.ttf /usr/share/fonts/truetype/noto/

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
# X-Forwarded-For is only trusted from FORWARDED_ALLOW_IPS (uvicorn default: 127.0.0.1).
# docker-compose.yml sets it to the nginx container's fixed IP — never "*", because port
# 8000 is also reachable directly and callers could then spoof their IP.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
