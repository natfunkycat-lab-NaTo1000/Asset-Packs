FROM python:3.11.9-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends make ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN python -m venv /workspace/.venv && \
    /workspace/.venv/bin/pip install --no-cache-dir -r /workspace/requirements.txt

COPY . /workspace

ENV PATH="/workspace/.venv/bin:${PATH}"

CMD ["make", "dist"]
