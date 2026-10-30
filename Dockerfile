FROM python:3.12-alpine AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache build-base libffi-dev

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    STORYGRAM_DATA_DIR=/data \
    STORYGRAM_SCHEMA_DIR=/app/schema \
    GIT_AUTHOR_NAME=Storygram \
    GIT_AUTHOR_EMAIL=storygram@localhost \
    GIT_COMMITTER_NAME=Storygram \
    GIT_COMMITTER_EMAIL=storygram@localhost

RUN apk add --no-cache git tini \
    && addgroup -S storygram \
    && adduser -S -G storygram -h /app storygram

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

WORKDIR /app
COPY --chown=storygram:storygram schema /app/schema
COPY --chown=storygram:storygram docker-entrypoint.sh /usr/local/bin/storygram-entrypoint
RUN chmod +x /usr/local/bin/storygram-entrypoint \
    && mkdir -p /data \
    && chown -R storygram:storygram /app /data

USER storygram
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=2)"

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/storygram-entrypoint"]
CMD ["storygram", "web", "--host", "0.0.0.0", "--port", "8080", "--archive", "/data"]
