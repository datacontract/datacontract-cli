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
    JAVA_HOME=/opt/java/openjdk/21-jre \
    PATH=/opt/venv/bin:/opt/java/openjdk/21-jre/bin:$PATH

# copy the pre-built venv (readable+executable by the nonroot user)
COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv

# Eclipse Temurin JRE 21 — required by PySpark-backed engines (Kafka, Spark).
# Spark 4.0 (what `.[all]` resolves to) supports Java 17 and 21. Without Java,
# those engines fail at SparkSession startup.
COPY --from=dhi.io/eclipse-temurin:21-debian13 /opt/java/openjdk /opt/java/openjdk

# Air-gap the Kafka/Spark engine: pre-fetch the Spark Kafka + Avro connector JARs
# at build time and bundle them onto the PySpark classpath. Without this, the
# first `datacontract test` against a Kafka server resolves `spark.jars.packages`
# from Maven Central at runtime (~60 MB download, needs outbound network). The
# JARs are resolved with the exact Spark/Scala version of the bundled PySpark, so
# they always match the runtime; `connector_jars_already_on_classpath()` then
# tells the engine to skip the Maven resolve and start offline.
RUN <<'PY' python3
import glob
import os
import shutil

import pyspark
from pyspark.sql import SparkSession

from datacontract.engines.ibis.connections.kafka import spark_connector_packages

ivy_home = "/tmp/ivyhome"
spark = (
    SparkSession.builder.appName("prefetch-connectors")
    .config("spark.jars.ivy", ivy_home)
    .config("spark.driver.bindAddress", "127.0.0.1")
    .config("spark.driver.host", "127.0.0.1")
    .config("spark.ui.enabled", "false")
    .config("spark.jars.packages", spark_connector_packages())
    .getOrCreate()
)
spark.stop()

jars_dir = os.path.join(os.path.dirname(pyspark.__file__), "jars")
jars = glob.glob(os.path.join(ivy_home, "jars", "*.jar"))
assert jars, "no connector JARs were resolved"
for jar in jars:
    # Ivy retrieves as "<org>_<artifact>-<rev>.jar"; strip the org prefix so the
    # bundled files use the canonical Maven name, matching the existing PySpark JARs.
    name = os.path.basename(jar)
    canonical = name.split("_", 1)[1] if "_" in name else name
    shutil.copy2(jar, os.path.join(jars_dir, canonical))
shutil.rmtree(ivy_home, ignore_errors=True)
print(f"Bundled {len(jars)} connector JARs into {jars_dir}")
PY

# Keep the venv (incl. the freshly bundled JARs) owned by the nonroot runtime user.
RUN chown -R 65532:65532 /opt/venv

USER nonroot:nonroot
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
