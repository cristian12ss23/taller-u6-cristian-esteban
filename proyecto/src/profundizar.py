"""Profundiza la comparación rural vs urbana de Saber 11.

Responde lo que analisis.py y comparar.py dejan abierto:
  1. ¿Cuánto queda de la brecha al comparar dentro del mismo tipo de colegio y estrato?
  2. ¿El aumento 2019-2022 ocurre dentro de esos grupos o viene de cambios de composición?
  3. ¿Qué tan precisa es la brecha de cada departamento y cuántos estudiantes rurales tiene?
  4. ¿Cuántos datos faltan o quedan por fuera?
Además guarda los datos limpios en Parquet y comprueba que la conversión sea correcta.

No modifica las salidas de analisis.py ni de comparar.py, así que sus huellas no cambian.
Uso: python src/profundizar.py --antes 20194 --despues 20224
"""

import argparse  # Lee los argumentos de la línea de comandos
import json  # Escribe los registros en formato JSON
import sys  # Da acceso al código de salida del programa
import time  # Mide el tiempo de lectura de CSV y Parquet
import urllib.parse  # Arma la dirección de la consulta a la API
import urllib.request  # Hace la consulta a datos.gov.co
from pathlib import Path  # Maneja rutas de archivos

import numpy as np  # Cálculos numéricos
import pandas as pd  # Manejo de tablas
from scipy import stats  # Valor crítico de la distribución t

from analisis import MIN_RURAL_DEPTO, PUNTAJES, cargar, huella  # Reutiliza la misma limpieza del análisis principal

URL_API = "https://www.datos.gov.co/resource/kgxf-xxbe.json"  # Misma fuente que usa descargar.py
SIN_DATO = "SIN DATO"  # Categoría para los valores vacíos, para no perder estudiantes en silencio
Z_95 = 1.96  # Valor crítico para un intervalo de confianza del 95 %
AJUSTES = {  # Comparaciones: nombre legible y columnas que deben coincidir
    "Sin ajustar": [],  # Brecha general, sin comparar dentro de grupos
    "Mismo tipo de colegio": ["cole_naturaleza"],  # Oficial con oficial, no oficial con no oficial
    "Mismo estrato": ["fami_estratovivienda"],  # Dentro de cada estrato
    "Mismo tipo y estrato": ["cole_naturaleza", "fami_estratovivienda"],  # Las dos variables a la vez
}


def preparar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Marca los valores vacíos como una categoría propia en las columnas de agrupación."""
    tabla = tabla.copy()  # No modifica la tabla original
    for columna in ["cole_naturaleza", "fami_estratovivienda", "cole_depto_ubicacion"]:  # Columnas de agrupación
        tabla[columna] = tabla[columna].fillna(SIN_DATO)  # El vacío queda visible como SIN DATO
    return tabla  # Devuelve la copia preparada


def celdas(tabla: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Calcula tamaño, media y varianza del puntaje global por grupo y zona, con una fila por grupo."""
    claves = ["zona", *columnas]  # Agrupa por zona y por las columnas pedidas
    resumen = tabla.groupby(claves, observed=True)["punt_global"].agg(n="size", media="mean", var="var")  # Estadísticos por celda
    ancha = resumen.unstack("zona")  # Deja urbano y rural en la misma fila
    ancha.columns = [f"{medida}_{zona.lower()}" for medida, zona in ancha.columns]  # Nombres como n_urbano o media_rural
    return ancha.reset_index()  # Deja los grupos como columnas


