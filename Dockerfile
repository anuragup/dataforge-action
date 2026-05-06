FROM python:3.11-slim

LABEL maintainer="DataForge"
LABEL description="Data quality checking GitHub Action"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN chmod +x src/main.py

ENTRYPOINT ["python", "/app/src/main.py"]
