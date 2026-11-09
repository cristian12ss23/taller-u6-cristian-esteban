# Proyecto: Brecha rural vs urbana en Saber 11

## Pregunta de análisis
¿Cuántos puntos de diferencia hay en Saber 11 entre los estudiantes de colegios urbanos y rurales en Colombia? ¿La brecha se mantiene cuando se compara dentro del mismo tipo de colegio (oficial o no oficial) y del mismo estrato? ¿En qué departamentos es más grande? ¿Cambió entre 2019, antes de la pandemia, y 2022? ¿Cómo cambian las cifras cuando la tabla plana se normaliza hasta la tercera forma normal (3FN) y se cuentan colegios en vez de filas?

El resultado sirve para orientar dónde focalizar programas e inversión en la educación rural.

## Fuente de datos
- Conjunto: Resultados únicos Saber 11
- Entidad: ICFES, publicado en datos.gov.co
- Enlace: https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe
- Licencia: Creative Commons Atribución-CompartirIgual 4.0 Internacional (CC BY-SA 4.0)
- Periodos analizados: `20224` (2022, calendario A, el más reciente del conjunto) y `20194` (2019, calendario A, antes de la pandemia)

Los datos se descargan con la API pública de datos.gov.co, filtrados por periodo y solo con las columnas necesarias. No se versionan: se regeneran con el contenedor.

**Calidad de los datos.** En los periodos 20194 y 20224 el conjunto trae repetida a casi toda la población. En 20224 hay 1.065.888 filas; 2 no traen puntaje o zona, y de las otras 1.065.886 se quitan 533.095 copias idénticas, de modo que quedan 532.791 estudiantes. En 20194 se pasa de 1.096.524 filas a 546.211 estudiantes. No hubo ningún identificador repetido con datos distintos. La primera versión de este análisis no quitaba los repetidos: contaba 1.065.886 estudiantes y un intervalo de confianza de 26,00 a 26,48. Ya sin ellos, el intervalo es de 25,90 a 26,58. Los promedios no cambiaron, pero los conteos sí, y la precisión estaba sobrestimada.

**Datos faltantes.** El puntaje global y las áreas están casi completos.
- **Estrato:** falta en el 6,7 % de los estudiantes de 2022 (6,5 % de los urbanos y 8,0 % de los rurales) y en el 6,3 % de los de 2019. Se conservan en la categoría `SIN DATO`, distinta de `Sin Estrato`, que sí es una respuesta registrada.
- **Inglés:** en 2022 falta en 1.463 rurales (1,6 %) y 514 urbanos (0,1 %), frente a solo 19 estudiantes en 2019. Como falta más entre los rurales, la brecha de inglés de 2022 debe leerse con algo de cautela.

## Variables
| Variable | Uso |
|---|---|
| `estu_consecutivo` | Identificador del estudiante (para quitar repetidos) |
| `cole_area_ubicacion` | Zona del colegio: URBANO o RURAL (variable de comparación) |
| `punt_global` | Puntaje global, 0 a 500 (variable principal) |
| `punt_matematicas`, `punt_lectura_critica`, `punt_c_naturales`, `punt_sociales_ciudadanas`, `punt_ingles` | Puntajes por área, 0 a 100 |
| `cole_naturaleza` | OFICIAL o NO OFICIAL (para comparar dentro del mismo tipo de colegio) |
| `fami_estratovivienda` | Estrato del estudiante (para comparar dentro del mismo estrato) |
| `cole_depto_ubicacion` | Departamento (para ver dónde la brecha es mayor) |
| `cole_cod_dane_sede`, `cole_nombre_sede` | Código DANE y nombre de la sede (llave del modelo en 3FN) |
| `cole_cod_dane_establecimiento`, `cole_nombre_establecimiento` | Código DANE y nombre del establecimiento educativo |
| `cole_cod_mcpio_ubicacion`, `cole_mcpio_ubicacion`, `cole_cod_depto_ubicacion` | Códigos DIVIPOLA y nombre del municipio, y código del departamento |

