FROM python:3.12-slim-bookworm

# Build arguments for version info (set by CI/CD)
ARG BUILD_VERSION
ARG GIT_SHA
ARG GIT_BRANCH

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BUILD_VERSION=${BUILD_VERSION} \
    GIT_SHA=${GIT_SHA} \
    GIT_BRANCH=${GIT_BRANCH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.lock /app/requirements.lock
RUN pip install --require-hashes -r /app/requirements.lock

COPY src /app/src
COPY entrypoint.sh /entrypoint.sh
COPY README.md LICENSE CHANGELOG.md /app/

RUN chmod +x /entrypoint.sh

ENV CONFIG_PATH=/config/playbook.yaml \
    DRY_RUN=false

ENV PYTHONPATH=/app/src

ENTRYPOINT ["/entrypoint.sh"]
