FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala (.dockerignore ile .env, .git, *.db vb. dışarıda tutulur)
COPY . .

# Root olmayan kullanıcıyla çalıştır
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# FastAPI portu
EXPOSE 8000

# Coolify / Docker konteyner içinde 0.0.0.0 adresini dinlemek zorundadır.
# --proxy-headers: Coolify'ın reverse proxy'si (Traefik) arkasında gerçek istemci IP'si ve https şeması doğru okunur.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]