# Imagen del proyecto: comparación rural vs urbano en Saber 11.
# Base fijada por etiqueta, igual que en el laboratorio 5.
FROM python:3.12-slim-bookworm

# Sin archivos .pyc, salida sin búfer, sin caché de pip, carpeta de matplotlib escribible
# y periodo por defecto (se puede cambiar con: docker run -e PERIODO=20194 ...).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    PERIODO=20224

# Usuario sin privilegios (principio de privilegio mínimo).
RUN groupadd --gid 1000 analista \
    && useradd --uid 1000 --gid analista --create-home analista

WORKDIR /app

# Primero las dependencias: esta capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código y el punto de entrada.
COPY src/ ./src/
COPY ejecutar.sh .
RUN chmod +x ejecutar.sh \
    && mkdir -p /app/datos /app/salidas \
    && chown -R analista:analista /app

USER analista

# Descarga los datos (si no existen) y ejecuta el análisis.
ENTRYPOINT ["./ejecutar.sh"]
