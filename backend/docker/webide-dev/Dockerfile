# Local, pinned Web IDE development image. It is deliberately built on the
# developer machine and is never pulled from a registry by the application.
FROM node:22.14.0-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates coreutils git curl \
    python3.11 python3-pip \
    openjdk-17-jdk-headless build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && if getent passwd developer >/dev/null; then test "$(id -u developer)" -ne 0; \
       elif getent passwd 1000 >/dev/null; then useradd --create-home developer; \
       else useradd --create-home --uid 1000 developer; fi \
    && mkdir -p /workspace \
    && chown developer:developer /workspace

WORKDIR /workspace
USER developer
CMD ["sleep", "infinity"]