## Método
1. `src/descargar.py` descarga el periodo y lo guarda en `datos/` ordenado de forma fija, para que dos descargas iguales tengan la misma huella SHA-256.
2. `src/analisis.py` quita los estudiantes repetidos, limpia los puntajes y calcula, en `salidas/<periodo>/`:
   - Resumen por zona: estudiantes, media, mediana y desviación del puntaje global, y media por área.
   - Brecha urbano − rural según tipo de colegio, estrato y departamento (departamentos con al menos 100 estudiantes rurales).
   - Prueba t de Welch, intervalo de confianza del 95 % de la diferencia y tamaño del efecto (d de Cohen).
   - Tres gráficas: distribución del puntaje global, promedio por área y brecha por departamento.
   - `manifiesto.json` con las filas quitadas, la huella SHA-256 de los datos y de cada salida, y las versiones de las bibliotecas.
3. `src/comparar.py` pone lado a lado los dos periodos en `salidas/comparacion/`: brecha global y por área, por tipo de colegio y por departamento, con dos gráficas.
4. `src/profundizar.py` escribe en `salidas/profundizacion/` lo que los pasos anteriores no responden: la brecha dentro del mismo tipo de colegio y estrato a la vez, el intervalo de confianza de cada departamento y el conteo de datos faltantes. También guarda los datos limpios en Parquet y comprueba la conversión. No cambia las salidas de los pasos 2 y 3, así que sus huellas siguen siendo válidas.
5. `src/modelo_3fn.py` corre con **PySpark** en su propia imagen (`Dockerfile.spark`) y escribe en `salidas/modelo/`: diagnostica qué impide cada forma normal, descompone la tabla plana en seis tablas en 3FN guardadas en Parquet, verifica llaves e integridad con **Spark SQL**, reconstruye la tabla plana con `JOIN` para comprobar que no se pierde ni cambia nada, y compara las cifras al contar sedes en vez de filas. Ver la sección 12.

Una copia de las gráficas está en `figuras/` para mostrarlas en este README.

## Técnicas y herramientas del curso
Esto es lo que se usó de Computación en la Nube para Análisis de Datos y para qué sirvió en este proyecto.

