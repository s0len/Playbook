FROM python:3.14-slim-bookworm

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
COPY icon.png /app/icon.png

RUN chmod +x /entrypoint.sh

# Run as a non-root user (defense in depth). In Kubernetes, set
# securityContext.fsGroup=1000 (with fsGroupChangePolicy: OnRootMismatch) so the
# mounted /config and /data volumes are writable by this user.
RUN groupadd --gid 1000 playbook \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin playbook \
    && chown -R playbook:playbook /app
USER playbook

# GUI_HOST=0.0.0.0 is required so the GUI is reachable through a container/k8s
# Service (the app default is 127.0.0.1). Keep the GUI on a trusted network and
# set GUI_PASSWORD to require login — see src/playbook/gui/auth.py.
ENV CONFIG_PATH=/config/playbook.yaml \
    DRY_RUN=false \
    GUI_ENABLED=true \
    GUI_PORT=8765 \
    GUI_HOST=0.0.0.0

ENV PYTHONPATH=/app/src

# Expose GUI port
EXPOSE 8765

ENTRYPOINT ["/entrypoint.sh"]
