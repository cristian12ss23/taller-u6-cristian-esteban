"""Normaliza los resultados de Saber 11 hasta la tercera forma normal (3FN) con PySpark.

Lee con Spark los CSV de los periodos indicados (una fila por estudiante, tabla
plana), diagnostica qué impide cada forma normal, construye el modelo en 3FN,
lo guarda en Parquet, verifica llaves e integridad con Spark SQL y mide cómo
cambian las cifras al contar colegios en vez de filas.
Uso: python src/modelo_3fn.py --periodos 20194 20224
"""

import argparse  # Lee los argumentos de la línea de comandos
import hashlib  # Calcula las huellas SHA-256 de las salidas
import json  # Escribe el registro del proceso
import sys  # Da acceso al código de salida del programa
import time  # Mide cuánto tarda cada etapa
from pathlib import Path  # Maneja rutas de archivos

import matplotlib  # Biblioteca de gráficas
matplotlib.use("Agg")  # Dibuja sin pantalla (necesario dentro del contenedor)
import matplotlib.pyplot as plt  # Interfaz para crear las figuras
import pandas as pd  # Solo para resúmenes pequeños traídos con toPandas()
from pyspark.sql import SparkSession, Window  # Punto de entrada a Spark y ventanas para elegir valores
from pyspark.sql import functions as F  # Funciones de columnas: trim, lpad, count, avg...

PUNTAJES = [  # Columnas de puntaje que pasan de texto a número
    "punt_global", "punt_matematicas", "punt_lectura_critica",  # Global, matemáticas y lectura
    "punt_c_naturales", "punt_sociales_ciudadanas", "punt_ingles",  # Naturales, sociales e inglés
]
CODIGOS = {  # Códigos DANE y su número de dígitos según DIVIPOLA
    "cole_cod_depto_ubicacion": 2,  # Departamento: 2 dígitos (05 = Antioquia)
    "cole_cod_mcpio_ubicacion": 5,  # Municipio: 5 dígitos (05001 = Medellín)
    "cole_cod_dane_establecimiento": 12,  # Establecimiento: 12 dígitos
    "cole_cod_dane_sede": 12,  # Sede: 12 dígitos
}
TEXTOS = [  # Columnas de texto que se limpian (espacios y mayúsculas)
    "cole_area_ubicacion", "cole_naturaleza", "cole_depto_ubicacion",  # Zona, tipo de colegio y departamento
    "cole_mcpio_ubicacion", "cole_nombre_establecimiento", "cole_nombre_sede",  # Municipio, colegio y sede
]
DEPENDENCIAS = [  # Dependencias funcionales que se ponen a prueba: (determinante, dependiente, forma normal)
    ("cole_cod_dane_sede", "cole_cod_dane_establecimiento", "2FN/3FN"),  # Cada sede pertenece a un establecimiento
    ("cole_cod_dane_sede", "cole_cod_mcpio_ubicacion", "3FN"),  # Cada sede está en un municipio
    ("cole_cod_dane_sede", "cole_area_ubicacion", "3FN"),  # Cada sede es urbana o rural
    ("cole_cod_dane_sede", "cole_nombre_sede", "3FN"),  # Cada sede tiene un nombre
    ("cole_cod_dane_establecimiento", "cole_naturaleza", "3FN"),  # Cada establecimiento es oficial o no oficial
    ("cole_cod_dane_establecimiento", "cole_nombre_establecimiento", "3FN"),  # Cada establecimiento tiene un nombre
    ("cole_cod_mcpio_ubicacion", "cole_mcpio_ubicacion", "3FN"),  # Cada código de municipio tiene un nombre
    ("cole_cod_mcpio_ubicacion", "cole_cod_depto_ubicacion", "3FN"),  # Cada municipio está en un departamento
    ("cole_cod_depto_ubicacion", "cole_depto_ubicacion", "3FN"),  # Cada código de departamento tiene un nombre
    ("cole_depto_ubicacion", "cole_cod_depto_ubicacion", "Dominio"),  # Cada nombre de departamento tiene un código
]

COLOR_SEDES = "#6250d6"  # Violeta: porcentaje de sedes rurales (modelo 3FN)
COLOR_FILAS = "#9d9c97"  # Gris: porcentaje de estudiantes rurales (filas de la tabla plana)
TINTA, TINTA_2, REJILLA, FONDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"  # Colores de texto, ejes, rejilla y fondo


