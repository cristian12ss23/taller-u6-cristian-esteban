#!/bin/sh
# Punto de entrada del contenedor: descarga y análisis, en ese orden.
set -eu                                               # Detiene el script ante cualquier error

echo "== Etapa 1. Descarga de datos (periodo ${PERIODO}) =="   # Encabezado de la etapa 1
python src/descargar.py --periodo "${PERIODO}"        # Descarga el periodo (o reutiliza el CSV ya descargado)

echo                                                  # Línea en blanco
echo "== Etapa 2. Análisis rural vs urbano =="          # Encabezado de la etapa 2
python src/analisis.py --periodo "${PERIODO}"         # Calcula tablas, prueba, gráficas y manifiesto
