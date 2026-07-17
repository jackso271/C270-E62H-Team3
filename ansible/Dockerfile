FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        docker-cli \
    && pip install --no-cache-dir \
        ansible-core==2.19.4 \
        docker==7.1.0 \
    && ansible-galaxy collection install community.docker:4.7.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["ansible-playbook", "--version"]
