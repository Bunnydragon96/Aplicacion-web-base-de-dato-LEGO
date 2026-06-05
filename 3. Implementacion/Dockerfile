# ============================================================
# LegoDB — Dockerfile
# Imagen de la capa Controlador + Vista (Flask + Jinja2)
# El DBMS MySQL corre en un contenedor separado (ver docker-compose.yml)
# ============================================================

FROM python:3.12-slim

# Variables de build (se pueden sobreescribir con --build-arg)
ARG APP_DIR=/app

WORKDIR ${APP_DIR}

# ---- Dependencias del sistema ----
# gcc puede ser necesario para compilar extensiones C de algunos paquetes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependencias Python ----
# Copiamos requirements.txt primero para aprovechar la caché de capas de Docker:
# si sólo cambia el código fuente, esta capa no se reconstruye.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Código de la aplicación ----
COPY app.py db.py etl.py schema.sql ./
COPY static/    static/
COPY templates/ templates/

# ---- Puerto expuesto por Gunicorn ----
EXPOSE 8000

# ---- Arranque con Gunicorn (servidor WSGI de producción) ----
# 2 workers síncronos son suficientes para demo/producción ligera.
# En producción aumentar workers o usar --worker-class gevent.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "app:app"]
