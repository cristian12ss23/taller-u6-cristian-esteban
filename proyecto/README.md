# Proyecto: Brecha rural vs urbana en Saber 11

## Pregunta de análisis
¿Cuántos puntos de diferencia hay en Saber 11 entre los estudiantes de colegios urbanos y rurales en Colombia? ¿La brecha se mantiene cuando se compara dentro del mismo tipo de colegio (oficial o no oficial) y del mismo estrato? ¿En qué departamentos es más grande? ¿Cambió entre 2019, antes de la pandemia, y 2022?

El resultado sirve para orientar dónde focalizar programas e inversión en la educación rural.

## Fuente de datos
- Conjunto: Resultados únicos Saber 11
- Entidad: ICFES, publicado en datos.gov.co
- Enlace: https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe
- Licencia: Creative Commons Atribución-CompartirIgual 4.0 Internacional (CC BY-SA 4.0)
- Periodos analizados: `20224` (2022, calendario A, el más reciente del conjunto) y `20194` (2019, calendario A, antes de la pandemia)

Los datos se descargan con la API pública de datos.gov.co, filtrados por periodo y solo con las columnas necesarias. No se versionan: se regeneran con el contenedor.

**Calidad de los datos.** En los periodos 20194 y 20224 el conjunto trae repetida a casi toda la población: en 20224 hay 1.065.888 filas, pero solo 532.792 identificadores de estudiante distintos (`estu_consecutivo`). Antes de calcular, el análisis quita las copias idénticas y luego deja una sola fila por identificador; `manifiesto.json` registra cuántas filas quita cada paso. La primera versión de este análisis no los quitaba: contaba 1.065.886 estudiantes y un intervalo de confianza de 26,00 a 26,48. Ya sin repetidos son 532.791 estudiantes y el intervalo es de 25,90 a 26,58. Los promedios no cambiaron, pero los conteos sí, y la precisión estaba sobrestimada.

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

Una copia de las gráficas está en `figuras/` para mostrarlas en este README.

## Técnicas y herramientas del curso
Esto es lo que se usó de Computación en la Nube para Análisis de Datos y para qué sirvió en este proyecto.

| Técnica o herramienta | Qué se hizo | Cómo ayudó | Dónde se ve |
|---|---|---|---|
| **Git** (control de versiones) | Cada cambio se registró como una confirmación con autor, fecha y mensaje. | La primera versión contaba 1.065.886 estudiantes, con repetidos. La corrección quedó en otra confirmación, así que se puede comparar el antes y el después. | `git log`, confirmaciones `647cc0d` y `d997e0a` |
| **GitHub** | El repositorio público guarda el código y el README con las gráficas. | Los dos integrantes trabajaron sobre la misma versión del proyecto, sin pasarse copias por correo, y cualquiera puede revisarlo. | Este repositorio |
| **Codespaces** (máquina en la nube) | El proyecto se construye y se ejecuta en un computador de GitHub, desde el navegador. | Más de un millón de filas por periodo se descargan y procesan sin instalar nada ni depender del computador de cada integrante. | `Cómo reproducir` |
| **Docker: imagen y Dockerfile** | La imagen fija Python 3.12, las bibliotecas y el código. El periodo se elige al ejecutar, con `-e PERIODO`. | 2019 y 2022 se analizan con la misma imagen. Si la brecha cambia, la causa no es una diferencia de código ni de versiones. | `Dockerfile`, `ejecutar.sh` |
| **Docker: volúmenes** | `datos/` y `salidas/` se conectan al contenedor con `--volume`. | El contenedor se desecha al terminar, pero los resultados quedan. Además, la descarga de varios minutos no se repite. | `Cómo reproducir` |
| **Docker: capas y privilegio mínimo** | `requirements.txt` se copia antes que el código y el contenedor corre con el usuario `analista`, sin permisos de administrador. | Cambiar el código no obliga a reinstalar las bibliotecas, y el proceso solo tiene los permisos que necesita. | `Dockerfile` |
| **Versiones fijadas** | Cada biblioteca lleva su versión exacta con `==`. | La imagen instala lo mismo sin importar cuándo se construya. | `requirements.txt` |
| **Huellas SHA-256 y manifiesto** | Se calcula la huella de los datos y de cada salida. Los datos se ordenan de forma fija antes de guardarlos. | Permite comprobar si otra ejecución dio exactamente lo mismo, y avisa si la fuente cambió. La huella detecta el cambio, pero no recupera los datos anteriores, porque no se guarda una copia. | `manifiesto.json`, `Huellas de referencia` |
| **`.gitignore`** | Los datos y las salidas no entran al repositorio. | Se versiona la receta y no el resultado, de modo que el repositorio se mantiene liviano. | `.gitignore` |
| **Datos abiertos e ingesta por API** | La descarga va por páginas de 50.000 filas, con hasta 5 reintentos, solo 12 columnas y reutilizando el CSV si ya existe. | Una falla momentánea de red se reintenta sin perder lo ya descargado, se baja solo lo necesario y repetir el comando no duplica datos. | `src/descargar.py` |
| **Calidad y zonas de datos** | Se separa el CSV original, los datos limpios y los resultados. Se revisó la fuente antes de analizar. | Revisar los identificadores mostró que los conteos estaban casi duplicados, y se corrigió antes de comparar 2019 con 2022. | `src/analisis.py`, `Calidad de los datos` |
| **Parquet** | El resumen y los datos limpios se guardan en Parquet. Se comparan filas, columnas, vacíos y suma del puntaje antes de aceptar la conversión. | Permite leer solo las columnas necesarias, y la comprobación evita aceptar una conversión dañada. | `src/profundizar.py`, `registro.json` |