def preparar_celdas(tabla: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Devuelve las celdas de una comparación; sin columnas, usa una sola celda con todos los estudiantes."""
    if columnas:  # Hay variables para comparar dentro de grupos
        return celdas(tabla, columnas)  # Una fila por combinación de valores
    copia = tabla.assign(_todos="todos")  # Columna auxiliar para tratar el caso sin ajustar igual que los demás
    return celdas(copia, ["_todos"])  # Una sola fila con toda la población


def brecha_con_pesos(tabla_celdas: pd.DataFrame, pesos: pd.Series) -> tuple[float, float]:
    """Calcula el promedio ponderado de las brechas de cada celda y su error estándar."""
    brecha = tabla_celdas["media_urbano"] - tabla_celdas["media_rural"]  # Brecha dentro de cada celda
    varianza = tabla_celdas["var_urbano"] / tabla_celdas["n_urbano"] + tabla_celdas["var_rural"] / tabla_celdas["n_rural"]  # Varianza de cada brecha
    valor = float((pesos * brecha).sum())  # Suma de peso por brecha
    error = float(np.sqrt((pesos**2 * varianza).sum()))  # Los pesos se tratan como fijos
    return valor, error  # Devuelve la brecha ajustada y su error estándar


def celdas_validas(tabla_celdas: pd.DataFrame) -> pd.DataFrame:
    """Conserva las celdas con al menos 2 estudiantes en cada zona, para poder calcular su varianza."""
    return tabla_celdas[(tabla_celdas["n_urbano"].fillna(0) >= 2) & (tabla_celdas["n_rural"].fillna(0) >= 2)]  # Sin una zona no hay comparación


def comparar_ajustes(antes: pd.DataFrame, despues: pd.DataFrame, periodo_a: str, periodo_d: str) -> pd.DataFrame:
    """Calcula cada brecha ajustada en los dos periodos con los mismos pesos y mide su cambio.

    Los pesos son la composición rural del periodo posterior, en los dos años. Así, el cambio
    mide lo que pasó dentro de los grupos y no se confunde con cambios en el tamaño de cada grupo.
    """
    filas = []  # Filas de la tabla final
    for nombre, columnas in AJUSTES.items():  # Recorre cada comparación
        claves = columnas or ["_todos"]  # Columna que identifica la celda
        ca = celdas_validas(preparar_celdas(antes, columnas))  # Celdas del periodo anterior
        cd = celdas_validas(preparar_celdas(despues, columnas))  # Celdas del periodo posterior
        union = cd.merge(ca, on=claves, suffixes=("", "_a"))  # Solo celdas presentes en ambos periodos
        pesos = union["n_rural"] / union["n_rural"].sum()  # Composición rural del periodo posterior
        celdas_a = union[[*claves, "n_urbano_a", "n_rural_a", "media_urbano_a", "media_rural_a", "var_urbano_a", "var_rural_a"]].copy()  # Datos del periodo anterior
        celdas_a.columns = [*claves, "n_urbano", "n_rural", "media_urbano", "media_rural", "var_urbano", "var_rural"]  # Mismos nombres para reutilizar la función
        valor_a, error_a = brecha_con_pesos(celdas_a, pesos)  # Brecha del periodo anterior
        valor_d, error_d = brecha_con_pesos(union, pesos)  # Brecha del periodo posterior
        cambio = valor_d - valor_a  # Positivo: la brecha creció
        error_c = float(np.hypot(error_a, error_d))  # Error del cambio; los dos periodos son poblaciones distintas
        total_rural = preparar_celdas(despues, columnas)["n_rural"].sum()  # Rurales antes de excluir celdas
        filas.append({  # Agrega la fila
            "comparacion": nombre,  # Nombre del ajuste
            f"brecha_{periodo_a}": round(valor_a, 2),  # Brecha del periodo anterior
            f"ic95_inf_{periodo_a}": round(valor_a - Z_95 * error_a, 2),  # Límite inferior
            f"ic95_sup_{periodo_a}": round(valor_a + Z_95 * error_a, 2),  # Límite superior
            f"brecha_{periodo_d}": round(valor_d, 2),  # Brecha del periodo posterior
            f"ic95_inf_{periodo_d}": round(valor_d - Z_95 * error_d, 2),  # Límite inferior
            f"ic95_sup_{periodo_d}": round(valor_d + Z_95 * error_d, 2),  # Límite superior
            "cambio": round(cambio, 2),  # Cambio de la brecha
            "cambio_ic95_inf": round(cambio - Z_95 * error_c, 2),  # Límite inferior del cambio
            "cambio_ic95_sup": round(cambio + Z_95 * error_c, 2),  # Límite superior del cambio
            "rurales_incluidos_pct": round(100 * float(union["n_rural"].sum()) / float(total_rural), 2),  # Rurales con comparación posible
        })
    return pd.DataFrame(filas)  # Devuelve la tabla


def tabla_tipo_estrato(tabla: pd.DataFrame) -> pd.DataFrame:
    """Calcula la brecha y su intervalo en cada combinación de tipo de colegio y estrato."""
    salida = celdas_validas(celdas(tabla, ["cole_naturaleza", "fami_estratovivienda"])).copy()  # Combinaciones con urbanos y rurales
    salida["brecha"] = salida["media_urbano"] - salida["media_rural"]  # Brecha de la combinación
    error = np.sqrt(salida["var_urbano"] / salida["n_urbano"] + salida["var_rural"] / salida["n_rural"])  # Error estándar de Welch
    salida["ic95_inf"] = salida["brecha"] - Z_95 * error  # Límite inferior
    salida["ic95_sup"] = salida["brecha"] + Z_95 * error  # Límite superior
    salida = salida.drop(columns=["var_urbano", "var_rural"])  # Las varianzas ya no hacen falta
    salida[["n_urbano", "n_rural"]] = salida[["n_urbano", "n_rural"]].astype(int)  # Conteos como enteros
    return salida.sort_values(["cole_naturaleza", "fami_estratovivienda"], kind="mergesort").round(2).reset_index(drop=True)  # Orden fijo


def tabla_departamentos(tabla: pd.DataFrame) -> pd.DataFrame:
    """Calcula la brecha de cada departamento con intervalo de confianza de Welch y peso rural."""
    salida = celdas_validas(celdas(tabla, ["cole_depto_ubicacion"])).copy()  # Departamentos con urbanos y rurales
    salida = salida[salida["n_rural"] >= MIN_RURAL_DEPTO].copy()  # Mismo mínimo que usa analisis.py
    salida["brecha"] = salida["media_urbano"] - salida["media_rural"]  # Brecha del departamento
    var_u = salida["var_urbano"] / salida["n_urbano"]  # Varianza de la media urbana
    var_r = salida["var_rural"] / salida["n_rural"]  # Varianza de la media rural
    gl = (var_u + var_r) ** 2 / (var_u**2 / (salida["n_urbano"] - 1) + var_r**2 / (salida["n_rural"] - 1))  # Grados de libertad de Welch
    margen = stats.t.ppf(0.975, gl) * np.sqrt(var_u + var_r)  # Margen de error del intervalo
    salida["ic95_inf"] = salida["brecha"] - margen  # Límite inferior
    salida["ic95_sup"] = salida["brecha"] + margen  # Límite superior
    salida["pct_de_los_rurales"] = 100 * salida["n_rural"] / tabla["zona"].eq("RURAL").sum()  # Peso en el total nacional de rurales
    salida = salida.drop(columns=["var_urbano", "var_rural"])  # Las varianzas ya no hacen falta
    salida[["n_urbano", "n_rural"]] = salida[["n_urbano", "n_rural"]].astype(int)  # Conteos como enteros
    return salida.sort_values("brecha", ascending=False, kind="mergesort").round(2).reset_index(drop=True)  # Mayor brecha primero


def contar_faltantes(tabla: pd.DataFrame, limpieza: dict) -> dict:
    """Cuenta los valores vacíos que llegan al análisis y las filas quitadas en la limpieza."""
    columnas = [*PUNTAJES, "cole_naturaleza", "fami_estratovivienda", "cole_depto_ubicacion"]  # Columnas que se revisan
    vacios = {c: {z.lower(): int(tabla.loc[tabla["zona"] == z, c].isna().sum()) for z in ["URBANO", "RURAL"]} for c in columnas}  # Vacíos por zona
    return {"limpieza": limpieza, "vacios_por_zona": vacios}  # Devuelve el registro


def excluidos_en_descarga(periodo: str) -> dict:
    """Pregunta a la API cuántas filas descartó el filtro de descargar.py; si no hay red, lo informa."""
    filtro = f"periodo='{periodo}' AND (punt_global IS NULL OR cole_area_ubicacion IS NULL)"  # Condición contraria a la de la descarga
    url = URL_API + "?" + urllib.parse.urlencode({"$select": "count(*) AS filas", "$where": filtro})  # Consulta de conteo
    try:  # La consulta es informativa: si falla, el análisis continúa
        with urllib.request.urlopen(url, timeout=120) as respuesta:  # Abre la conexión
            filas = int(json.loads(respuesta.read().decode("utf-8"))[0]["filas"])  # Lee el conteo
        return {"filas_excluidas_en_descarga": filas, "nota": "Filas, no estudiantes: el conjunto trae casi todo repetido."}  # Resultado
    except Exception as error:  # Sin red, o la API rechazó la consulta
        return {"filas_excluidas_en_descarga": None, "nota": f"No se pudo consultar: {error}"}  # Deja constancia sin detener el programa


def a_parquet(tabla: pd.DataFrame, entrada: Path, destino: Path) -> dict:
    """Guarda la tabla limpia en Parquet y comprueba que la conversión conserve los datos."""
    tabla.to_parquet(destino, index=False)  # Escribe el archivo sin el índice de pandas
    leida = pd.read_parquet(destino)  # Lo vuelve a leer para compararlo
    iguales = {  # Comprobaciones de la clase: conteos, columnas, nulos y sumas
        "filas": len(leida) == len(tabla),  # Mismo número de filas
        "columnas": list(leida.columns) == list(tabla.columns),  # Mismas columnas y en el mismo orden
        "nulos": bool((leida.isna().sum() == tabla.isna().sum()).all()),  # Mismos vacíos por columna
        "suma_global": bool(np.isclose(leida["punt_global"].sum(), tabla["punt_global"].sum())),  # Misma suma del puntaje
    }
    if not all(iguales.values()):  # Si algo no coincide, es mejor detenerse
        raise RuntimeError(f"La conversión a Parquet no conserva los datos: {iguales}")  # Evita seguir con datos dañados
    inicio = time.perf_counter()  # Marca el inicio de la lectura del CSV
    pd.read_csv(entrada, usecols=["cole_area_ubicacion", "punt_global"], dtype=str)  # Lee dos columnas del CSV
    t_csv = time.perf_counter() - inicio  # Tiempo de lectura del CSV
    inicio = time.perf_counter()  # Marca el inicio de la lectura del Parquet
    pd.read_parquet(destino, columns=["zona", "punt_global"])  # Lee dos columnas del Parquet
    t_parquet = time.perf_counter() - inicio  # Tiempo de lectura del Parquet
    print(f"  Dos columnas de {entrada.name}: CSV {t_csv:.2f} s, Parquet {t_parquet:.2f} s (cambia en cada corrida)")  # Solo en pantalla, para no alterar huellas
    return {  # Registro de la conversión
        "comprobaciones": iguales,  # Resultado de cada comprobación
        "mb_csv_con_repetidos": round(entrada.stat().st_size / 1e6, 1),  # Tamaño del CSV original
        "mb_parquet_sin_repetidos": round(destino.stat().st_size / 1e6, 1),  # Tamaño del Parquet limpio
    }


def num(valor) -> str:
    """Escribe un número con coma decimal, como en el README."""
    return f"{valor:.2f}".replace(".", ",")  # Dos decimales y coma


def entero(valor) -> str:
    """Escribe un entero con punto de miles, como en el README."""
    return f"{int(valor):,}".replace(",", ".")  # Punto de miles


def ic(inferior, superior) -> str:
    """Escribe un intervalo de confianza."""
    return f"{num(inferior)} a {num(superior)}"  # Texto del intervalo


def escribir_resultados(ruta: Path, ajustes: pd.DataFrame, tipo_estrato: pd.DataFrame, deptos: pd.DataFrame, registro: dict, a: str, d: str) -> None:
    """Escribe tablas en Markdown, listas para copiar en el README."""
    lineas = ["# Resultados de la profundización", ""]  # Título del archivo
    lineas += [f"## Brecha urbano − rural con la composición rural de {d}", ""]  # Encabezado de la tabla de ajustes
    lineas += [f"| Comparación | Brecha {a} | IC 95 % | Brecha {d} | IC 95 % | Cambio | IC 95 % del cambio | Rurales incluidos |", "|---|---|---|---|---|---|---|---|"]  # Columnas
    for _, f in ajustes.iterrows():  # Una fila por comparación
        lineas.append(f"| {f['comparacion']} | {num(f[f'brecha_{a}'])} | {ic(f[f'ic95_inf_{a}'], f[f'ic95_sup_{a}'])} | {num(f[f'brecha_{d}'])} | {ic(f[f'ic95_inf_{d}'], f[f'ic95_sup_{d}'])} | {num(f['cambio'])} | {ic(f['cambio_ic95_inf'], f['cambio_ic95_sup'])} | {num(f['rurales_incluidos_pct'])} % |")  # Fila
    lineas += ["", f"## Brecha por tipo de colegio y estrato, {d}", ""]  # Encabezado
    lineas += ["| Tipo | Estrato | Urbanos | Rurales | Media urbano | Media rural | Brecha | IC 95 % |", "|---|---|---|---|---|---|---|---|"]  # Columnas
    for _, f in tipo_estrato.iterrows():  # Una fila por combinación
        lineas.append(f"| {f['cole_naturaleza']} | {f['fami_estratovivienda']} | {entero(f['n_urbano'])} | {entero(f['n_rural'])} | {num(f['media_urbano'])} | {num(f['media_rural'])} | {num(f['brecha'])} | {ic(f['ic95_inf'], f['ic95_sup'])} |")  # Fila
    lineas += ["", f"## Brecha por departamento, {d}", ""]  # Encabezado
    lineas += ["| Departamento | Rurales | % de los rurales | Brecha | IC 95 % |", "|---|---|---|---|---|"]  # Columnas
    for _, f in deptos.iterrows():  # Una fila por departamento
        lineas.append(f"| {f['cole_depto_ubicacion']} | {entero(f['n_rural'])} | {num(f['pct_de_los_rurales'])} % | {num(f['brecha'])} | {ic(f['ic95_inf'], f['ic95_sup'])} |")  # Fila
    lineas += ["", "## Datos faltantes y conversión a Parquet", "", "```json", json.dumps(registro, indent=2, ensure_ascii=False), "```", ""]  # Registro completo
    ruta.write_text("\n".join(lineas), encoding="utf-8")  # Guarda el archivo


def main() -> int:
    """Ejecuta la profundización y escribe sus salidas con un manifiesto."""
    lector = argparse.ArgumentParser(description=__doc__)  # Lector de argumentos
    lector.add_argument("--antes", default="20194")  # Periodo anterior
    lector.add_argument("--despues", default="20224")  # Periodo posterior
    lector.add_argument("--datos", default="datos")  # Carpeta de datos
    lector.add_argument("--salidas", default="salidas")  # Carpeta base de salidas
    args = lector.parse_args()  # Lee los argumentos

    carpeta = Path(args.salidas) / "profundizacion"  # Carpeta de salida
    carpeta.mkdir(parents=True, exist_ok=True)  # La crea si no existe
    tablas, registro = {}, {}  # Tablas limpias y registro de cada periodo

    for periodo in [args.antes, args.despues]:  # Recorre los dos periodos
        entrada = Path(args.datos) / f"saber11_{periodo}.csv"  # CSV descargado por descargar.py
        print(f"== Periodo {periodo} ==", flush=True)  # Encabezado
        tabla, limpieza = cargar(entrada)  # Misma limpieza de analisis.py
        registro[periodo] = {  # Registro de faltantes y conversión
            "faltantes": contar_faltantes(tabla, limpieza),  # Vacíos antes de marcarlos como SIN DATO
            "descarga": excluidos_en_descarga(periodo),  # Filas descartadas por el filtro de la descarga
            "parquet": a_parquet(tabla, entrada, Path(args.datos) / f"saber11_{periodo}_limpio.parquet"),  # Zona curada
        }
        tablas[periodo] = preparar(tabla)[["zona", "punt_global", "cole_naturaleza", "fami_estratovivienda", "cole_depto_ubicacion"]]  # Solo lo necesario, para ahorrar memoria

    ajustes = comparar_ajustes(tablas[args.antes], tablas[args.despues], args.antes, args.despues)  # Brechas ajustadas y su cambio
    tipo_estrato = tabla_tipo_estrato(tablas[args.despues])  # Brecha por tipo y estrato del periodo posterior
    deptos = tabla_departamentos(tablas[args.despues])  # Brecha por departamento con intervalo

    ajustes.to_csv(carpeta / "brecha_ajustada.csv", index=False, lineterminator="\n")  # Guarda la tabla de ajustes
    tipo_estrato.to_csv(carpeta / "brecha_tipo_estrato.csv", index=False, lineterminator="\n")  # Guarda tipo por estrato
    deptos.to_csv(carpeta / "brecha_departamento_ic.csv", index=False, lineterminator="\n")  # Guarda departamentos
    (carpeta / "registro.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")  # Guarda el registro
    escribir_resultados(carpeta / "resultados.md", ajustes, tipo_estrato, deptos, registro, args.antes, args.despues)  # Tablas listas para el README

    pd.set_option("display.width", 220)  # Ancho de impresión
    pd.set_option("display.max_columns", 30)  # Muestra todas las columnas
    print("\n-- Brecha ajustada --")  # Título
    print(ajustes.to_string(index=False))  # Imprime la tabla

    nombres = sorted(p.name for p in carpeta.iterdir() if p.is_file() and p.name != "manifiesto.json")  # Salidas a registrar
    manifiesto = {n: huella(carpeta / n) for n in nombres}  # Huella de cada salida
    (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2) + "\n", encoding="utf-8")  # Guarda el manifiesto
    print("\n-- Huellas SHA-256 --")  # Título
    for nombre, valor in manifiesto.items():  # Recorre las salidas
        print(f"{valor}  {nombre}")  # Imprime la huella
    print(f"\nTablas listas para el README en {carpeta / 'resultados.md'}")  # Indica dónde quedaron
    return 0  # Termina sin error


if __name__ == "__main__":  # Solo si el archivo se corre directamente
    sys.exit(main())  # Ejecuta main