| Técnica o herramienta | Qué se hizo | Cómo ayudó | Dónde se ve |
|---|---|---|---|
| **Git** (control de versiones) | Cada cambio se registró como una confirmación con autor, fecha y mensaje. | La primera versión contaba 1.065.886 estudiantes, con repetidos. La corrección quedó en otra confirmación, así que se puede comparar el antes y el después. | `git log`, confirmaciones `647cc0d` y `d997e0a` |
| **GitHub** | El repositorio público guarda el código y el README con las gráficas. | Los dos integrantes trabajaron sobre la misma versión del proyecto, sin pasarse copias por correo, y cualquiera puede revisarlo. | Este repositorio |
| **Codespaces** (máquina en la nube) | El proyecto se construye y se ejecuta en un computador de GitHub, desde el navegador. | Más de un millón de filas por periodo se descargan y procesan sin instalar nada ni depender del computador de cada integrante. Si la máquina falla, se reconstruye y los archivos siguen ahí. | `Cómo reproducir` |
| **Docker: imagen y Dockerfile** | La imagen fija Python 3.12, las bibliotecas y el código. El periodo se elige al ejecutar, con `-e PERIODO`. | 2019 y 2022 se analizan con la misma imagen. Si la brecha cambia, la causa no es una diferencia de código ni de versiones. | `Dockerfile`, `ejecutar.sh` |
| **Docker: volúmenes** | `datos/` y `salidas/` se conectan al contenedor con `--volume`. | El contenedor se desecha al terminar, pero los resultados quedan. Además, la descarga de varios minutos no se repite. | `Cómo reproducir` |
| **Docker: capas y privilegio mínimo** | `requirements.txt` se copia antes que el código y el contenedor corre con el usuario `analista`, sin permisos de administrador. | Cambiar el código no obliga a reinstalar las bibliotecas, y el proceso solo tiene los permisos que necesita. | `Dockerfile` |
| **Versiones fijadas** | Cada biblioteca lleva su versión exacta con `==`. | La imagen instala lo mismo sin importar cuándo se construya. | `requirements.txt` |
| **Huellas SHA-256 y manifiesto** | Se calcula la huella de los datos y de cada salida. Los datos se ordenan de forma fija antes de guardarlos. | Permite comprobar si otra ejecución dio exactamente lo mismo, y avisa si la fuente cambió. En un Codespace reconstruido, `salidas/20194/resumen_zona.csv` volvió a dar la huella de referencia. La huella detecta los cambios, pero no recupera los datos anteriores, porque no se guarda una copia. | `manifiesto.json`, `Huellas de referencia` |
| **`.gitignore`** | Los datos y las salidas no entran al repositorio. | Se versiona la receta y no el resultado, de modo que el repositorio se mantiene liviano. | `.gitignore` |
| **Datos abiertos e ingesta por API** | La descarga va por páginas de 50.000 filas, con hasta 5 reintentos, solo 12 columnas y reutilizando el CSV si ya existe. | Una falla momentánea de red se reintenta sin perder lo ya descargado, se baja solo lo necesario y repetir el comando no duplica datos. | `src/descargar.py` |
| **Calidad y zonas de datos** | Se separa el CSV original, los datos limpios y los resultados. Se revisó la fuente antes de analizar. | Revisar los identificadores mostró que los conteos estaban casi duplicados, y se corrigió antes de comparar 2019 con 2022. | `src/analisis.py`, `Calidad de los datos` |
| **Modelado y normalización (1FN, 2FN, 3FN)** | Se probaron 10 dependencias funcionales en los datos y la tabla plana se descompuso en seis tablas con llaves primarias y foráneas. | Mostró que contar filas mide estudiantes y no colegios, que 83 nombres de municipio se repiten entre municipios distintos y que la zona de 66 sedes cambió entre 2019 y 2022. | `src/modelo_3fn.py`, sección 12 |
| **PySpark** | `SparkSession` local, lectura perezosa del CSV, transformaciones (`filter`, `groupBy`, `join`, `withColumn`), acciones (`count`, `toPandas`), `cache` y 4 particiones. | Procesa 2,16 millones de filas en unos 2,5 minutos en el Codespace, y el mismo código corre en un clúster o en Databricks cambiando solo la configuración de la sesión. | `src/modelo_3fn.py`, `Dockerfile.spark` |
| **Spark SQL** | Las tablas se registran como vistas y se consultan con SQL: llaves repetidas, `LEFT ANTI JOIN` para huérfanos, regla DIVIPOLA, reconstrucción con `JOIN` y `EXPLAIN FORMATTED`. | Como Spark no hace cumplir llaves primarias ni foráneas, la integridad se comprueba con consultas: las 11 dan 0. | `salidas/modelo/plan_reconstruccion.txt` |
| **Parquet** | El resumen y los datos limpios se guardan en Parquet. Se comparan filas, columnas, vacíos y suma del puntaje antes de aceptar la conversión. | En 20224 se pasa de 80,7 MB (CSV con repetidos) a 6,4 MB (Parquet sin repetidos), con lectura por columnas. Las cuatro comprobaciones pasaron en los dos periodos. | `src/profundizar.py`, `registro.json` |

**Herramientas del curso que no se usaron.** Databricks y Cassandra no hacen parte de este proyecto. El modelo en 3FN corre con PySpark dentro de Docker, en el Codespace, para que cualquiera lo reproduzca con dos comandos y sin cuenta en otra plataforma; el mismo código corre en Databricks, donde las tablas se guardarían como tablas Delta con `saveAsTable`. Cassandra está pensada para consultar por clave, y aquí el trabajo consiste en agrupar y resumir todos los datos.

Para el análisis estadístico se usaron pandas, scipy y matplotlib; para el modelo en 3FN, PySpark y Spark SQL.

## Cómo reproducir
Desde la raíz del repositorio, en el codespace:

```bash
docker build --tag proyecto:0.5 proyecto/

# 2022
docker run --rm -e PERIODO=20224 \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.5

# 2019
docker run --rm -e PERIODO=20194 \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.5

# Comparación
docker run --rm --entrypoint python \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.5 src/comparar.py

# Profundización (usa los CSV de datos/)
docker run --rm --entrypoint python \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.5 src/profundizar.py

# Modelo en 3FN con PySpark (usa los CSV de datos/)
docker build --file proyecto/Dockerfile.spark --tag proyecto-spark:1.0 proyecto/
docker run --rm \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto-spark:1.0
```

Cada descarga trae cerca de un millón de filas y tarda varios minutos. Las ejecuciones siguientes reutilizan los CSV de `datos/`. Si aparece `docker: command not found`, la solución está en "Incidencias en M0" de `INFORME.md`.

## Resultados 2022 (periodo 20224)

