FROM python:3.11-slim

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY app/ ./app/
COPY .env .
COPY google_credentials.json .

# Puerto
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
