"""Compara la brecha rural vs urbana entre dos periodos de Saber 11.

Lee las salidas que analisis.py dejó en salidas/<periodo> para cada periodo,
arma tablas con la brecha de ambos años lado a lado, dibuja dos gráficas y
escribe un manifiesto con las huellas SHA-256.
Uso: python src/comparar.py --antes 20194 --despues 20224
"""

import argparse  # Lee los argumentos de la línea de comandos
import hashlib  # Calcula las huellas SHA-256
import json  # Lee la prueba estadística y escribe el manifiesto
import sys  # Da acceso al código de salida del programa
from pathlib import Path  # Maneja rutas de archivos

import matplotlib  # Biblioteca de gráficas
matplotlib.use("Agg")  # Dibuja sin pantalla (necesario dentro del contenedor)
import matplotlib.pyplot as plt  # Interfaz para crear las figuras
import numpy as np  # Cálculos numéricos
import pandas as pd  # Manejo de tablas

AREAS = {  # Columnas de media por área (como quedaron en resumen_zona.csv) y su nombre legible
    "media_matematicas": "Matemáticas",  # Matemáticas
    "media_lectura_critica": "Lectura crítica",  # Lectura crítica
    "media_c_naturales": "C. naturales",  # Ciencias naturales
    "media_sociales_ciudadanas": "Sociales",  # Sociales y ciudadanas
    "media_ingles": "Inglés",  # Inglés
}
TINTA = "#0b0b0b"  # Color del texto principal
TINTA_2 = "#52514e"  # Color del texto secundario
REJILLA = "#e4e3df"  # Color de las líneas de referencia
FONDO = "#fcfcfb"  # Color de fondo
COLOR_ANTES = "#6250d6"  # Violeta para el periodo anterior (distinto de los colores de zona)
COLOR_DESPUES = "#1baf7a"  # Verde agua para el periodo posterior
COLOR_CAMBIO = "#2a78d6"  # Azul para la gráfica de cambio por departamento


