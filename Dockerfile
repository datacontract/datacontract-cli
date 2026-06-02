# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
# Docker Hardened Image (DHI) with Socket Firewall Free: signed, SBOM/VEX,
# tighter CVE patch SLAs than upstream Debian, and `pip` / `uv` installs are
# proxied through Socket Firewall to block malicious dependencies at build time.
# Requires `docker login dhi.io` with a Docker Hub account that has DHI access.
FROM dhi.io/python:3.11-debian13-sfw-dev AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# install uv (build-time only)
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

# install protoc here so we can copy it into the minimal runtime
# (the runtime image has no apt and no shell)
RUN apt-get update \
    && apt-get install -y --no-install-recommends protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# create the venv that we'll copy into the runtime image
RUN python3 -m venv "$VIRTUAL_ENV"

WORKDIR /app

# install dependencies into the venv, routed through Socket Firewall
COPY pyproject.toml MANIFEST.in /app/
COPY datacontract/ /app/datacontract/
RUN sfw uv pip install --no-cache-dir ".[all]"


# ---------- Runtime ----------
# Minimal Docker Hardened Image: signed, SBOM/VEX, nonroot (uid 65532), no
# shell, no apt. Only the artifacts copied below from the builder are present.
FROM dhi.io/python:3.11-debian13 AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:/opt/protoc/bin:$PATH \
    LD_LIBRARY_PATH=/opt/protoc/lib:$LD_LIBRARY_PATH

# copy the pre-built venv (readable+executable by nonroot)
COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv

# copy protoc + its shared libs so `datacontract import protobuf` works in the
# runtime. Glob matches the Debian multi-arch lib path for amd64 and arm64.
COPY --from=builder /usr/bin/protoc /opt/protoc/bin/protoc
COPY --from=builder /usr/lib/*-linux-gnu/libproto*.so* /opt/protoc/lib/

USER nonroot:nonroot
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
