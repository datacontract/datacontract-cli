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

# create the venv that we'll copy into the runtime image
RUN python3 -m venv "$VIRTUAL_ENV"

WORKDIR /app

# install dependencies into the venv, routed through Socket Firewall
COPY pyproject.toml MANIFEST.in /app/
COPY datacontract/ /app/datacontract/
RUN sfw uv pip install --no-cache-dir ".[all]"


# ---------- Runtime ----------
# NOTE: the `-dev` suffix is intentional. In Docker Hardened Images, `-dev`
# names a hardened production variant that ships bash + coreutils + apt — it is
# NOT a development-only image. It's signed, ships SBOM/VEX, and is on the same
# DHI patch SLAs as the minimal variant.
#
# We picked `-dev` over the minimal `3.11-debian13` (no shell, no apt) because
# PySpark's `spark-submit` is a bash script. Without bash, Kafka/Spark engines
# can't even start. The `-dev` variant adds bash + coreutils + apt at ~60 MB
# cost. Default user is root; switched to nonroot via the USER directive at
# the bottom.
FROM dhi.io/python:3.11-debian13-dev AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    JAVA_HOME=/opt/java/openjdk/17-jre \
    PATH=/opt/venv/bin:/opt/java/openjdk/17-jre/bin:$PATH

# copy the pre-built venv (readable+executable by the nonroot user)
COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv

# Eclipse Temurin JRE 17 — required by PySpark-backed engines (Kafka, Spark).
# Without Java, those engines fail at SparkSession startup. Adding the JRE here
# means `datacontract test` against a kafka/spark server works in the image
# without users having to extend it.
COPY --from=dhi.io/eclipse-temurin:17-debian13 /opt/java/openjdk /opt/java/openjdk

USER nonroot:nonroot
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
