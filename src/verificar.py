"""Comparación de dos ejecuciones del análisis.

Compara los manifiestos producidos por dos corridas independientes y declara
si las huellas SHA-256 de todas las salidas coinciden. Devuelve código de
salida 0 si la reproducción es exacta y 1 en caso contrario.

Uso:
    python src/verificar.py salidas_a/manifiesto.json salidas_b/manifiesto.json
"""

import json
import sys
from pathlib import Path


def principal(ruta_a: Path, ruta_b: Path) -> int:
    manifiesto_a = json.loads(ruta_a.read_text())
    manifiesto_b = json.loads(ruta_b.read_text())
    huellas_a = manifiesto_a["huellas"]
    huellas_b = manifiesto_b["huellas"]
    nombres = sorted(set(huellas_a) | set(huellas_b))
    coincidencias = 0
    for nombre in nombres:
        iguales = huellas_a.get(nombre) == huellas_b.get(nombre)
        coincidencias += int(iguales)
        estado = "IDENTICO" if iguales else "DIFIERE"
        print(f"{estado:9} {nombre}")
    print()
    if coincidencias == len(nombres):
        print(f"Reproducción exacta: {len(nombres)} de {len(nombres)} salidas coinciden.")
        return 0
    print(f"Reproducción fallida: {coincidencias} de {len(nombres)} salidas coinciden.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python src/verificar.py <manifiesto_a> <manifiesto_b>")
        sys.exit(2)
    sys.exit(principal(Path(sys.argv[1]), Path(sys.argv[2])))
