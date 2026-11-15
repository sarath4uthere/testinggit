# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------
# API image: 4 stages
#   base    -> common settings
#   deps    -> production libraries installed into /install
#   test    -> runs the unit tests (build fails if a test fails)
#   runtime -> small final image, non-root, no test tools
# Build the final image : docker build --target runtime -t shop-api .
# Run only the tests    : docker build --target test .
# ---------------------------------------------------------------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base AS test
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt
COPY app ./app
COPY tests ./tests
RUN python -m pytest -q tests

FROM base AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="shop-api" \
      org.opencontainers.image.version="${APP_VERSION}"
COPY --from=deps /install /usr/local
COPY app ./app
COPY migrations ./migrations
COPY migrate.py entrypoint.sh ./
RUN useradd --system --uid 10001 appuser
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=40s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
ENTRYPOINT ["sh", "./entrypoint.sh"]
