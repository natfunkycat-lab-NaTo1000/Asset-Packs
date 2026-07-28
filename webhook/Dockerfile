FROM python:3.11-slim

WORKDIR /app

COPY webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webhook/ webhook/
COPY workers/ workers/

CMD ["uvicorn", "webhook.main:app", "--host", "0.0.0.0", "--port", "8000"]
