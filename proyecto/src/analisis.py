"""Compara los resultados de Saber 11 entre colegios rurales y urbanos.

Lee el CSV descargado por descargar.py, calcula la brecha urbano - rural en el
puntaje global y por áreas, la desglosa por tipo de colegio, estrato y
departamento, aplica una prueba estadística, dibuja tres gráficas y escribe un
manifiesto con la huella SHA-256 de cada salida.
Uso: python src/analisis.py --periodo 20224
"""

import argparse  # Lee los argumentos de la línea de comandos
import hashlib  # Calcula las huellas SHA-256
import json  # Escribe el manifiesto y la prueba estadística en formato JSON
import platform  # Obtiene la versión de Python para el manifiesto
import sys  # Da acceso al código de salida del programa
from pathlib import Path  # Maneja rutas de archivos

import matplotlib  # Biblioteca de gráficas
matplotlib.use("Agg")  # Dibuja sin pantalla (necesario dentro del contenedor)
import matplotlib.pyplot as plt  # Interfaz para crear las figuras
import numpy as np  # Cálculos numéricos
import pandas as pd  # Manejo de tablas
import pyarrow  # Motor para escribir Parquet (se importa para registrar su versión)
import scipy  # Biblioteca científica (se importa para registrar su versión)
from scipy import stats  # Prueba t de Welch y distribución t

AREAS = {  # Columnas de puntaje por área y su nombre legible
    "punt_matematicas": "Matemáticas",  # Área de matemáticas
    "punt_lectura_critica": "Lectura crítica",  # Área de lectura crítica
    "punt_c_naturales": "C. naturales",  # Área de ciencias naturales
    "punt_sociales_ciudadanas": "Sociales",  # Área de sociales y ciudadanas
    "punt_ingles": "Inglés",  # Área de inglés
}
PUNTAJES = ["punt_global", *AREAS]  # Todas las columnas de puntaje
ZONAS = ["URBANO", "RURAL"]  # Las dos zonas que se comparan, en orden fijo
MIN_RURAL_DEPTO = 100  # Mínimo de estudiantes rurales para incluir un departamento

COLOR = {"URBANO": "#2a78d6", "RURAL": "#eb6834"}  # Azul para urbano, naranja para rural (paleta validada)
TINTA = "#0b0b0b"  # Color del texto principal
TINTA_2 = "#52514e"  # Color del texto secundario (ejes y notas)
REJILLA = "#e4e3df"  # Color suave de las líneas de referencia
FONDO = "#fcfcfb"  # Color de fondo de las gráficas