def huella(ruta: Path) -> str:
    """Calcula la huella SHA-256 de un archivo."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()  # Lee el archivo y devuelve su huella


def iniciar_spark() -> SparkSession:
    """Crea la SparkSession local con el patrón builder."""
    spark = (SparkSession.builder  # Inicio del patrón builder
             .appName("saber11_3fn")  # Nombre de la aplicación
             .master("local[*]")  # Usa todos los núcleos de la máquina como si fueran un clúster
             .config("spark.driver.memory", "4g")  # Memoria para el proceso principal
             .config("spark.sql.shuffle.partitions", "8")  # Particiones tras un groupBy o join (pocas, datos medianos)
             .config("spark.sql.session.timeZone", "UTC")  # Zona horaria fija para que el resultado no dependa de la máquina
             .config("spark.ui.enabled", "false")  # Sin interfaz web dentro del contenedor
             .config("spark.ui.showConsoleProgress", "false")  # Sin barras de progreso en la terminal
             .getOrCreate())  # Crea la sesión o reutiliza la existente
    spark.sparkContext.setLogLevel("ERROR")  # Muestra solo errores para no llenar la pantalla
    return spark  # Devuelve la sesión


def leer_plana(spark: SparkSession, carpeta: Path, periodos: list[str]):
    """Lee los CSV como tabla plana. Todo como texto: inferSchema quitaría los ceros iniciales de los códigos."""
    rutas = [str(carpeta / f"saber11_{p}.csv") for p in periodos]  # Un CSV por periodo
    plana = spark.read.option("header", True).csv(rutas)  # Lectura perezosa: todavía no abre los archivos
    return plana  # Devuelve el DataFrame sin ejecutar nada


def limpiar_codigos(df):
    """Quita espacios, decimales sobrantes (.0) y completa con ceros a la izquierda cada código DANE."""
    for col, digitos in CODIGOS.items():  # Recorre cada código
        limpio = F.regexp_replace(F.trim(F.col(col)), r"\.0+$", "")  # Quita espacios y un '.0' final (1234.0 -> 1234)
        df = df.withColumn(col, F.when(limpio.rlike(r"^[0-9]+$"), F.lpad(limpio, digitos, "0")))  # Solo dígitos; si no, queda vacío
    for col in TEXTOS:  # Recorre las columnas de texto
        df = df.withColumn(col, F.upper(F.trim(F.col(col))))  # Mayúsculas y sin espacios en los extremos
    return df  # Devuelve el DataFrame con las columnas limpias


def primera_forma_normal(plana):
    """Deja una fila por estudiante (llave primaria estu_consecutivo) y aplica la limpieza del análisis principal."""
    sin_copias = plana.dropDuplicates().cache()  # Quita filas idénticas y guarda el resultado en memoria
    filas = sin_copias.count()  # Acción: filas tras quitar las copias idénticas
    llaves = sin_copias.select("estu_consecutivo").distinct().count()  # Acción: estudiantes distintos
    if filas == llaves:  # Cada estudiante quedó con una sola fila: la llave ya es única
        unica = sin_copias  # No hace falta elegir entre filas
    else:  # Hay estudiantes con dos versiones distintas de sus datos
        orden = Window.partitionBy("estu_consecutivo").orderBy(*[F.col(c).asc_nulls_last() for c in sin_copias.columns])  # Orden fijo
        unica = (sin_copias.withColumn("_n", F.row_number().over(orden))  # Numera las filas de cada estudiante
                 .filter(F.col("_n") == 1).drop("_n"))  # Conserva la primera: una fila por estudiante, siempre la misma
    for col in PUNTAJES:  # Recorre los puntajes
        unica = unica.withColumn(col, F.col(col).cast("double"))  # Texto a número; lo inválido queda vacío
    valida = unica.filter(F.col("cole_area_ubicacion").isin("URBANO", "RURAL")  # Solo las dos zonas comparadas
                          & F.col("punt_global").between(0, 500))  # Y puntaje global en el rango válido
    return sin_copias, unica, valida  # Devuelve cada paso para poder contarlos


def probar_dependencias(df) -> pd.DataFrame:
    """Cuenta, para cada dependencia X -> Y, cuántos valores de X aparecen con más de un valor de Y."""
    filas = []  # Resultados de cada prueba
    for x, y, forma in DEPENDENCIAS:  # Recorre las dependencias
        combinaciones = (df.filter(F.col(x).isNotNull() & F.col(y).isNotNull())  # Solo filas con los dos valores
                         .groupBy("periodo", x, y).count()  # Spark reduce millones de filas a las combinaciones distintas
                         .toPandas())  # Acción: trae ese resumen pequeño a pandas (reducir antes de traer)
        por_x = combinaciones.groupby(["periodo", x]).agg(valores=(y, "nunique"), estudiantes=("count", "sum"))  # Valores de Y por X
        conflictos = por_x[por_x["valores"] > 1]  # X con más de un Y en el mismo periodo: la dependencia no se cumple
        total = combinaciones[x].nunique()  # Valores distintos de X
        n_conf = conflictos.index.get_level_values(x).nunique()  # X en conflicto dentro de algún periodo
        filas_afectadas = int(conflictos["estudiantes"].sum())  # Estudiantes en esos X
        entre_periodos = int((combinaciones.groupby(x)[y].nunique() > 1).sum())  # X con más de un Y juntando los periodos
        filas.append({"determinante": x, "dependiente": y, "forma": forma, "valores_x": total,  # Guarda la fila
                      "en_conflicto_mismo_periodo": n_conf, "estudiantes_afectados": filas_afectadas,  # Conflictos y alcance
                      "cambian_entre_periodos": entre_periodos})  # Cambios entre 2019 y 2022
    return pd.DataFrame(filas)  # Devuelve la tabla de pruebas


def moda(df, llaves: list[str], valor: str, nombre: str):
    """Elige, para cada llave, el valor más frecuente; en empate, el primero en orden alfabético."""
    conteo = df.filter(F.col(valor).isNotNull()).groupBy(*llaves, valor).count()  # Frecuencia de cada valor
    orden = Window.partitionBy(*llaves).orderBy(F.col("count").desc(), F.col(valor).asc())  # Más frecuente primero
    return (conteo.withColumn("_n", F.row_number().over(orden)).filter("_n = 1")  # Queda el valor ganador
            .select(*llaves, F.col(valor).alias(nombre)))  # Con el nombre de columna del modelo


def construir_modelo(df) -> dict:
    """Descompone la tabla plana en seis tablas en 3FN."""
    con_sede = df.filter(F.col("cole_cod_dane_sede").isNotNull())  # Solo estudiantes con código de sede (llave foránea)
    departamentos = (moda(con_sede.withColumn("cod_depto", F.col("cole_cod_mcpio_ubicacion").substr(1, 2)),  # Código desde DIVIPOLA
                          ["cod_depto"], "cole_depto_ubicacion", "departamento")  # Nombre más frecuente por código
                     .filter(F.col("cod_depto").isNotNull()))  # Sin códigos vacíos
    municipios = (moda(con_sede, ["cole_cod_mcpio_ubicacion"], "cole_mcpio_ubicacion", "municipio")  # Nombre por código
                  .withColumnRenamed("cole_cod_mcpio_ubicacion", "cod_mcpio")  # Nombre de la llave primaria
                  .withColumn("cod_depto", F.col("cod_mcpio").substr(1, 2)))  # DIVIPOLA: los 2 primeros dígitos son el departamento
    establecimientos = (moda(con_sede, ["cole_cod_dane_establecimiento"], "cole_nombre_establecimiento", "establecimiento")  # Nombre
                        .join(moda(con_sede, ["cole_cod_dane_establecimiento"], "cole_naturaleza", "naturaleza"),  # Tipo de colegio
                              "cole_cod_dane_establecimiento", "left")  # Une nombre y naturaleza
                        .withColumnRenamed("cole_cod_dane_establecimiento", "cod_establecimiento"))  # Llave primaria
    sedes = (moda(con_sede, ["cole_cod_dane_sede"], "cole_nombre_sede", "sede")  # Nombre de la sede
             .join(moda(con_sede, ["cole_cod_dane_sede"], "cole_cod_dane_establecimiento", "cod_establecimiento"),  # Establecimiento
                   "cole_cod_dane_sede", "left")  # Une
             .join(moda(con_sede, ["cole_cod_dane_sede"], "cole_cod_mcpio_ubicacion", "cod_mcpio"),  # Municipio
                   "cole_cod_dane_sede", "left")  # Une
             .withColumnRenamed("cole_cod_dane_sede", "cod_sede"))  # Llave primaria
    sedes_periodo = (moda(con_sede, ["cole_cod_dane_sede", "periodo"], "cole_area_ubicacion", "zona")  # Zona de la sede en cada periodo
                     .withColumnRenamed("cole_cod_dane_sede", "cod_sede"))  # Llave compuesta (cod_sede, periodo)
    resultados = con_sede.select(  # Hechos: una fila por estudiante
        "estu_consecutivo", "periodo", F.col("cole_cod_dane_sede").alias("cod_sede"),  # Llave, periodo y sede
        F.col("fami_estratovivienda").alias("estrato"), *PUNTAJES)  # Estrato y puntajes
    return {"departamentos": departamentos, "municipios": municipios, "establecimientos": establecimientos,  # Catálogos
            "sedes": sedes, "sedes_periodo": sedes_periodo, "resultados": resultados}  # Sedes y hechos


CHEQUEOS_SQL = {  # Consultas de integridad: todas deben dar 0
    "pk_repetida_departamentos": "SELECT COUNT(*) - COUNT(DISTINCT cod_depto) FROM departamentos",  # Llave única
    "pk_repetida_municipios": "SELECT COUNT(*) - COUNT(DISTINCT cod_mcpio) FROM municipios",  # Llave única
    "pk_repetida_establecimientos": "SELECT COUNT(*) - COUNT(DISTINCT cod_establecimiento) FROM establecimientos",  # Llave única
    "pk_repetida_sedes": "SELECT COUNT(*) - COUNT(DISTINCT cod_sede) FROM sedes",  # Llave única
    "pk_repetida_sedes_periodo": "SELECT COUNT(*) - COUNT(DISTINCT cod_sede, periodo) FROM sedes_periodo",  # Llave compuesta única
    "pk_repetida_resultados": "SELECT COUNT(*) - COUNT(DISTINCT estu_consecutivo) FROM resultados",  # Un estudiante, una fila
    "fk_huerfanos_resultados_sedes_periodo": "SELECT COUNT(*) FROM resultados r LEFT ANTI JOIN sedes_periodo s "  # Resultados sin sede-periodo
                                             "ON r.cod_sede = s.cod_sede AND r.periodo = s.periodo",  # Por llave compuesta
    "fk_huerfanos_sedes_establecimientos": "SELECT COUNT(*) FROM sedes s LEFT ANTI JOIN establecimientos e "  # Sedes sin establecimiento
                                           "ON s.cod_establecimiento = e.cod_establecimiento",  # Por código
    "fk_huerfanos_sedes_municipios": "SELECT COUNT(*) FROM sedes s LEFT ANTI JOIN municipios m ON s.cod_mcpio = m.cod_mcpio",  # Sedes sin municipio
    "fk_huerfanos_municipios_departamentos": "SELECT COUNT(*) FROM municipios m LEFT ANTI JOIN departamentos d "  # Municipios sin departamento
                                             "ON m.cod_depto = d.cod_depto",  # Por código
    "divipola_incumplida": "SELECT COUNT(*) FROM municipios WHERE substr(cod_mcpio, 1, 2) <> cod_depto",  # Regla DIVIPOLA
}

RECONSTRUCCION = """
SELECT r.estu_consecutivo, r.periodo, sp.zona, e.naturaleza, d.departamento, r.punt_global
FROM resultados r
JOIN sedes_periodo sp ON r.cod_sede = sp.cod_sede AND r.periodo = sp.periodo
JOIN sedes s ON r.cod_sede = s.cod_sede
JOIN establecimientos e ON s.cod_establecimiento = e.cod_establecimiento
JOIN municipios m ON s.cod_mcpio = m.cod_mcpio
JOIN departamentos d ON m.cod_depto = d.cod_depto
"""  # Vuelve a armar la tabla plana uniendo las seis tablas

EFECTO = """
WITH por_sede AS (
  SELECT sp.periodo, sp.cod_sede, sp.zona, COUNT(*) AS estudiantes, AVG(r.punt_global) AS media_sede
  FROM resultados r JOIN sedes_periodo sp ON r.cod_sede = sp.cod_sede AND r.periodo = sp.periodo
  GROUP BY sp.periodo, sp.cod_sede, sp.zona
)
SELECT periodo, zona,
       COUNT(*) AS sedes,
       SUM(estudiantes) AS estudiantes,
       ROUND(AVG(estudiantes), 1) AS estudiantes_por_sede,
       ROUND(SUM(media_sede * estudiantes) / SUM(estudiantes), 2) AS media_por_estudiante,
       ROUND(AVG(media_sede), 2) AS media_por_sede
