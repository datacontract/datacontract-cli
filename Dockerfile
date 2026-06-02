# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
# Docker Hardened Image (DHI), -dev variant: includes a shell and apt-get,
# so we can install build-time deps and copy the resulting venv into the
# minimal runtime image below.
FROM dhi.io/python:3.11-debian13-dev AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

USER root

# install uv (build-time only)
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

# install protoc — required by `datacontract import protobuf` (the CLI shells
# out to the system protoc to compile .proto files into FileDescriptorSets).
# The binary and well-known-types headers are copied into the runtime stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# create the venv that we'll copy into the runtime image
RUN python -m venv "$VIRTUAL_ENV"

WORKDIR /app

# install dependencies into the venv
COPY pyproject.toml MANIFEST.in /app/
COPY datacontract/ /app/datacontract/
RUN uv pip install --no-cache-dir ".[all]"

# pre-create a writable workdir owned by the nonroot user, to be copied into
# the runtime image (the runtime is distroless — no shell, no mkdir/chown).
RUN install -d -o nonroot -g nonroot /workdir


# ---------- Runtime ----------
# Docker Hardened Image (DHI): distroless, nonroot by default, no shell,
# no package manager. Only what's copied in is present.
FROM dhi.io/python:3.11-debian13 AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# copy the pre-built venv and the system protoc + well-known-types headers
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /usr/bin/protoc /usr/bin/protoc
COPY --from=builder /usr/include/google /usr/include/google

# nonroot-owned workdir (host volume mounts overlay this at runtime)
COPY --from=builder /workdir /home/datacontract
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