Se analizaron **532.791 estudiantes**: 441.577 de colegios urbanos y 91.214 de colegios rurales.

### 1. La brecha general es de 26 puntos
| Zona | Estudiantes | Media global | Mediana | Desv. estándar |
|---|---|---|---|---|
| Urbano | 441.577 | 254,63 | 252 | 51,58 |
| Rural | 91.214 | 228,39 | 222 | 47,39 |
| **Brecha (U − R)** | | **26,24** | **30** | |

- Prueba t de Welch: diferencia de 26,24 puntos, intervalo de confianza del 95 % entre 25,90 y 26,58, valor p menor que 0,001. La diferencia no se explica por azar.
- Tamaño del efecto: d de Cohen = 0,52, un efecto **mediano**. La brecha es real y además importante en la práctica.

![Distribución del puntaje global por zona](figuras/distribucion_global.png)

### 2. Todas las áreas muestran brecha; la mayor es en inglés
| Área | Urbano | Rural | Brecha |
|---|---|---|---|
| Inglés | 51,01 | 44,25 | **6,76** |
| Lectura crítica | 53,75 | 48,18 | 5,57 |
| Matemáticas | 51,51 | 46,12 | 5,40 |
| Sociales | 48,60 | 43,34 | 5,27 |
| C. naturales | 49,81 | 45,58 | 4,23 |

![Promedio por área según zona del colegio](figuras/medias_por_area.png)

### 3. Según el tipo de colegio, la brecha cambia de sentido
| Tipo de colegio | Estudiantes rurales | Media urbano | Media rural | Brecha |
|---|---|---|---|---|
| Oficial | 85.886 | 248,61 | 224,50 | **24,11** |
| No oficial | 5.328 | 271,69 | 291,12 | **−19,43** |

En los colegios oficiales, que concentran el 94 % de los estudiantes rurales, la brecha es de 24 puntos. En los no oficiales se invierte: los rurales sacan 19 puntos más. Son solo 5.328 estudiantes, y una posible explicación (por verificar) es que en ese grupo hay colegios privados campestres ubicados en zona rural cerca de las ciudades.

### 4. La brecha general crece con el estrato, pero mezcla tipos de colegio
| Estrato | Brecha |
|---|---|
| Sin estrato | 13,54 |
| Estrato 1 | 14,25 |
| Estrato 2 | 21,12 |
| Estrato 3 | 30,37 |
| Estrato 4 | 40,92 |
| Estrato 5 | 42,64 |
| Estrato 6 | 43,79 |

El puntaje rural se mantiene casi plano (entre 205 y 236) sin importar el estrato, mientras que el urbano sube con el estrato. Por eso la brecha es pequeña en estrato 1 y grande en los estratos altos. Esta tabla no separa el tipo de colegio, y la sección 10 muestra que eso cambia la lectura de los estratos altos.

### 5. Por departamento
- **Mayor brecha:** Guainía (55,90), San Andrés (44,33), Amazonas (36,89), Sucre (34,09) y La Guajira (33,70).
- **Menor brecha:** Valle (12,65), Meta (5,93) y Bogotá (3,63). En Cundinamarca (−3,64) y Quindío (−8,15) los rurales superan a los urbanos.

La brecha mayor no indica dónde están la mayoría de los estudiantes afectados, y por eso conviene mirar también su precisión y su peso:

| Departamento | Estudiantes rurales | % de los rurales | Brecha | IC 95 % |
|---|---|---|---|---|
| Guainía | 190 | 0,21 % | 55,90 | 48,00 a 63,79 |
| San Andrés | 263 | 0,29 % | 44,33 | 36,71 a 51,95 |
| Amazonas | 209 | 0,23 % | 36,89 | 32,08 a 41,70 |
| Antioquia | 12.539 | 13,75 % | 21,83 | 20,88 a 22,77 |
| Córdoba | 8.514 | 9,33 % | 24,45 | 23,23 a 25,68 |
| Cauca | 5.797 | 6,36 % | 27,12 | 25,63 a 28,61 |
| Bolívar | 5.310 | 5,82 % | 29,06 | 27,84 a 30,28 |
| Nariño | 4.563 | 5,00 % | 27,20 | 25,55 a 28,84 |

