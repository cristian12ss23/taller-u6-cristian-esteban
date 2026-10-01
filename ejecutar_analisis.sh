#!/bin/sh
# Punto de entrada del contenedor: genera el conjunto de datos y ejecuta el análisis.
# Uso dentro del contenedor: ./ejecutar_analisis.sh [--filas N]
set -eu

FILAS=50000
while [ $# -gt 0 ]; do
    case "$1" in
        --filas) FILAS="$2"; shift 2 ;;
        *) echo "Argumento no reconocido: $1" >&2; exit 2 ;;
    esac
done

echo "== Etapa 1. Generación de datos (${FILAS} filas) =="
python src/generar_datos.py --filas "${FILAS}" --salida datos/viajes.csv
echo
echo "== Etapa 2. Análisis y persistencia de salidas =="
python src/analisis.py --entrada datos/viajes.csv --salidas salidas
