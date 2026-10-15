# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-runtime.txt /tmp/requirements-runtime.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-runtime.txt \
    && python -m pip check \
    && rm -f /tmp/requirements-runtime.txt

RUN groupadd --system --gid 10001 tmrds \
    && useradd --system --uid 10001 --gid tmrds --home-dir /nonexistent \
       --shell /usr/sbin/nologin tmrds \
    && mkdir -p /app/data/audit /app/data/research /app/data/logs \
    && chown -R tmrds:tmrds /app/data

COPY --chown=tmrds:tmrds api/ /app/api/
COPY --chown=tmrds:tmrds engines/ /app/engines/
COPY --chown=tmrds:tmrds scripts/ /app/scripts/
COPY --chown=tmrds:tmrds migrations/ /app/migrations/

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/research/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
