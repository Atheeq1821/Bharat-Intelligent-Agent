FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CORAL_CONFIG_DIR=/coral-config

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

# Install Coral CLI in the image so backend can run `coral sql ...` directly.
RUN set -eux; \
    ok=0; \
    for attempt in 1 2 3 4 5; do \
      echo "Installing Coral (attempt ${attempt}/5)..."; \
      if curl -fL --retry 5 --retry-delay 2 --retry-all-errors https://withcoral.com/install.sh | sh; then \
        ok=1; \
        break; \
      fi; \
      sleep $((attempt * 3)); \
    done; \
    if [ "$ok" -ne 1 ]; then \
      echo "Coral installation failed after retries" >&2; \
      exit 1; \
    fi; \
    install -m 0755 /root/.local/bin/coral /usr/local/bin/coral; \
    coral --version

WORKDIR /app/backend

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt

COPY backend /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
