# Imagem base Python — equivalente a ter o PHP-FPM no container
FROM python:3.12-slim

WORKDIR /app

# Dependências primeiro (cache de build do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY app ./app

# Uvicorn = "php-fpm" + "public/index.php" recebendo HTTP
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
