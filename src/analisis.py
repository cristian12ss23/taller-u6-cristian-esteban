"""Análisis reproducible del conjunto de viajes.

Lee el CSV generado, calcula un resumen por ciudad, lo persiste en Parquet y
CSV, y produce una gráfica de barras. Todas las salidas son deterministas para
una misma versión de las dependencias declaradas en requirements.txt.

Uso:
    python src/analisis.py --entrada datos/viajes.csv --salidas salidas/
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow  # noqa: E402


def huella_sha256(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def resumir(tabla: pd.DataFrame) -> pd.DataFrame:
    """Calcula medidas resumen por ciudad, ordenadas de forma determinista."""
    resumen = (
        tabla.groupby("ciudad", sort=True)
        .agg(
            n_viajes=("viaje_id", "size"),
            distancia_media_km=("distancia_km", "mean"),
            duracion_media_min=("duracion_min", "mean"),
            tarifa_media_cop=("tarifa_cop", "mean"),
            tarifa_p50_cop=("tarifa_cop", "median"),
        )
        .round(2)
        .reset_index()
    )
    return resumen


def graficar(resumen: pd.DataFrame, ruta: Path) -> None:
    """Genera la gráfica de tarifa media por ciudad sin metadatos variables."""
    figura, ejes = plt.subplots(figsize=(8, 4.5))
    ejes.bar(resumen["ciudad"], resumen["tarifa_media_cop"], color="#1f4e79")
    ejes.set_title("Tarifa media por ciudad (COP)")
    ejes.set_ylabel("COP")
    ejes.set_xlabel("Ciudad")
    figura.tight_layout()
    figura.savefig(ruta, dpi=100, metadata={"Software": None})
    plt.close(figura)


def principal() -> None:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--entrada", type=Path, default=Path("datos/viajes.csv"))
    analizador.add_argument("--salidas", type=Path, default=Path("salidas"))
    argumentos = analizador.parse_args()
    argumentos.salidas.mkdir(parents=True, exist_ok=True)

    tabla = pd.read_csv(argumentos.entrada, parse_dates=["fecha_hora"])
    resumen = resumir(tabla)

    ruta_parquet = argumentos.salidas / "resumen_ciudad.parquet"
    ruta_csv = argumentos.salidas / "resumen_ciudad.csv"
    ruta_png = argumentos.salidas / "tarifa_media_ciudad.png"
    ruta_manifiesto = argumentos.salidas / "manifiesto.json"

    resumen.to_parquet(ruta_parquet, index=False, engine="pyarrow")
    resumen.to_csv(ruta_csv, index=False, lineterminator="\n")
    graficar(resumen, ruta_png)

    manifiesto = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
        "matplotlib": matplotlib.__version__,
        "filas_entrada": int(len(tabla)),
        "huellas": {
            ruta.name: huella_sha256(ruta) for ruta in (ruta_parquet, ruta_csv, ruta_png)
        },
    }
    ruta_manifiesto.write_text(json.dumps(manifiesto, indent=2, sort_keys=True) + "\n")

    print(resumen.to_string(index=False))
    print()
    for nombre, huella in manifiesto["huellas"].items():
        print(f"{huella}  {nombre}")


if __name__ == "__main__":
    principal()
