# Imagen del laboratorio 5: análisis reproducible de viajes.
# Base fijada por etiqueta; para fijación estricta se recomienda añadir el
# digest de la imagen (python:3.12-slim-bookworm@sha256:...), obtenido con
# docker pull y docker inspect en el momento de la construcción de referencia.
FROM python:3.12-slim-bookworm

# Variables de entorno: sin archivos .pyc, salida sin búfer y sin caché de pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib

# Usuario sin privilegios para la ejecución del análisis (principio de privilegio mínimo).
RUN groupadd --gid 1000 analista \
    && useradd --uid 1000 --gid analista --create-home analista

WORKDIR /app

# Primero las dependencias: esta capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código fuente y el punto de entrada.
COPY src/ ./src/
COPY ejecutar_analisis.sh .
RUN chmod +x ejecutar_analisis.sh \
    && mkdir -p /app/datos /app/salidas \
    && chown -R analista:analista /app

USER analista

# Punto de entrada: genera los datos y ejecuta el análisis.
# Los argumentos adicionales se transmiten al script (por ejemplo, --filas 10000).
ENTRYPOINT ["./ejecutar_analisis.sh"]