FROM por_sede
GROUP BY periodo, zona
ORDER BY periodo, zona DESC
"""  # Compara contar estudiantes (filas) con contar sedes (colegios)

POR_DEPARTAMENTO = """
WITH sede_depto AS (
  SELECT sp.periodo, sp.cod_sede, sp.zona, d.departamento, COUNT(*) AS estudiantes
  FROM resultados r
  JOIN sedes_periodo sp ON r.cod_sede = sp.cod_sede AND r.periodo = sp.periodo
  JOIN sedes s ON r.cod_sede = s.cod_sede
  JOIN municipios m ON s.cod_mcpio = m.cod_mcpio
  JOIN departamentos d ON m.cod_depto = d.cod_depto
  WHERE r.periodo = '{periodo}'
  GROUP BY sp.periodo, sp.cod_sede, sp.zona, d.departamento
)
SELECT departamento,
       COUNT(*) AS sedes,
       ROUND(100 * AVG(CASE WHEN zona = 'RURAL' THEN 1 ELSE 0 END), 1) AS pct_sedes_rurales,
       SUM(estudiantes) AS estudiantes,
       ROUND(100 * SUM(CASE WHEN zona = 'RURAL' THEN estudiantes ELSE 0 END) / SUM(estudiantes), 1) AS pct_estudiantes_rurales