**Herramientas del curso que no se usaron.** PySpark, Databricks y Cassandra no hacen parte de este proyecto. Con cerca de un millón de filas por periodo, pandas fue suficiente en el Codespace. Cassandra está pensada para consultar por clave, y aquí el trabajo consiste en agrupar y resumir todos los datos.

Para el análisis se usaron pandas, scipy y matplotlib.

## Cómo reproducir
Desde la raíz del repositorio, en el codespace:

```bash
docker build --tag proyecto:0.4 proyecto/

# 2022
docker run --rm -e PERIODO=20224 \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.4

# 2019
docker run --rm -e PERIODO=20194 \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.4

# Comparación
docker run --rm --entrypoint python \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.4 src/comparar.py

# Profundización (usa los CSV de datos/)
docker run --rm --entrypoint python \
  --volume "$(pwd)/proyecto/datos:/app/datos" \
  --volume "$(pwd)/proyecto/salidas:/app/salidas" \
  proyecto:0.4 src/profundizar.py
```

Cada descarga trae cerca de un millón de filas y tarda varios minutos. Las ejecuciones siguientes reutilizan los CSV de `datos/`.

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

### 4. La brecha crece con el estrato
| Estrato | Brecha |
|---|---|
| Sin estrato | 13,54 |
| Estrato 1 | 14,25 |
| Estrato 2 | 21,12 |
| Estrato 3 | 30,37 |
| Estrato 4 | 40,92 |
| Estrato 5 | 42,64 |
| Estrato 6 | 43,79 |

El puntaje rural se mantiene casi plano (entre 205 y 236) sin importar el estrato, mientras que el urbano sube con el estrato. Por eso la brecha es pequeña en estrato 1 y grande en los estratos altos. Los grupos rurales de estratos 5 y 6 son pequeños, así que esos valores deben leerse con cuidado.

### 5. Por departamento
- **Mayor brecha:** Guainía (55,90), San Andrés (44,33), Amazonas (36,89), Sucre (34,09) y La Guajira (33,70).
- **Menor brecha:** Valle (12,65), Meta (5,93) y Bogotá (3,63). En Cundinamarca (−3,64) y Quindío (−8,15) los rurales superan a los urbanos.

