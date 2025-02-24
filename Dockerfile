FROM python:3.11-bullseye

# Setting PYTHONUNBUFFERED to a non-empty value different from 0 ensures that the python output i.e.
# the stdout and stderr streams are sent straight to terminal (e.g. your container log) without
# being first buffered and that you can see the output of your application in real time.
ENV PYTHONUNBUFFERED=1

# copy resources
COPY pyproject.toml /app/.
COPY MANIFEST.in /app/.
COPY datacontract/ /app/datacontract/

# install requirements
RUN cd /app && pip3 --no-cache-dir install ".[all]"

# install duckdb httpfs extension
RUN python -c "import duckdb; duckdb.connect().sql(\"INSTALL httpfs\");"

RUN mkdir -p /home/datacontract
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
