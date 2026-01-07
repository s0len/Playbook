FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apk add --no-cache \
    bash \
    ca-certificates \
    tzdata \
    curl

WORKDIR /app

COPY requirements.lock /app/requirements.lock
RUN pip install --require-hashes -r /app/requirements.lock

COPY src /app/src
COPY entrypoint.sh /entrypoint.sh
COPY README.md LICENSE /app/

RUN chmod +x /entrypoint.sh

ENV CONFIG_PATH=/config/playbook.yaml \
    DRY_RUN=false

ENV PYTHONPATH=/app/src

ENTRYPOINT ["/entrypoint.sh"]