FROM python:3.11-slim

WORKDIR /app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# FastAPI portu
EXPOSE 8000

# Coolify / Docker konteyner içinde 0.0.0.0 adresini dinlemek zorundadır
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]