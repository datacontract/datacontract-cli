# using ubuntu LTS version
FROM ubuntu:22.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

 RUN apt-get update && \
     apt-get install --no-install-recommends -y python3.11 python3.11-dev python3.11-venv python3-pip python3-wheel build-essential && \
     apt-get clean && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install requirements
WORKDIR /app
COPY pyproject.toml .
COPY datacontract/ datacontract/
RUN pip3 --no-cache-dir install .

FROM ubuntu:22.04 AS runner-image

RUN apt-get update && apt-get install --no-install-recommends -y python3.11 python3.11-venv && \
   apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder-image /opt/venv /opt/venv

RUN groupadd -r datacontract
RUN useradd -r -g datacontract datacontract
USER datacontract

WORKDIR /app
RUN chown -R datacontract:datacontract /app

ENV PYTHONUNBUFFERED=1

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["datacontract"]
