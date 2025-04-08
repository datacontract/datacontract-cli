FROM python:3.11-bullseye

# Setting PYTHONUNBUFFERED to a non-empty value different from 0 ensures that the python output i.e.
# the stdout and stderr streams are sent straight to terminal (e.g. your container log) without
# being first buffered and that you can see the output of your application in real time.
ENV PYTHONUNBUFFERED=1

# Compiling Python source files to bytecode is typically desirable for production images as it tends
# to improve startup time (at the cost of increased installation time).
ENV UV_COMPILE_BYTECODE=1

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.9 /uv /uvx /bin/

# copy resources
COPY pyproject.toml /app/.
COPY MANIFEST.in /app/.
COPY datacontract/ /app/datacontract/

# install requirements
RUN cd /app && uv pip --no-cache-dir install --system ".[all]"

RUN mkdir -p /home/datacontract
WORKDIR /home/datacontract

ENTRYPOINT ["datacontract"]
