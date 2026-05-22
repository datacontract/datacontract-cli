# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
FROM python:3.11-slim-trixie AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# install uv (build-time only)
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

# create the venv that we'll copy into the runtime image
RUN python -m venv "$VIRTUAL_ENV"

WORKDIR /app

# install dependencies into the venv
COPY pyproject.toml MANIFEST.in /app/
COPY datacontract/ /app/datacontract/
RUN uv pip install --no-cache-dir ".[all]"


# ---------- Runtime ----------
FROM python:3.11-slim-trixie AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# install protoc — required by `datacontract import protobuf` (the CLI shells out
# to the system protoc to compile .proto files into FileDescriptorSets)
RUN apt-get update \
    && apt-get install -y --no-install-recommends protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# copy the pre-built venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

RUN mkdir -p /home/datacontract
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