Estas cifras deben leerse junto con el número de estudiantes de cada departamento: el mínimo para entrar en la tabla es de 100 rurales, y con pocos estudiantes la brecha es menos precisa. `salidas/profundizacion/brecha_departamento_ic.csv` trae el intervalo de confianza y el peso de cada departamento en el total de rurales.

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
- En los colegios **oficiales**, que tienen el 94 % de los rurales, la brecha pasó de 22,88 a 24,11 (+1,23), menos de la mitad del aumento general de 2,55. La sección 10 revisa de dónde viene el resto.
- En los **no oficiales** los rurales siguen por encima, pero la ventaja bajó de 27,39 a 19,43 puntos.
- La brecha creció en **todos los estratos**; por ejemplo, en estrato 1 pasó de 12,03 a 14,25 y en estrato 3 de 26,74 a 30,37.

### 9. Por departamento
La brecha creció en **26 de los 32 departamentos** comparados.
- **Mayor aumento:** Casanare (+11,64), Bogotá (+9,54), La Guajira (+7,75), Amazonas (+7,26) y Nariño (+6,19).
- **Se redujo en 6:** Valle (−4,44), Quindío (−3,69), Chocó (−3,58), Putumayo (−1,05), Arauca (−0,18) y Guainía (cambio muy pequeño, cerca de −0,1 en la gráfica).

Bogotá tiene pocos estudiantes rurales (alrededor de 600 por año), así que su cambio debe leerse con cuidado.

![Cambio de la brecha por departamento, 2019 a 2022](figuras/cambio_departamento.png)

## Comparación dentro del mismo tipo de colegio y estrato

### 10. ¿Cuánto queda de la brecha?
La brecha general mezcla dos cosas: la diferencia entre zonas y el hecho de que urbanos y rurales no se reparten igual entre tipos de colegio y estratos. Para separarlas, se calcula la brecha dentro de cada grupo y se promedia con el peso que ese grupo tiene entre los rurales.

Por ejemplo, con solo el tipo de colegio en 2022:

(85.886 × 24,11 + 5.328 × (−19,43)) / 91.214 = **21,57 puntos**, frente a 26,24 sin ajustar.

Es decir, igualar el tipo de colegio quita cerca de 4,7 puntos de la brecha. Los estudiantes sin dato de estrato se conservan como una categoría propia, `SIN DATO`, y su cantidad queda registrada en `salidas/profundizacion/registro.json`.

> **Pendiente:** correr `src/profundizar.py` y pegar aquí las tablas de `salidas/profundizacion/resultados.md`.

## Conclusión
Los estudiantes de colegios rurales obtienen en promedio 26 puntos menos en el puntaje global de Saber 11 de 2022, con un efecto mediano y presente en todas las áreas, sobre todo en inglés. La brecha se concentra en el sector oficial y es más grande en departamentos periféricos (Guainía, San Andrés, Amazonas, La Guajira).

Entre 2019 y 2022 la brecha aumentó de 23,7 a 26,2 puntos: aunque los dos grupos mejoraron, los colegios rurales mejoraron menos. El aumento se ve en todas las áreas, en todos los estratos y en 26 de 32 departamentos. Esto es coherente con la idea de que la pandemia y la educación remota afectaron más a la educación rural, pero este análisis compara dos momentos y no prueba la causa: otros factores también pudieron cambiar en esos años.

## Huellas de referencia
```
2d2cffdc691ca7c5b1db4a38bbba6958fb3f56c53b0f5a9f8a516c5ee0fae46c  datos/saber11_20194.csv
bd21913fb35ac914fe87bce5c33a96c8549d38406a3fe68cf2fd70d064341219  datos/saber11_20224.csv
b805e8031e62bad43d9175c51211154aecc04c302fbcb93e14b61d3c88224445  salidas/20194/resumen_zona.csv
229ebc57a0fd8eb2a4912700a674d4792903dc0c71f8d6974ce205ef623c84bc  salidas/20224/resumen_zona.csv
b1198188685e39fac8fa1d4dff436e8d085ed8aba6604687f4611b2e3d7529c9  salidas/comparacion/comparacion_zona.csv
a360db391ce583118846c90e0afa1c5051a3ccb0ede42ddbd7b354ed864e0611  salidas/comparacion/comparacion_departamento.csv
```
