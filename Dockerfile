FROM python:3.11-bullseye AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

# create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install requirements
WORKDIR /app
COPY pyproject.toml .
COPY MANIFEST.in .
COPY datacontract/ datacontract/
RUN pip3 --no-cache-dir install ".[all]"
RUN python -c "import duckdb; duckdb.connect().sql(\"INSTALL httpfs\");"

FROM python:3.11-bullseye AS runner-image

COPY --from=builder-image /opt/venv /opt/venv

# RUN groupadd -r datacontract
# RUN useradd -r --home /home/datacontract -g datacontract datacontract
# USER datacontract
# WORKDIR /home/datacontract

# Setting PYTHONUNBUFFERED to a non-empty value different from 0 ensures that the python output i.e.
# the stdout and stderr streams are sent straight to terminal (e.g. your container log) without
# being first buffered and that you can see the output of your application in real time.
ENV PYTHONUNBUFFERED=1

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["datacontract"]
