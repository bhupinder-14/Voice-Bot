# FROM alpine:3.21.3
FROM debian:bookworm-slim
# RUN apk add --no-cache python3 py3-pip
RUN apt update
RUN apt install python3 python3-pip curl -y
COPY requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r /app/requirements.txt --break-system-packages

RUN curl -sSL https://get.livekit.io/cli | bash

WORKDIR /app

COPY dispatch-rule.json /app
COPY inbound-trunk.json /app


COPY decent-habitat-448415-n4-4df16195de3a.json /app
COPY .env.local /app
COPY info.py /app
COPY agent.py /app
COPY silence.py /app
COPY gemini.py /app
COPY setup.sh /app
RUN chmod +x /app/setup.sh
RUN python3 agent.py download-files