- Guainía, San Andrés y Amazonas tienen las brechas más altas, pero juntos suman 662 rurales, el 0,7 % del total. Además, sus intervalos se traslapan, así que el orden exacto entre ellos no es firme.
- Multiplicando la brecha por el número de rurales, Antioquia, Córdoba, Cauca, Bolívar y Nariño concentran el 46 % de los puntos de diferencia, entre los departamentos con brecha positiva. Tienen el 40 % de los rurales.
- En Bogotá el intervalo incluye el cero (−0,11 a 7,37), así que su brecha no es clara.

La tabla completa de los 33 departamentos queda en `salidas/profundizacion/brecha_departamento_ic.csv`.

![Brecha urbano − rural por departamento](figuras/brecha_departamento.png)

## Comparación 2019 vs 2022

### 6. La brecha creció 2,5 puntos
| Periodo | Estudiantes | Media urbano | Media rural | Brecha | IC 95 % | d de Cohen |
|---|---|---|---|---|---|---|
| 2019 (20194) | 546.211 | 249,91 | 226,22 | 23,69 | 23,34 a 24,04 | 0,47 |
| 2022 (20224) | 532.791 | 254,63 | 228,39 | **26,24** | 25,90 a 26,58 | 0,52 |

El aumento fue de 2,55 puntos, con un intervalo de confianza del 95 % de 2,06 a 3,04, calculado a partir de los intervalos de cada año. Como no incluye el cero, el aumento es estadísticamente claro. Los dos grupos subieron su puntaje promedio entre 2019 y 2022, pero el urbano subió 4,72 puntos y el rural solo 2,17. Por eso la distancia entre ellos aumentó.

### 7. La brecha creció en todas las áreas
| Área | Brecha 2019 | Brecha 2022 | Cambio |
|---|---|---|---|
| Lectura crítica | 4,73 | 5,57 | +0,84 |
| Inglés | 6,17 | 6,76 | +0,59 |
| Matemáticas | 4,82 | 5,40 | +0,58 |
| Sociales | 4,88 | 5,27 | +0,39 |
| C. naturales | 4,05 | 4,23 | +0,18 |

![Brecha por área, 2019 vs 2022](figuras/brecha_por_area_periodos.png)

### 8. Por tipo de colegio y estrato
- En los colegios **oficiales**, que tienen el 94 % de los rurales, la brecha pasó de 22,88 a 24,11 (+1,23), menos de la mitad del aumento general de 2,55. La sección 10 revisa cuánto del aumento queda al comparar dentro de los mismos grupos.
- En los **no oficiales** los rurales siguen por encima, pero la ventaja bajó de 27,39 a 19,43 puntos.
- La brecha creció en **todos los estratos**; por ejemplo, en estrato 1 pasó de 12,03 a 14,25 y en estrato 3 de 26,74 a 30,37.

### 9. Por departamento
La brecha creció en **26 de los 32 departamentos** comparados.
- **Mayor aumento:** Casanare (+11,64), Bogotá (+9,54), La Guajira (+7,75), Amazonas (+7,26) y Nariño (+6,19).
- **Se redujo en 6:** Valle (−4,44), Quindío (−3,69), Chocó (−3,58), Putumayo (−1,05), Arauca (−0,18) y Guainía (cambio muy pequeño, cerca de −0,1 en la gráfica).

Bogotá tiene pocos estudiantes rurales (alrededor de 600 por año), así que su cambio debe leerse con cuidado.

![Cambio de la brecha por departamento, 2019 a 2022](figuras/cambio_departamento.png)

## Comparación dentro del mismo tipo de colegio y estrato

### 10. Quedan 17,5 de los 26,2 puntos
La brecha general mezcla dos cosas: la diferencia entre zonas y el hecho de que urbanos y rurales no se reparten igual entre tipos de colegio y estratos. Para separarlas, se calcula la brecha dentro de cada grupo y se promedia con el peso que ese grupo tiene entre los rurales de 2022.

Por ejemplo, con solo el tipo de colegio en 2022:

(85.886 × 24,11 + 5.328 × (−19,43)) / 91.214 = **21,57 puntos**