FROM sede_depto
GROUP BY departamento
ORDER BY pct_sedes_rurales DESC, departamento
"""  # Porcentaje rural por departamento, contando sedes y contando estudiantes


def grafica_efecto(deptos: pd.DataFrame, ruta: Path, periodo: str) -> None:
    """Barras horizontales: % de sedes rurales (modelo) frente a % de estudiantes rurales (filas)."""
    datos = deptos.sort_values("pct_sedes_rurales", kind="mergesort")  # Mayor porcentaje arriba
    alto = max(5, 0.3 * len(datos))  # Alto según el número de departamentos
    figura, eje = plt.subplots(figsize=(8, alto), facecolor=FONDO)  # Crea la figura
    y = range(len(datos))  # Posición de cada departamento
    eje.barh([v + 0.2 for v in y], datos["pct_sedes_rurales"], height=0.38, color=COLOR_SEDES,  # Barras de sedes
             label="% de sedes rurales (modelo 3FN)")  # Etiqueta
    eje.barh([v - 0.2 for v in y], datos["pct_estudiantes_rurales"], height=0.38, color=COLOR_FILAS,  # Barras de estudiantes
             label="% de estudiantes rurales (filas de la tabla plana)")  # Etiqueta
    eje.set_yticks(list(y), datos["departamento"].str.title())  # Nombres de los departamentos
    eje.set_facecolor(FONDO)  # Fondo
    for lado in ("top", "right"):  # Bordes superior y derecho
        eje.spines[lado].set_visible(False)  # Se ocultan
    eje.grid(axis="x", color=REJILLA, linewidth=0.8)  # Rejilla vertical
    eje.set_axisbelow(True)  # Rejilla detrás de las barras
    eje.tick_params(colors=TINTA_2, labelsize=8)  # Marcas en gris
    eje.set_xlabel("Participación rural (%)", color=TINTA_2)  # Eje horizontal
    eje.set_title(f"Contar sedes o contar filas, Saber 11 {periodo}", color=TINTA, loc="left")  # Título
    eje.legend(frameon=False, labelcolor=TINTA, loc="lower right", fontsize=8)  # Leyenda
    figura.tight_layout()  # Ajusta márgenes
    figura.savefig(ruta, dpi=150, facecolor=FONDO, metadata={"Software": None})  # Guarda sin metadatos variables
    plt.close(figura)  # Libera memoria


def main() -> int:
    """Ejecuta el diagnóstico, la normalización, la verificación y la comparación de cifras."""
    lector = argparse.ArgumentParser(description=__doc__)  # Lector de argumentos
    lector.add_argument("--periodos", nargs="+", default=["20194", "20224"])  # Periodos a modelar
    lector.add_argument("--datos", default="datos")  # Carpeta de los CSV
    lector.add_argument("--salidas", default="salidas")  # Carpeta base de salidas
    args = lector.parse_args()  # Lee los argumentos
    carpeta = Path(args.salidas) / "modelo"  # Carpeta de salida del modelo
    carpeta.mkdir(parents=True, exist_ok=True)  # La crea si no existe
    reciente = max(args.periodos)  # Periodo para la gráfica por departamento
    inicio = time.time()  # Momento de inicio

    spark = iniciar_spark()  # Abre la SparkSession
    print(f"== Modelo en 3FN con PySpark {spark.version} (periodos {', '.join(args.periodos)}) ==")  # Encabezado

    plana = limpiar_codigos(leer_plana(spark, Path(args.datos), args.periodos))  # Transformaciones perezosas: nada se ejecuta aún
    print(f"Particiones de la tabla plana: {plana.rdd.getNumPartitions()}")  # Unidad de paralelismo de Spark
    registro = {"spark": spark.version, "periodos": args.periodos}  # Registro del proceso

    # --- 1FN: llave primaria y filas repetidas ---
    sin_copias, unica, valida = primera_forma_normal(plana)  # Pasos de la 1FN
    valida = valida.cache()  # Guarda en memoria la tabla limpia, que se usa muchas veces
    valida.count()  # Acción: llena la memoria ahora
    conteos = (plana.groupBy("periodo").agg(F.count("*").alias("filas_plana"),  # Acción al final: filas por periodo
                                            F.countDistinct("estu_consecutivo").alias("estudiantes_distintos"))  # Llaves distintas
               .join(sin_copias.groupBy("periodo").count().withColumnRenamed("count", "sin_copias_identicas"), "periodo")  # Tras quitar copias
               .join(valida.groupBy("periodo").count().withColumnRenamed("count", "validos_para_analisis"), "periodo")  # Tras filtros
               .join(valida.groupBy("periodo").agg(F.sum(F.col("cole_cod_dane_sede").isNull().cast("int")).alias("sin_codigo_sede")),  # Sin sede
                     "periodo")  # Une por periodo
               .orderBy("periodo").toPandas())  # Acción: trae un resumen pequeño a pandas
    print("\n-- 1FN: una fila por estudiante --")  # Título
    print(conteos.to_string(index=False))  # Imprime los conteos
    registro["primera_forma_normal"] = conteos.to_dict(orient="records")  # Guarda en el registro
    sin_copias.unpersist()  # Libera la memoria del paso intermedio; ya solo se usa la tabla limpia

    # --- Calidad de los códigos (dominio) ---
    codigos = valida.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in CODIGOS]).toPandas()  # Códigos vacíos o inválidos
    print("\n-- Códigos vacíos o con caracteres no numéricos --")  # Título
    print(codigos.to_string(index=False))  # Imprime
    registro["codigos_invalidos"] = codigos.iloc[0].astype(int).to_dict()  # Guarda

    # --- 2FN y 3FN: dependencias funcionales ---
    dependencias = probar_dependencias(valida)  # Prueba cada dependencia
    print("\n-- Dependencias funcionales (X -> Y) --")  # Título
    print(dependencias.to_string(index=False))  # Imprime
    dependencias.to_csv(carpeta / "dependencias.csv", index=False, lineterminator="\n")  # Guarda
    divipola = valida.filter(F.col("cole_cod_mcpio_ubicacion").substr(1, 2) != F.col("cole_cod_depto_ubicacion"))  # Municipio en otro depto
    registro["divipola_tabla_plana"] = {  # Incumplimientos de la regla DIVIPOLA en la tabla plana
        "municipios": divipola.select("cole_cod_mcpio_ubicacion").distinct().count(),  # Municipios afectados
        "estudiantes": divipola.count()}  # Estudiantes afectados
    print(f"\nRegla DIVIPOLA incumplida en la tabla plana: {registro['divipola_tabla_plana']}")  # Imprime

    # --- Construcción del modelo, guardado en Parquet y vistas SQL ---
    modelo = construir_modelo(valida)  # Seis tablas (transformaciones perezosas)
    filas_modelo = {}  # Filas de cada tabla
    for nombre, tabla in modelo.items():  # Recorre las tablas
        destino = carpeta / "parquet" / nombre  # Carpeta Parquet de la tabla
        tabla.write.mode("overwrite").parquet(str(destino))  # Acción: escribe la tabla en Parquet
        guardada = spark.read.parquet(str(destino))  # La vuelve a leer desde disco
        guardada.createOrReplaceTempView(nombre)  # La registra como vista para consultarla con SQL
        filas_modelo[nombre] = guardada.count()  # Acción: cuenta sus filas
    print("\n-- Tablas del modelo en 3FN (Parquet) --")  # Título
    for nombre, n in filas_modelo.items():  # Recorre las tablas
        print(f"{nombre:<18}{n:>10,}")  # Imprime el nombre y sus filas
    registro["filas_modelo"] = filas_modelo  # Guarda

    # --- Integridad con Spark SQL ---
    chequeos = {nombre: int(spark.sql(sql).collect()[0][0]) for nombre, sql in CHEQUEOS_SQL.items()}  # Ejecuta cada consulta
    print("\n-- Integridad verificada con Spark SQL (todo debe ser 0) --")  # Título
    for nombre, valor in chequeos.items():  # Recorre los chequeos
        print(f"{nombre:<42}{valor:>6}")  # Imprime el resultado
    registro["integridad"] = chequeos  # Guarda

    # --- Reconstrucción: ¿el modelo devuelve la misma tabla? ---
    reconstruida = spark.sql(RECONSTRUCCION)  # Une las seis tablas
    reconstruida.createOrReplaceTempView("reconstruida")  # Vista para comparar con SQL
    valida.createOrReplaceTempView("plana")  # La tabla plana también como vista
    comparacion = spark.sql("""
        SELECT r.periodo,
               COUNT(*) AS filas_reconstruidas,
               SUM(CASE WHEN r.zona <> p.cole_area_ubicacion THEN 1 ELSE 0 END) AS zona_distinta,
               SUM(CASE WHEN r.naturaleza <> p.cole_naturaleza THEN 1 ELSE 0 END) AS naturaleza_distinta,
               SUM(CASE WHEN r.departamento <> p.cole_depto_ubicacion THEN 1 ELSE 0 END) AS departamento_distinto
        FROM reconstruida r JOIN plana p ON r.estu_consecutivo = p.estu_consecutivo
        GROUP BY r.periodo ORDER BY r.periodo
    """).toPandas()  # Compara estudiante por estudiante
    print("\n-- Reconstrucción con JOIN frente a la tabla plana --")  # Título
    print(comparacion.to_string(index=False))  # Imprime
    registro["reconstruccion"] = comparacion.to_dict(orient="records")  # Guarda
    plan = spark.sql("EXPLAIN FORMATTED " + RECONSTRUCCION).collect()[0][0]  # Plan que arma Catalyst para la consulta
    (carpeta / "plan_reconstruccion.txt").write_text(plan + "\n", encoding="utf-8")  # Lo guarda para mostrarlo

    # --- Brecha recalculada con SQL sobre el modelo ---
    brecha = spark.sql("""
        SELECT periodo,
               ROUND(AVG(CASE WHEN zona = 'URBANO' THEN punt_global END), 2) AS media_urbano,
               ROUND(AVG(CASE WHEN zona = 'RURAL' THEN punt_global END), 2) AS media_rural,
               ROUND(AVG(CASE WHEN zona = 'URBANO' THEN punt_global END)
                     - AVG(CASE WHEN zona = 'RURAL' THEN punt_global END), 2) AS brecha
        FROM reconstruida GROUP BY periodo ORDER BY periodo
    """).toPandas()  # Media urbana, rural y brecha por periodo
    print("\n-- Brecha calculada con SQL sobre el modelo --")  # Título
    print(brecha.to_string(index=False))  # Imprime
    brecha.to_csv(carpeta / "brecha_modelo.csv", index=False, lineterminator="\n")  # Guarda

    # --- Tabla plana frente al modelo: los mismos indicadores contados de las dos formas ---
    plana_cuenta = spark.sql("""
        SELECT COUNT(DISTINCT cole_depto_ubicacion) AS deptos_nombre,
               COUNT(DISTINCT cole_cod_depto_ubicacion) AS deptos_codigo,
               COUNT(DISTINCT cole_mcpio_ubicacion) AS mcpios_nombre,
               COUNT(DISTINCT cole_cod_mcpio_ubicacion) AS mcpios_codigo,
               COUNT(DISTINCT CASE WHEN substr(cole_cod_mcpio_ubicacion, 1, 2) <> cole_cod_depto_ubicacion
                                   THEN cole_cod_mcpio_ubicacion END) AS mcpios_divipola
        FROM plana
    """).collect()[0]  # Conteos sobre la tabla plana (por nombre y por código)
    brecha_plana = spark.sql("""
        SELECT periodo, ROUND(AVG(CASE WHEN cole_area_ubicacion = 'URBANO' THEN punt_global END)
                              - AVG(CASE WHEN cole_area_ubicacion = 'RURAL' THEN punt_global END), 2) AS brecha
        FROM plana GROUP BY periodo ORDER BY periodo
    """).toPandas().set_index("periodo")["brecha"]  # Brecha con la zona tal como viene en cada fila
    filas_plana_total = int(conteos["filas_plana"].sum())  # Filas de la tabla plana original, con repetidos
    indicadores = [  # Cada indicador medido en la tabla plana y en el modelo
        ("Filas (observaciones)", filas_plana_total, filas_modelo["resultados"]),  # Filas con repetidos frente a estudiantes únicos
        ("Departamentos (por nombre / por código)", f"{plana_cuenta.deptos_nombre} / {plana_cuenta.deptos_codigo}",  # Nombres y códigos
         filas_modelo["departamentos"]),  # Filas de la tabla departamentos
        ("Municipios (por nombre / por código)", f"{plana_cuenta.mcpios_nombre} / {plana_cuenta.mcpios_codigo}",  # Nombres y códigos
         filas_modelo["municipios"]),  # Filas de la tabla municipios
        ("Municipios que incumplen DIVIPOLA", plana_cuenta.mcpios_divipola, chequeos["divipola_incumplida"]),  # Regla de códigos
    ] + [(f"Brecha urbano - rural {p}", float(brecha_plana[p]),  # Brecha con la zona de cada fila
          float(brecha.set_index("periodo").loc[p, "brecha"])) for p in brecha["periodo"]]  # Brecha con la zona de la sede
    indicadores = pd.DataFrame(indicadores, columns=["indicador", "tabla_plana", "modelo_3fn"], dtype=object)  # Sin forzar a decimales
    print("\n-- Tabla plana frente al modelo 3FN --")  # Título
    print(indicadores.to_string(index=False))  # Imprime
    indicadores.to_csv(carpeta / "indicadores_plana_vs_3fn.csv", index=False, lineterminator="\n")  # Guarda

    # --- Efecto de normalizar: contar sedes en vez de filas ---
    efecto = spark.sql(EFECTO).toPandas()  # Sedes, estudiantes y medias por zona y periodo
    print("\n-- Contar sedes o contar estudiantes --")  # Título
    print(efecto.to_string(index=False))  # Imprime
    efecto.to_csv(carpeta / "efecto_sedes.csv", index=False, lineterminator="\n")  # Guarda
    deptos = spark.sql(POR_DEPARTAMENTO.format(periodo=reciente)).toPandas()  # Porcentajes por departamento
    deptos.to_csv(carpeta / f"rural_departamento_{reciente}.csv", index=False, lineterminator="\n")  # Guarda
    print(f"\n-- Departamentos con mayor diferencia entre % de sedes y % de estudiantes rurales ({reciente}) --")  # Título
    deptos["diferencia"] = (deptos["pct_sedes_rurales"] - deptos["pct_estudiantes_rurales"]).round(1)  # Puntos de diferencia
    print(deptos.sort_values("diferencia", ascending=False, kind="mergesort").head(8).to_string(index=False))  # Imprime
    grafica_efecto(deptos.drop(columns="diferencia"), carpeta / "efecto_normalizacion.png", reciente)  # Gráfica

    # --- Registro y huellas ---
    registro["segundos"] = round(time.time() - inicio, 1)  # Duración total
    (carpeta / "registro.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False, default=str) + "\n",  # Guarda el registro
                                           encoding="utf-8")  # En UTF-8
    print("\n-- Huellas SHA-256 (resúmenes; los Parquet de Spark cambian de nombre en cada escritura) --")  # Título
    for archivo in sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix in {".csv", ".png"}):  # Resúmenes y gráfica
        print(f"{huella(archivo)}  {archivo.name}")  # Imprime la huella
    print(f"\nTiempo total: {registro['segundos']} s")  # Duración
    spark.stop()  # Cierra la SparkSession y libera la memoria
    return 0  # Termina sin error


if __name__ == "__main__":  # Solo si el archivo se corre directamente
    sys.exit(main())  # Ejecuta main
