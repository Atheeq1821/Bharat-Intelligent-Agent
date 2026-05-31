FROM debian:trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

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

WORKDIR /workspace

COPY scripts/coral/setup-sources.sh /usr/local/bin/setup-coral-sources
RUN chmod +x /usr/local/bin/setup-coral-sources

ENV CORAL_CONFIG_DIR=/coral-config

CMD ["bash", "-lc", "coral --version && echo 'Coral container ready. Use: docker compose run --rm coral setup-coral-sources' && sleep infinity"]
