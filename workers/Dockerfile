FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY workers/requirements.txt workers/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r workers/requirements.txt

COPY .utils .utils
COPY workers workers

ENV REPO_ROOT=/workspace

CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info", "--queues=conductor"]
