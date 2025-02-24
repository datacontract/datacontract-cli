FROM python:3.11-bullseye

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

# create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

# Setting PYTHONUNBUFFERED to a non-empty value different from 0 ensures that the python output i.e.
# the stdout and stderr streams are sent straight to terminal (e.g. your container log) without
# being first buffered and that you can see the output of your application in real time.
ENV PYTHONUNBUFFERED=1

# install requirements
COPY pyproject.toml /app/.
COPY MANIFEST.in /app/.
COPY datacontract/ /app/datacontract/
RUN cd /app && pip3 --no-cache-dir install ".[all]"
RUN python -c "import duckdb; duckdb.connect().sql(\"INSTALL httpfs\");"

ENTRYPOINT ["datacontract"]
