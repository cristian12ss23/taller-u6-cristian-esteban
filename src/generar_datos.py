"""Generación reproducible del conjunto de datos de viajes.

Produce un archivo CSV con registros sintéticos de viajes urbanos. La semilla
fija garantiza que cada ejecución genere exactamente los mismos registros,
condición necesaria para verificar la reproducibilidad del análisis.

Uso:
    python src/generar_datos.py --filas 50000 --salida datos/viajes.csv
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 20260917
CIUDADES = ["Bogota", "Medellin", "Cali", "Barranquilla", "Bucaramanga"]
PESOS_CIUDAD = [0.45, 0.20, 0.15, 0.12, 0.08]
FECHA_INICIO = "2026-08-01"


def generar(filas: int) -> pd.DataFrame:
    """Construye el DataFrame sintético con la semilla fija del curso."""
    generador = np.random.default_rng(SEMILLA)
    inicio = pd.Timestamp(FECHA_INICIO)
    desplazamiento_seg = generador.integers(0, 31 * 24 * 3600, size=filas)
    distancia_km = np.round(generador.gamma(shape=2.0, scale=3.0, size=filas), 2)
    duracion_min = np.round(distancia_km * generador.uniform(2.0, 4.0, size=filas), 1)
    tarifa = np.round(3500 + distancia_km * 1800 + duracion_min * 120, 0)
    tabla = pd.DataFrame(
        {
            "viaje_id": np.arange(1, filas + 1, dtype="int64"),
            "fecha_hora": inicio + pd.to_timedelta(desplazamiento_seg, unit="s"),
            "ciudad": generador.choice(CIUDADES, size=filas, p=PESOS_CIUDAD),
            "distancia_km": distancia_km,
            "duracion_min": duracion_min,
            "tarifa_cop": tarifa.astype("int64"),
        }
    )
    return tabla


def huella_sha256(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def principal() -> None:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--filas", type=int, default=50_000)
    analizador.add_argument("--salida", type=Path, default=Path("datos/viajes.csv"))
    argumentos = analizador.parse_args()

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    tabla = generar(argumentos.filas)
    tabla.to_csv(argumentos.salida, index=False, lineterminator="\n")
    print(f"Filas generadas : {len(tabla)}")
    print(f"Archivo         : {argumentos.salida}")
    print(f"SHA-256         : {huella_sha256(argumentos.salida)}")


if __name__ == "__main__":
    principal()