| Comparación | Brecha 2019 | Brecha 2022 | IC 95 % (2022) | Cambio | IC 95 % del cambio |
|---|---|---|---|---|---|
| Sin ajustar | 23,69 | **26,24** | 25,90 a 26,58 | +2,55 | 2,06 a 3,04 |
| Mismo tipo de colegio | 19,94 | 21,57 | 21,24 a 21,90 | +1,62 | 1,15 a 2,09 |
| Mismo estrato | 17,65 | 20,84 | 20,50 a 21,19 | +3,20 | 2,70 a 3,70 |
| Mismo tipo y estrato | 16,32 | **17,52** | 17,19 a 17,85 | **+1,20** | 0,72 a 1,67 |

- **La brecha se mantiene, pero es menor.** Dentro del mismo tipo de colegio y estrato quedan 17,52 puntos. Los otros 8,72 (el 33 %) corresponden a cómo se reparten urbanos y rurales entre esos grupos.
- **El aumento también se mantiene, pero es menor.** Con la misma comparación son 1,20 puntos, cerca de la mitad de los 2,55 generales. Es decir, parte del aumento viene de cambios en la composición de los grupos, y parte ocurre dentro de ellos. La reducción viene del tipo de colegio: si se iguala solo el estrato, el aumento sube a 3,20 puntos.

### 11. En los estratos altos, la brecha general engaña
Brecha urbano − rural en 2022, dentro de cada combinación:

| Estrato | Oficial | IC 95 % | No oficial | IC 95 % | Brecha general (sección 4) |
|---|---|---|---|---|---|
| Estrato 1 | 14,41 | 13,85 a 14,96 | −3,01 | −7,58 a 1,56 | 14,25 |
| Estrato 2 | 20,57 | 19,93 a 21,20 | −13,32 | −16,53 a −10,12 | 21,12 |
| Estrato 3 | 32,92 | 31,92 a 33,91 | −17,70 | −20,13 a −15,28 | 30,37 |
| Estrato 4 | 35,48 | 33,78 a 37,19 | −12,69 | −15,61 a −9,76 | 40,92 |
| Estrato 5 | 23,72 | 21,02 a 26,43 | −7,83 | −12,74 a −2,93 | 42,64 |
| Estrato 6 | 18,53 | 15,10 a 21,95 | −16,31 | −24,74 a −7,89 | 43,79 |
| Sin Estrato | 11,81 | 10,61 a 13,02 | −9,73 | −21,73 a 2,28 | 13,54 |

- **En estrato 5, la brecha general (42,64) es mayor que en cada tipo de colegio** (23,72 y −7,83). Ocurre porque el 61 % de los urbanos de ese estrato está en colegios no oficiales, frente al 26 % de los rurales. Por eso, la sección 4 mide allí en buena parte el tipo de colegio.
- **En los oficiales, la brecha no crece siempre con el estrato:** sube hasta estrato 4 y luego baja.
- **En los no oficiales, los rurales superan a los urbanos** en los grupos con diferencia clara. En estrato 1 y en `Sin Estrato` el intervalo incluye el cero. La posible explicación de los colegios campestres sigue por verificar.
- **Hay un resultado por verificar:** en los colegios oficiales rurales, el puntaje baja de 233,36 en estrato 2 a 192,90 en estrato 6. El estrato es el de la vivienda del estudiante, y este análisis no permite saber qué tan bien mide su situación en zona rural.

Las tablas completas, con los conteos y la categoría `SIN DATO`, quedan en `salidas/profundizacion/`.

## Modelo en 3FN con PySpark

### 12. De una tabla plana a seis tablas
La tabla descargada es plana: cada fila es un estudiante y repite los datos de su sede, su colegio, su municipio y su departamento. `src/modelo_3fn.py` la lee con PySpark (2.162.410 filas de los dos periodos, en 4 particiones), prueba 10 dependencias funcionales y la descompone hasta la tercera forma normal:

| Tabla | Llave primaria | Columnas | Filas |
|---|---|---|---|
| `departamentos` | `cod_depto` | departamento | 33 |
| `municipios` | `cod_mcpio` | municipio, `cod_depto` (FK) | 1.114 |
| `establecimientos` | `cod_establecimiento` | establecimiento, naturaleza | 10.724 |
| `sedes` | `cod_sede` | sede, `cod_establecimiento` (FK), `cod_mcpio` (FK) | 11.937 |
| `sedes_periodo` | (`cod_sede`, `periodo`) | zona | 22.336 |
| `resultados` | `estu_consecutivo` | periodo, `cod_sede` (FK), estrato, seis puntajes | 1.079.002 |