def huella(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()  # Lee el archivo completo y devuelve su huella


def estilo(eje) -> None:
    """Aplica el estilo común de las gráficas."""
    eje.set_facecolor(FONDO)  # Fondo del área de dibujo
    for lado in ("top", "right"):  # Bordes superior y derecho
        eje.spines[lado].set_visible(False)  # Se ocultan
    for lado in ("left", "bottom"):  # Bordes izquierdo e inferior
        eje.spines[lado].set_color(REJILLA)  # Se dibujan en gris suave
    eje.tick_params(colors=TINTA_2, labelsize=9)  # Marcas de los ejes en gris
    eje.set_axisbelow(True)  # La rejilla queda detrás de los datos


def guardar(figura, ruta: Path) -> None:
    """Guarda la figura en PNG sin metadatos variables."""
    figura.savefig(ruta, dpi=150, facecolor=FONDO, metadata={"Software": None})  # Huella estable
    plt.close(figura)  # Libera memoria


def tabla_zona(base: Path, periodos: list[str]) -> pd.DataFrame:
    """Arma una tabla con media urbana, media rural y brecha del global y de cada área, para cada periodo."""
    filas = []  # Lista de filas de la tabla final
    for periodo in periodos:  # Recorre los dos periodos
        resumen = pd.read_csv(base / periodo / "resumen_zona.csv").set_index("zona")  # Resumen del periodo
        for columna in ["media_global", *AREAS]:  # Global y cada área
            filas.append({  # Agrega una fila
                "periodo": periodo,  # Periodo
                "medida": columna.removeprefix("media_"),  # Nombre corto de la medida
                "urbano": resumen.loc["URBANO", columna],  # Media urbana
                "rural": resumen.loc["RURAL", columna],  # Media rural
                "brecha": resumen.loc["BRECHA (U-R)", columna],  # Brecha urbano menos rural
            })
    return pd.DataFrame(filas)  # Devuelve la tabla


def lado_a_lado(base: Path, archivo: str, clave: str, antes: str, despues: str) -> pd.DataFrame:
    """Une la brecha de los dos periodos para cada grupo (tipo de colegio o departamento) y calcula el cambio."""
    a = pd.read_csv(base / antes / archivo)[[clave, "brecha"]]  # Brecha del periodo anterior
    d = pd.read_csv(base / despues / archivo)[[clave, "brecha"]]  # Brecha del periodo posterior
    union = a.merge(d, on=clave, how="inner", suffixes=(f"_{antes}", f"_{despues}"))  # Solo grupos presentes en ambos
    union["cambio"] = (union[f"brecha_{despues}"] - union[f"brecha_{antes}"]).round(2)  # Positivo: la brecha creció
    return union.sort_values("cambio", ascending=False, kind="mergesort").reset_index(drop=True)  # Mayor aumento primero


def grafica_areas(zona: pd.DataFrame, ruta: Path, antes: str, despues: str) -> None:
    """Barras agrupadas con la brecha de cada área en los dos periodos."""
    figura, eje = plt.subplots(figsize=(8, 4.5), facecolor=FONDO)  # Crea la figura
    posiciones = np.arange(len(AREAS))  # Posición de cada área
    ancho = 0.38  # Ancho de cada barra
    for i, (periodo, color) in enumerate([(antes, COLOR_ANTES), (despues, COLOR_DESPUES)]):  # Un grupo por periodo
        datos = zona[zona["periodo"] == periodo].set_index("medida")  # Filas del periodo
        valores = [datos.loc[c.removeprefix("media_"), "brecha"] for c in AREAS]  # Brecha por área
        barras = eje.bar(posiciones + (i - 0.5) * (ancho + 0.02), valores, width=ancho, color=color, label=periodo)  # Barras
        eje.bar_label(barras, fmt="%.1f", fontsize=8, color=TINTA_2, padding=2)  # Valor encima de cada barra
    estilo(eje)  # Estilo común
    eje.grid(axis="y", color=REJILLA, linewidth=0.8)  # Rejilla horizontal
    eje.set_ylim(min(0, zona["brecha"].min() * 1.3), zona.loc[zona["medida"] != "global", "brecha"].max() * 1.3)  # Espacio arriba para la leyenda
    eje.set_xticks(posiciones, list(AREAS.values()))  # Nombres de las áreas
    eje.set_ylabel("Brecha urbano − rural (puntos)", color=TINTA_2)  # Eje vertical
    eje.set_title(f"Brecha urbano − rural por área: {antes} vs {despues}", color=TINTA, loc="left")  # Título
    eje.legend(frameon=False, labelcolor=TINTA, ncol=2, loc="upper left")  # Leyenda en una fila, arriba a la izquierda
    figura.tight_layout()  # Ajusta márgenes
    guardar(figura, ruta)  # Guarda


def grafica_departamentos(deptos: pd.DataFrame, ruta: Path, antes: str, despues: str) -> None:
    """Barras horizontales con el cambio de la brecha de cada departamento."""
    datos = deptos.sort_values("cambio", kind="mergesort")  # Mayor aumento arriba
    figura, eje = plt.subplots(figsize=(8, max(4, 0.28 * len(datos))), facecolor=FONDO)  # Alto según departamentos
    eje.barh(datos["cole_depto_ubicacion"].str.title(), datos["cambio"], color=COLOR_CAMBIO, height=0.7)  # Barras
    estilo(eje)  # Estilo común
    eje.grid(axis="x", color=REJILLA, linewidth=0.8)  # Rejilla vertical
    eje.axvline(0, color=TINTA_2, linewidth=1)  # Cero: a la derecha la brecha creció, a la izquierda se redujo
    eje.set_xlabel(f"Cambio de la brecha en puntaje global ({despues} − {antes})", color=TINTA_2)  # Eje horizontal
    eje.set_title(f"¿Creció la brecha rural? Cambio por departamento, {antes} → {despues}", color=TINTA, loc="left")  # Título
    eje.tick_params(axis="y", labelsize=8)  # Nombres en letra pequeña
    figura.tight_layout()  # Ajusta márgenes
    guardar(figura, ruta)  # Guarda


def main() -> int:
    """Ejecuta la comparación y escribe sus salidas."""
    lector = argparse.ArgumentParser(description=__doc__)  # Lector de argumentos
    lector.add_argument("--antes", default="20194")  # Periodo anterior
    lector.add_argument("--despues", default="20224")  # Periodo posterior
    lector.add_argument("--salidas", default="salidas")  # Carpeta base de salidas
    args = lector.parse_args()  # Lee los argumentos

    base = Path(args.salidas)  # Carpeta donde están las salidas de cada periodo
    carpeta = base / "comparacion"  # Carpeta de salida de la comparación
    carpeta.mkdir(parents=True, exist_ok=True)  # La crea si no existe
    periodos = [args.antes, args.despues]  # Los dos periodos en orden

    zona = tabla_zona(base, periodos)  # Brecha global y por área de ambos periodos
    naturaleza = lado_a_lado(base, "brecha_naturaleza.csv", "cole_naturaleza", args.antes, args.despues)  # Por tipo de colegio
    deptos = lado_a_lado(base, "brecha_departamento.csv", "cole_depto_ubicacion", args.antes, args.despues)  # Por departamento
    pruebas = {p: json.loads((base / p / "prueba_estadistica.json").read_text(encoding="utf-8")) for p in periodos}  # Pruebas t

    zona.to_csv(carpeta / "comparacion_zona.csv", index=False, lineterminator="\n")  # Guarda la tabla por zona
    naturaleza.to_csv(carpeta / "comparacion_naturaleza.csv", index=False, lineterminator="\n")  # Guarda por tipo de colegio
    deptos.to_csv(carpeta / "comparacion_departamento.csv", index=False, lineterminator="\n")  # Guarda por departamento
    grafica_areas(zona, carpeta / "brecha_por_area_periodos.png", args.antes, args.despues)  # Gráfica de áreas
    grafica_departamentos(deptos, carpeta / "cambio_departamento.png", args.antes, args.despues)  # Gráfica de departamentos

    pd.set_option("display.width", 200)  # Ancho de impresión
    print(f"== Comparación {args.antes} vs {args.despues} ==")  # Encabezado
    print("\n-- Brecha global y por área --")  # Título
    print(zona.pivot(index="medida", columns="periodo", values="brecha").to_string())  # Brecha por medida y periodo
    print("\n-- Medias del puntaje global --")  # Título
    print(zona[zona["medida"] == "global"].to_string(index=False))  # Medias urbana y rural del global
    print("\n-- Prueba estadística por periodo --")  # Título
    for p in periodos:  # Recorre los periodos
        t = pruebas[p]  # Resultado de la prueba del periodo
        print(f"{p}: brecha {t['diferencia_medias']} (IC95 {t['ic95_inferior']} a {t['ic95_superior']}), "  # Brecha e intervalo
              f"d de Cohen {t['d_cohen']}, n urbano {t['n_urbano']:,}, n rural {t['n_rural']:,}")  # Efecto y tamaños
    print("\n-- Brecha por tipo de colegio --")  # Título
    print(naturaleza.to_string(index=False))  # Tabla por tipo de colegio
    print("\n-- Departamentos donde más creció y más se redujo la brecha --")  # Título
    print(pd.concat([deptos.head(5), deptos.tail(5)]).to_string(index=False))  # Extremos
    print(f"\nDepartamentos donde la brecha creció: {(deptos['cambio'] > 0).sum()} de {len(deptos)}")  # Conteo

    nombres = sorted(p.name for p in carpeta.iterdir() if p.is_file() and p.name != "manifiesto.json")  # Salidas
    manifiesto = {  # Contenido del manifiesto
        "antes": args.antes,  # Periodo anterior
        "despues": args.despues,  # Periodo posterior
        "huellas": {n: huella(carpeta / n) for n in nombres},  # Huella de cada salida
        "pandas": pd.__version__,  # Versión de pandas
        "matplotlib": matplotlib.__version__,  # Versión de matplotlib
    }
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2) + "\n", encoding="utf-8")  # Guarda
    print("\n-- Huellas SHA-256 --")  # Título
    for nombre, valor in manifiesto["huellas"].items():  # Recorre las salidas
        print(f"{valor}  {nombre}")  # Imprime la huella
    return 0  # Termina sin error


if __name__ == "__main__":  # Solo si el archivo se corre directamente
    sys.exit(main())  # Ejecuta main