def huella(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    sha = hashlib.sha256()  # Crea el calculador de la huella
    with ruta.open("rb") as archivo:  # Abre el archivo en modo binario
        for bloque in iter(lambda: archivo.read(1 << 20), b""):  # Lee en bloques de 1 MB
            sha.update(bloque)  # Agrega el bloque al cálculo
    return sha.hexdigest()  # Devuelve la huella en hexadecimal


def cargar(ruta: Path) -> pd.DataFrame:
    """Lee el CSV, convierte los puntajes a números y limpia los registros inválidos."""
    tabla = pd.read_csv(ruta, dtype=str)  # Lee todo como texto para controlar la conversión
    for columna in PUNTAJES:  # Recorre cada columna de puntaje
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")  # Convierte a número; lo inválido queda vacío
    tabla["zona"] = tabla["cole_area_ubicacion"].str.strip().str.upper()  # Normaliza la zona a mayúsculas sin espacios
    tabla = tabla[tabla["zona"].isin(ZONAS)]  # Conserva solo URBANO y RURAL
    tabla = tabla[tabla["punt_global"].between(0, 500)]  # Conserva puntajes globales en el rango válido
    return tabla.reset_index(drop=True)  # Devuelve la tabla limpia con índice nuevo


def resumen_zona(tabla: pd.DataFrame) -> pd.DataFrame:
    """Calcula conteo, media, mediana y desviación del global, y la media por área, para cada zona."""
    grupos = tabla.groupby("zona")  # Agrupa los estudiantes por zona
    resumen = pd.DataFrame({  # Arma la tabla de resumen
        "n_estudiantes": grupos.size(),  # Número de estudiantes por zona
        "media_global": grupos["punt_global"].mean(),  # Promedio del puntaje global
        "mediana_global": grupos["punt_global"].median(),  # Mediana del puntaje global
        "de_global": grupos["punt_global"].std(),  # Desviación estándar del puntaje global
    })
    for columna in AREAS:  # Recorre cada área
        resumen[f"media_{columna.removeprefix('punt_')}"] = grupos[columna].mean()  # Promedio del área por zona
    resumen = resumen.reindex(ZONAS)  # Ordena las filas: primero URBANO, luego RURAL
    resumen.loc["BRECHA (U-R)"] = resumen.loc["URBANO"] - resumen.loc["RURAL"]  # Agrega la fila con la diferencia
    resumen.loc["BRECHA (U-R)", "n_estudiantes"] = np.nan  # La resta de conteos no tiene sentido; se deja vacía
    resumen = resumen.round(2)  # Redondea a 2 decimales
    resumen["n_estudiantes"] = resumen["n_estudiantes"].astype("Int64")  # Conteo como entero (admite el vacío de la brecha)
    return resumen.rename_axis("zona").reset_index()  # Deja la zona como columna


def brecha_por(tabla: pd.DataFrame, columna: str, minimo: int = 1) -> pd.DataFrame:
    """Calcula la media global urbana y rural, y su brecha, para cada valor de una columna."""
    conteo = tabla.pivot_table(index=columna, columns="zona", values="punt_global", aggfunc="size")  # Estudiantes por grupo y zona
    media = tabla.pivot_table(index=columna, columns="zona", values="punt_global", aggfunc="mean")  # Media global por grupo y zona
    salida = pd.DataFrame({  # Arma la tabla de brechas
        "n_urbano": conteo.get("URBANO"),  # Estudiantes urbanos del grupo
        "n_rural": conteo.get("RURAL"),  # Estudiantes rurales del grupo
        "media_urbano": media.get("URBANO"),  # Media global urbana del grupo
        "media_rural": media.get("RURAL"),  # Media global rural del grupo
    })
    salida["brecha"] = salida["media_urbano"] - salida["media_rural"]  # Diferencia urbano menos rural
    salida = salida[salida["n_rural"].fillna(0) >= minimo]  # Descarta grupos con muy pocos estudiantes rurales
    salida = salida.dropna(subset=["brecha"])  # Descarta grupos sin una de las dos zonas
    salida = salida.sort_values("brecha", ascending=False, kind="mergesort")  # Ordena de mayor a menor brecha
    salida[["n_urbano", "n_rural"]] = salida[["n_urbano", "n_rural"]].astype(int)  # Conteos como enteros
    return salida.round(2).rename_axis(columna).reset_index()  # Redondea y deja el grupo como columna


def prueba_estadistica(tabla: pd.DataFrame) -> dict:
    """Aplica la prueba t de Welch y calcula el tamaño del efecto (d de Cohen)."""
    urbano = tabla.loc[tabla["zona"] == "URBANO", "punt_global"].to_numpy(float)  # Puntajes urbanos
    rural = tabla.loc[tabla["zona"] == "RURAL", "punt_global"].to_numpy(float)  # Puntajes rurales
    diferencia = urbano.mean() - rural.mean()  # Diferencia de medias
    var_u, var_r = urbano.var(ddof=1), rural.var(ddof=1)  # Varianzas muestrales de cada grupo
    n_u, n_r = len(urbano), len(rural)  # Tamaños de cada grupo
    error = np.sqrt(var_u / n_u + var_r / n_r)  # Error estándar de la diferencia (Welch)
    gl = (var_u / n_u + var_r / n_r) ** 2 / ((var_u / n_u) ** 2 / (n_u - 1) + (var_r / n_r) ** 2 / (n_r - 1))  # Grados de libertad de Welch
    t, p = stats.ttest_ind(urbano, rural, equal_var=False)  # Prueba t de Welch (no supone varianzas iguales)
    margen = stats.t.ppf(0.975, gl) * error  # Margen del intervalo de confianza del 95 %
    de_combinada = np.sqrt(((n_u - 1) * var_u + (n_r - 1) * var_r) / (n_u + n_r - 2))  # Desviación estándar combinada
    return {  # Devuelve los resultados redondeados
        "prueba": "t de Welch, puntaje global, URBANO vs RURAL",  # Nombre de la prueba
        "n_urbano": int(n_u),  # Tamaño del grupo urbano
        "n_rural": int(n_r),  # Tamaño del grupo rural
        "diferencia_medias": round(float(diferencia), 2),  # Brecha en puntos
        "ic95_inferior": round(float(diferencia - margen), 2),  # Límite inferior del intervalo
        "ic95_superior": round(float(diferencia + margen), 2),  # Límite superior del intervalo
        "t": round(float(t), 2),  # Estadístico t
        "grados_libertad": round(float(gl), 1),  # Grados de libertad
        "p_valor": float(f"{p:.3g}"),  # Valor p con 3 cifras significativas
        "d_cohen": round(float(diferencia / de_combinada), 3),  # Tamaño del efecto
    }


def estilo(eje) -> None:
    """Aplica el estilo común: fondo claro, ejes discretos y rejilla suave."""
    eje.set_facecolor(FONDO)  # Fondo del área de dibujo
    for lado in ("top", "right"):  # Bordes superior y derecho
        eje.spines[lado].set_visible(False)  # Se ocultan para una gráfica más limpia
    for lado in ("left", "bottom"):  # Bordes izquierdo e inferior
        eje.spines[lado].set_color(REJILLA)  # Se dibujan en gris suave
    eje.tick_params(colors=TINTA_2, labelsize=9)  # Marcas y números de los ejes en gris
    eje.grid(axis="y", color=REJILLA, linewidth=0.8)  # Líneas horizontales de referencia
    eje.set_axisbelow(True)  # La rejilla queda detrás de los datos


def guardar(figura, ruta: Path) -> None:
    """Guarda la figura en PNG sin metadatos variables, para que su huella sea estable."""
    figura.savefig(ruta, dpi=150, facecolor=FONDO, metadata={"Software": None})  # Sin la versión de software en el archivo
    plt.close(figura)  # Libera la memoria de la figura


def grafica_distribucion(tabla: pd.DataFrame, ruta: Path, periodo: str) -> None:
    """Dibuja la distribución del puntaje global de cada zona."""
    figura, eje = plt.subplots(figsize=(8, 4.5), facecolor=FONDO)  # Crea la figura
    bordes = np.arange(0, 505, 10)  # Intervalos de 10 puntos entre 0 y 500
    for zona in ZONAS:  # Una curva por zona
        datos = tabla.loc[tabla["zona"] == zona, "punt_global"]  # Puntajes de la zona
        eje.hist(datos, bins=bordes, density=True, histtype="step", linewidth=2, color=COLOR[zona],  # Histograma de contorno normalizado
                 label=f"{zona.capitalize()} (media {datos.mean():.1f})")  # Etiqueta con la media
    estilo(eje)  # Aplica el estilo común
    eje.set_xlabel("Puntaje global", color=TINTA_2)  # Nombre del eje horizontal
    eje.set_ylabel("Proporción de estudiantes", color=TINTA_2)  # Nombre del eje vertical
    eje.set_title(f"Distribución del puntaje global, Saber 11 {periodo}", color=TINTA, loc="left")  # Título
    eje.legend(frameon=False, labelcolor=TINTA)  # Leyenda sin recuadro
    figura.tight_layout()  # Ajusta márgenes
    guardar(figura, ruta)  # Guarda la imagen


def grafica_areas(resumen: pd.DataFrame, ruta: Path, periodo: str) -> None:
    """Dibuja la media de cada área para urbano y rural, en barras agrupadas."""
    figura, eje = plt.subplots(figsize=(8, 4.5), facecolor=FONDO)  # Crea la figura
    posiciones = np.arange(len(AREAS))  # Posición de cada área en el eje horizontal
    ancho = 0.38  # Ancho de cada barra
    for i, zona in enumerate(ZONAS):  # Un grupo de barras por zona
        fila = resumen.set_index("zona").loc[zona]  # Fila de resumen de la zona
        valores = [fila[f"media_{c.removeprefix('punt_')}"] for c in AREAS]  # Medias por área
        barras = eje.bar(posiciones + (i - 0.5) * (ancho + 0.02), valores, width=ancho,  # Barras desplazadas con 2 % de separación
                         color=COLOR[zona], label=zona.capitalize())  # Color y etiqueta de la zona
        eje.bar_label(barras, fmt="%.1f", fontsize=8, color=TINTA_2, padding=2)  # Valor encima de cada barra
    estilo(eje)  # Aplica el estilo común
    eje.set_xticks(posiciones, list(AREAS.values()))  # Nombres de las áreas
    eje.set_ylabel("Puntaje promedio (0 a 100)", color=TINTA_2)  # Nombre del eje vertical
    eje.set_ylim(0, 100)  # Escala completa del puntaje por área
    eje.set_title(f"Promedio por área según zona del colegio, Saber 11 {periodo}", color=TINTA, loc="left")  # Título
    eje.legend(frameon=False, labelcolor=TINTA)  # Leyenda sin recuadro
    figura.tight_layout()  # Ajusta márgenes
    guardar(figura, ruta)  # Guarda la imagen


def grafica_departamentos(deptos: pd.DataFrame, ruta: Path, periodo: str) -> None:
    """Dibuja la brecha urbano - rural de cada departamento en barras horizontales."""
    datos = deptos.sort_values("brecha", kind="mergesort")  # Ordena de menor a mayor para que la mayor quede arriba
    figura, eje = plt.subplots(figsize=(8, max(4, 0.28 * len(datos))), facecolor=FONDO)  # Alto según el número de departamentos
    eje.barh(datos["cole_depto_ubicacion"].str.title(), datos["brecha"], color=COLOR["URBANO"], height=0.7)  # Una barra por departamento
    estilo(eje)  # Aplica el estilo común
    eje.grid(axis="y", visible=False)  # Quita la rejilla horizontal
    eje.grid(axis="x", color=REJILLA, linewidth=0.8)  # Usa rejilla vertical
    eje.axvline(0, color=TINTA_2, linewidth=1)  # Línea en cero: a la derecha, ventaja urbana
    eje.set_xlabel("Brecha en puntaje global (urbano − rural)", color=TINTA_2)  # Nombre del eje
    eje.set_title(f"Brecha urbano − rural por departamento, Saber 11 {periodo}", color=TINTA, loc="left")  # Título
    eje.tick_params(axis="y", labelsize=8)  # Nombres de departamentos en letra pequeña
    figura.tight_layout()  # Ajusta márgenes
    guardar(figura, ruta)  # Guarda la imagen


def main() -> int:
    """Ejecuta el análisis completo y escribe las salidas con su manifiesto."""
    lector = argparse.ArgumentParser(description=__doc__)  # Prepara el lector de argumentos
    lector.add_argument("--periodo", default="20224")  # Periodo a analizar
    lector.add_argument("--datos", default="datos")  # Carpeta de entrada
    lector.add_argument("--salidas", default="salidas")  # Carpeta de salida
    args = lector.parse_args()  # Lee los argumentos

    entrada = Path(args.datos) / f"saber11_{args.periodo}.csv"  # Archivo de datos descargado
    carpeta = Path(args.salidas)  # Carpeta de salidas
    carpeta.mkdir(parents=True, exist_ok=True)  # La crea si no existe

    tabla = cargar(entrada)  # Lee y limpia los datos
    print(f"== Análisis rural vs urbano, periodo {args.periodo} ({len(tabla):,} estudiantes) ==")  # Encabezado

    resumen = resumen_zona(tabla)  # Resumen por zona
    naturaleza = brecha_por(tabla, "cole_naturaleza")  # Brecha según colegio oficial o no oficial
    estrato = brecha_por(tabla, "fami_estratovivienda", minimo=30)  # Brecha según estrato (grupos con al menos 30 rurales)
    deptos = brecha_por(tabla, "cole_depto_ubicacion", minimo=MIN_RURAL_DEPTO)  # Brecha por departamento
    prueba = prueba_estadistica(tabla)  # Prueba t y tamaño del efecto

    salidas = {  # Archivos que produce el análisis
        "resumen_zona.csv": resumen,  # Tabla de resumen por zona
        "brecha_naturaleza.csv": naturaleza,  # Brecha por tipo de colegio
        "brecha_estrato.csv": estrato,  # Brecha por estrato
        "brecha_departamento.csv": deptos,  # Brecha por departamento
    }
    for nombre, df in salidas.items():  # Recorre cada tabla
        df.to_csv(carpeta / nombre, index=False, lineterminator="\n")  # La guarda en CSV
    resumen.to_parquet(carpeta / "resumen_zona.parquet", index=False)  # El resumen también en Parquet
    (carpeta / "prueba_estadistica.json").write_text(json.dumps(prueba, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")  # Guarda la prueba

    grafica_distribucion(tabla, carpeta / "distribucion_global.png", args.periodo)  # Gráfica 1
    grafica_areas(resumen, carpeta / "medias_por_area.png", args.periodo)  # Gráfica 2
    grafica_departamentos(deptos, carpeta / "brecha_departamento.png", args.periodo)  # Gráfica 3

    pd.set_option("display.width", 200)  # Ancho de impresión para que las tablas no se partan
    print("\n-- Resumen por zona --")  # Título de la tabla
    print(resumen.to_string(index=False))  # Imprime el resumen
    print("\n-- Brecha según tipo de colegio --")  # Título de la tabla
    print(naturaleza.to_string(index=False))  # Imprime la brecha por naturaleza
    print("\n-- Brecha según estrato --")  # Título de la tabla
    print(estrato.to_string(index=False))  # Imprime la brecha por estrato
    print("\n-- Departamentos con mayor y menor brecha --")  # Título de la tabla
    print(pd.concat([deptos.head(5), deptos.tail(5)]).to_string(index=False))  # Imprime los 5 extremos de cada lado
    print("\n-- Prueba estadística --")  # Título
    print(json.dumps(prueba, indent=2, ensure_ascii=False))  # Imprime la prueba

    nombres = sorted(p.name for p in carpeta.iterdir() if p.is_file() and p.name not in {"manifiesto.json", ".gitkeep"})  # Salidas a registrar
    manifiesto = {  # Contenido del manifiesto
        "periodo": args.periodo,  # Periodo analizado
        "estudiantes": int(len(tabla)),  # Número de estudiantes analizados
        "sha256_datos": huella(entrada),  # Huella del archivo de entrada
        "huellas": {n: huella(carpeta / n) for n in nombres},  # Huella de cada salida
        "python": platform.python_version(),  # Versión de Python
        "numpy": np.__version__,  # Versión de numpy
        "pandas": pd.__version__,  # Versión de pandas
        "pyarrow": pyarrow.__version__,  # Versión de pyarrow
        "matplotlib": matplotlib.__version__,  # Versión de matplotlib
        "scipy": scipy.__version__,  # Versión de scipy
    }
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2) + "\n", encoding="utf-8")  # Guarda el manifiesto

    print("\n-- Huellas SHA-256 --")  # Título
    print(f"{manifiesto['sha256_datos']}  datos/{entrada.name}")  # Huella de los datos
    for nombre, valor in manifiesto["huellas"].items():  # Recorre las salidas
        print(f"{valor}  {nombre}")  # Huella de cada salida
    return 0  # Termina sin error


if __name__ == "__main__":  # Solo se ejecuta si el archivo se corre directamente
    sys.exit(main())  # Llama a main y devuelve su código de salida
