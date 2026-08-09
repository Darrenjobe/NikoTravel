FROM python:3.12-slim

WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY knowledge ./knowledge

ENV KNOWLEDGE_DIR=/srv/knowledge \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