`resultados` se une a `sedes_periodo` por la llave compuesta (`cod_sede`, `periodo`). Las tablas quedan en Parquet en `salidas/modelo/parquet/`.

**Hallazgos y decisiones**

| Hallazgo (evidencia) | Forma | Decisión |
|---|---|---|
| Cada estudiante aparece dos veces: 2.162.410 filas para 1.079.002 estudiantes | 1FN | Una fila por `estu_consecutivo`, que pasa a ser la llave primaria |
| Los datos del colegio, el municipio y el departamento se repiten en cada estudiante | 3FN | Tablas `sedes`, `establecimientos`, `municipios` y `departamentos` |
| El departamento depende del municipio, no del estudiante | 3FN | Se toma de los dos primeros dígitos del código DIVIPOLA; ningún municipio incumple la regla |
| La zona de 66 sedes cambió entre 2019 y 2022 | 3FN | La zona depende de la sede **y** del periodo: tabla `sedes_periodo` con llave compuesta |
| Hay 1.114 códigos de municipio pero solo 1.031 nombres: municipios distintos comparten nombre | Dominio | El municipio se identifica por código, nunca por nombre |
| Un colegio tuvo dos naturalezas en 2019 (35 estudiantes) y 5 cambiaron entre periodos | 3FN | Se guarda la naturaleza más frecuente: 354 estudiantes de 2019 (0,06 %) quedan con la de 2022 |
| Cambian entre periodos el nombre de 1.337 sedes y 632 colegios; 3 sedes cambian de colegio y 2 de municipio | Dominio | Se guarda el valor más frecuente; el análisis usa códigos, y ningún estudiante cambia de zona ni de departamento |

**Verificación con Spark SQL.** Spark no hace cumplir llaves primarias ni foráneas, así que se comprueban con consultas: llaves repetidas en las seis tablas, huérfanos con `LEFT ANTI JOIN` en las cuatro relaciones y la regla DIVIPOLA. Las 11 consultas dan **0**. Al reconstruir la tabla plana con `JOIN` salen las mismas 1.079.002 filas, sin diferencias de zona ni de departamento, y la brecha calculada con SQL sobre el modelo es la misma del análisis: **23,69** en 2019 y **26,24** en 2022.

| Indicador | Tabla plana | Modelo 3FN |
|---|---|---|
| Filas (observaciones) | 2.162.410 | 1.079.002 |
| Departamentos (por nombre / por código) | 33 / 33 | 33 |
| Municipios (por nombre / por código) | 1.031 / 1.114 | 1.114 |
| Municipios que incumplen DIVIPOLA | 0 | 0 |
| Brecha urbano − rural 2019 | 23,69 | 23,69 |
| Brecha urbano − rural 2022 | 26,24 | 26,24 |

### 13. Contar colegios en vez de filas cambia la foto
Con el modelo se puede contar por sede, algo que la tabla plana no permite sin repetir cálculos:

| Periodo | Zona | Sedes | Estudiantes | Estudiantes por sede | Media por estudiante | Media por sede |
|---|---|---|---|---|---|---|
| 2019 | Urbano | 7.149 | 460.467 | 64,4 | 249,91 | 251,18 |
| 2019 | Rural | 3.790 | 85.744 | 22,6 | 226,22 | 223,15 |
| 2022 | Urbano | 7.234 | 441.577 | 61,0 | 254,63 | 255,06 |
| 2022 | Rural | 4.163 | 91.214 | 21,9 | 228,39 | 225,26 |

- **Lo rural pesa el doble en colegios que en estudiantes.** En 2022, el 36,5 % de las sedes con estudiantes evaluados son rurales, pero solo el 17,1 % de los estudiantes. Una sede rural presenta en promedio 22 estudiantes; una urbana, 61.
- **Por colegio, la brecha es mayor.** Si cada sede cuenta una vez, la brecha de 2022 es de 29,80 puntos, frente a 26,24 por estudiante (en 2019, 28,03 frente a 23,69). Las sedes rurales pequeñas tienen promedios más bajos.
- **En algunos departamentos la diferencia es enorme.** En Guaviare el 62,5 % de las sedes son rurales y solo el 25,8 % de los estudiantes; en Caquetá, 48,8 % frente a 17,6 %; en Chocó, 60,9 % frente a 30,0 %; y en Antioquia, 43,7 % frente a 17,3 %.

