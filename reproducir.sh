#!/bin/sh
# Construye la imagen, ejecuta el análisis dos veces en contenedores independientes
# y verifica que las huellas SHA-256 de las salidas coincidan.
# Uso: ./reproducir.sh
set -eu

IMAGEN="lab05-viajes:1.0"

echo "== Construcción de la imagen ${IMAGEN} =="
docker build --tag "${IMAGEN}" .

rm -rf salidas_a salidas_b
mkdir -p salidas_a salidas_b

echo
echo "== Corrida A =="
docker run --rm --volume "$(pwd)/salidas_a:/app/salidas" "${IMAGEN}"

echo
echo "== Corrida B =="
docker run --rm --volume "$(pwd)/salidas_b:/app/salidas" "${IMAGEN}"

echo
echo "== Verificación de reproducibilidad =="
python3 src/verificar.py salidas_a/manifiesto.json salidas_b/manifiesto.json
