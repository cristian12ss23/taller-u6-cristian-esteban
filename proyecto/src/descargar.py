"""Descarga los resultados de Saber 11 de un periodo desde datos.gov.co.

Usa la API pública (Socrata) del conjunto "Resultados únicos Saber 11" del ICFES
y guarda un CSV ordenado de forma fija, para que dos descargas iguales produzcan
el mismo archivo (misma huella SHA-256).
Uso: python src/descargar.py --periodo 20224
"""

import argparse  # Lee los argumentos de la línea de comandos (por ejemplo, --periodo)
import hashlib  # Calcula la huella SHA-256 del archivo descargado
import io  # Permite leer texto en memoria como si fuera un archivo
import sys  # Da acceso a la salida estándar y al código de salida del programa
import time  # Permite esperar unos segundos entre reintentos
import urllib.parse  # Arma la dirección web con los filtros codificados
import urllib.request  # Hace las peticiones HTTP a datos.gov.co
from pathlib import Path  # Maneja rutas de archivos de forma clara

import pandas as pd  # Une las páginas descargadas, las ordena y escribe el CSV

URL_BASE = "https://www.datos.gov.co/resource/kgxf-xxbe.csv"  # Dirección del conjunto en formato CSV
COLUMNAS = [  # Columnas que se piden a la API (solo las necesarias, para descargar menos)
    "periodo",  # Año y calendario de la prueba (por ejemplo, 20224)
    "cole_area_ubicacion",  # Zona del colegio: URBANO o RURAL
    "cole_naturaleza",  # Tipo de colegio: OFICIAL o NO OFICIAL
    "cole_depto_ubicacion",  # Departamento donde está el colegio
    "fami_estratovivienda",  # Estrato de la vivienda del estudiante
    "punt_global",  # Puntaje global (0 a 500)
    "punt_matematicas",  # Puntaje de matemáticas
    "punt_lectura_critica",  # Puntaje de lectura crítica
    "punt_c_naturales",  # Puntaje de ciencias naturales
    "punt_sociales_ciudadanas",  # Puntaje de sociales y ciudadanas
    "punt_ingles",  # Puntaje de inglés
]
TAM_PAGINA = 50000  # Filas por petición; la API entrega los datos por páginas
REINTENTOS = 5  # Veces que se reintenta una página si la conexión falla


def pedir_pagina(periodo: str, desplazamiento: int) -> pd.DataFrame:
    """Descarga una página de resultados y la devuelve como tabla."""
    filtro = (  # Condición SoQL: el periodo pedido y filas con puntaje y zona
        f"periodo='{periodo}' "  # Solo el periodo indicado
        "AND punt_global IS NOT NULL "  # Descarta filas sin puntaje global
        "AND cole_area_ubicacion IS NOT NULL"  # Descarta filas sin zona del colegio
    )
    parametros = {  # Parámetros de la consulta a la API
        "$select": ",".join(COLUMNAS),  # Columnas a devolver
        "$where": filtro,  # Filtro de filas
        "$order": ":id",  # Orden estable por identificador interno, para paginar sin repetir filas
        "$limit": TAM_PAGINA,  # Tamaño de la página
        "$offset": desplazamiento,  # Desde qué fila empieza esta página
    }
    url = URL_BASE + "?" + urllib.parse.urlencode(parametros)  # Dirección completa con los parámetros
    for intento in range(1, REINTENTOS + 1):  # Repite la petición si falla
        try:  # Intenta descargar la página
            with urllib.request.urlopen(url, timeout=180) as respuesta:  # Abre la conexión con 3 minutos de espera máxima
                texto = respuesta.read().decode("utf-8")  # Lee la respuesta completa como texto
            return pd.read_csv(io.StringIO(texto), dtype=str)  # Convierte el texto CSV en tabla, todo como texto
        except Exception as error:  # Si hubo un error de red o del servidor
            espera = 10 * intento  # Espera cada vez más larga entre reintentos
            print(f"  Intento {intento} falló ({error}); reintento en {espera} s", flush=True)  # Informa el problema
            time.sleep(espera)  # Pausa antes de reintentar
    raise RuntimeError(f"No se pudo descargar la página con desplazamiento {desplazamiento}")  # Se rinde tras varios fallos


def huella(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    sha = hashlib.sha256()  # Crea el calculador de la huella
    with ruta.open("rb") as archivo:  # Abre el archivo en modo binario
        for bloque in iter(lambda: archivo.read(1 << 20), b""):  # Lee el archivo en bloques de 1 MB
            sha.update(bloque)  # Agrega cada bloque al cálculo
    return sha.hexdigest()  # Devuelve la huella en hexadecimal


def main() -> int:
    """Descarga todas las páginas del periodo y guarda el CSV ordenado."""
    lector = argparse.ArgumentParser(description=__doc__)  # Prepara el lector de argumentos
    lector.add_argument("--periodo", default="20224")  # Periodo a descargar; por defecto 2022, calendario A
    lector.add_argument("--salida", default="datos")  # Carpeta donde se guarda el CSV
    args = lector.parse_args()  # Lee los argumentos recibidos

    carpeta = Path(args.salida)  # Ruta de la carpeta de datos
    carpeta.mkdir(parents=True, exist_ok=True)  # Crea la carpeta si no existe
    destino = carpeta / f"saber11_{args.periodo}.csv"  # Nombre del archivo final

    if destino.exists():  # Si los datos ya se descargaron antes
        print(f"Ya existe {destino}; se reutiliza (bórrelo para descargar de nuevo).")  # Evita descargar otra vez
        print(f"SHA-256 datos : {huella(destino)}")  # Muestra su huella
        return 0  # Termina sin error

    print(f"== Descarga de Saber 11, periodo {args.periodo} ==", flush=True)  # Encabezado del proceso
    paginas = []  # Lista donde se acumulan las páginas descargadas
    desplazamiento = 0  # Empieza desde la primera fila
    while True:  # Repite hasta que no queden filas
        pagina = pedir_pagina(args.periodo, desplazamiento)  # Descarga una página
        paginas.append(pagina)  # La guarda en la lista
        desplazamiento += len(pagina)  # Avanza el punto de inicio de la siguiente página
        print(f"  Filas descargadas: {desplazamiento:,}", flush=True)  # Muestra el avance
        if len(pagina) < TAM_PAGINA:  # Una página incompleta significa que era la última
            break  # Sale del ciclo

    tabla = pd.concat(paginas, ignore_index=True)  # Une todas las páginas en una sola tabla
    tabla = tabla[COLUMNAS]  # Asegura el mismo orden de columnas siempre
    tabla = tabla.sort_values(COLUMNAS, kind="mergesort", na_position="last")  # Ordena todas las filas de forma fija
    tabla.to_csv(destino, index=False, lineterminator="\n")  # Guarda el CSV sin índice y con saltos de línea fijos

    print(f"Filas totales : {len(tabla):,}")  # Informa cuántas filas quedaron
    print(f"Archivo       : {destino}")  # Informa dónde quedó el archivo
    print(f"SHA-256 datos : {huella(destino)}")  # Informa la huella de los datos
    return 0  # Termina sin error


if __name__ == "__main__":  # Solo se ejecuta si el archivo se corre directamente
    sys.exit(main())  # Llama a main y devuelve su código de salida