![Porcentaje de sedes rurales frente a porcentaje de estudiantes rurales por departamento, 2022](figuras/efecto_normalizacion.png)

## Conclusión
Los estudiantes de colegios rurales obtienen en promedio 26 puntos menos en el puntaje global de Saber 11 de 2022, con un efecto mediano y presente en todas las áreas, sobre todo en inglés. Al comparar dentro del mismo tipo de colegio y estrato, la brecha baja a 17,5 puntos: se mantiene, pero cerca de un tercio de la cifra general corresponde a la composición de los grupos. La brecha se concentra en el sector oficial, donde están el 94 % de los rurales.

Para focalizar programas e inversión, conviene mirar dos cosas. Las brechas más altas están en Guainía, San Andrés y Amazonas, pero tienen menos del 1 % de los rurales. Antioquia, Córdoba, Cauca, Bolívar y Nariño concentran el mayor número de estudiantes afectados.

Entre 2019 y 2022 la brecha aumentó de 23,7 a 26,2 puntos: aunque los dos grupos mejoraron, los colegios rurales mejoraron menos. El aumento se ve en todas las áreas y en 26 de 32 departamentos. Dentro del mismo tipo de colegio y estrato es de 1,2 puntos, menos de la mitad de los 2,55 generales, pero sigue siendo claro. Esto es coherente con la idea de que la pandemia y la educación remota afectaron más a la educación rural, pero este análisis compara dos momentos y no prueba la causa: otros factores también pudieron cambiar en esos años.

Normalizar la tabla hasta 3FN con PySpark no cambió la brecha, pero sí la forma de contar: la tabla plana repetía a cada estudiante dos veces y no permitía contar colegios. Con el modelo se ve que lo rural es el 36,5 % de las sedes y solo el 17,1 % de los estudiantes, y que por colegio la brecha sube a 29,8 puntos. Para focalizar programas, esto importa: la educación rural está repartida en muchas sedes pequeñas.

## Huellas de referencia
```
462f0dab35cef1f536c0ff4058f0e3022591b731b369960b2dac8b156db0f02d  datos/saber11_20194.csv
617c6547a6725ff7a2c4fe860b35a8c7aca83878cb0dc0fdc0a0d365e3f10905  datos/saber11_20224.csv
b805e8031e62bad43d9175c51211154aecc04c302fbcb93e14b61d3c88224445  salidas/20194/resumen_zona.csv
229ebc57a0fd8eb2a4912700a674d4792903dc0c71f8d6974ce205ef623c84bc  salidas/20224/resumen_zona.csv
b1198188685e39fac8fa1d4dff436e8d085ed8aba6604687f4611b2e3d7529c9  salidas/comparacion/comparacion_zona.csv
a360db391ce583118846c90e0afa1c5051a3ccb0ede42ddbd7b354ed864e0611  salidas/comparacion/comparacion_departamento.csv
42b0c8367db6797d9c43294594502ccb57092d127e45b6fafd6d57f5967277d3  salidas/profundizacion/resultados.md
ed26b106391bd1aa3bd276db02afb3916a0a7a19bc6cccbf292c2d8cd8be03cf  salidas/modelo/brecha_modelo.csv
e0b93913213b00a6b34801a6cfb9f847246ba96073d90d3f8fb0a54571d58a7e  salidas/modelo/dependencias.csv
198cae0f17f35348a93a3e8d5c15b64648ca310023e62579fbd4864ba49964f6  salidas/modelo/efecto_sedes.csv
e8ccb5f50aff1c07430758687f0f4d2e955bef2197f4dc5062354675faf24fa7  salidas/modelo/indicadores_plana_vs_3fn.csv
baae94d315a380e05fb3c7b8efe0e518a29d7040a8cc03c8da5231da10235077  salidas/modelo/rural_departamento_20224.csv
```

Los CSV descargados traen desde la versión 0.5 las columnas de códigos del colegio, por eso su huella cambió respecto a versiones anteriores. Las salidas del análisis (`resumen_zona.csv` y las demás) mantienen exactamente las mismas huellas. Los archivos Parquet que escribe Spark no tienen huella fija porque Spark les pone un nombre distinto en cada escritura; por eso se registran las huellas de los resúmenes en CSV.
