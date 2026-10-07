# Informe del taller · Unidad 6 · Cristian Puerto y Esteban Díaz

## 1. Repositorio e integrantes

Repositorio: https://github.com/cristian12ss23/taller-u6-cristian-esteban

| Integrante | Usuario de GitHub | Rol |
|---|---|---|
| Cristian Puerto | @cristian12ss23 | R1 y R2: responsable del repositorio y de datos |
| Esteban Díaz | @diazesteban1001-sudo | R3: responsable de análisis |

El grupo tiene dos integrantes, por lo que R1 asumió también el rol de R2. En el Taller 2, Esteban Díaz ejecutó todos los momentos en su codespace.

## 2. Reproducción de la versión 1.0 (M2)

**Esteban Díaz** (codespace propio, versión `e8353d3`):

```
SHA-256 datos/viajes.csv : 5ddad64f85e081307de1dad5a52e10a40422c12749954716f607f3c6d15bc19e

154b62824a5a7f02e37a5e7a0a93e46ddd0237f2d88a57a8048800650b15a59a  resumen_ciudad.parquet
0c598115bb5676dd920eb4ada9a1be22dc6509f79aad616d795a65e337bfbb4b  resumen_ciudad.csv
568842db5a3964bdf2714a947311d127a9e35722593c2f12cba9b2ced58e74b2  tarifa_media_ciudad.png

Reproducción exacta: 3 de 3 salidas coinciden.
```

Las tres huellas coinciden con los valores de referencia de la versión 1.0. Como el cambio de Pereira ya estaba publicado cuando se hizo esta prueba, la reproducción se ejecutó sobre la confirmación `e8353d3` (`git checkout e8353d3`), que corresponde exactamente a la versión 1.0.

## 3. Trabajo en paralelo (M3)

Salida de `git log --oneline --graph`:

```
* 3908faa Proyecto: README inicial
* dcd85e1 Proyecto: dependencias fijadas
* 1ea7cf6 Proyecto: dependencias fijadas
* ac8e499 Documenta integrantes; prepara imagen 1.1
* 125b7db Corrige la sangría de CIUDADES y PESOS_CIUDAD
*   714c574 Merge branch 'main' of https://github.com/cristian12ss23/taller-u6-individual
|\
| * 0ed2322 Agrega Pereira al generador de datos
* | 82aa5b2 Agrega desviación estándar de la tarifa
|/
* e8353d3 Estructura inicial del laboratorio 5
* 1bea594 Create README.md
```

Conteo de confirmaciones por autor (`git log --format="%an" | sort | uniq -c`):

```
      6 cristian12ss23
      4 diazesteban1001-sudo
```

Reparto de los cambios del momento 3:

- R2 (Cristian): `Agrega Pereira al generador de datos`, en `src/generar_datos.py`.
- R3: `Agrega desviación estándar de la tarifa`, en `src/analisis.py`. Este cambio lo publicó Cristian antes de que Esteban lo hiciera.
- R1: `Documenta integrantes; prepara imagen 1.1`, en `README.md` y `reproducir.sh`. Lo hizo Esteban.

El grafo muestra que el cambio de Pereira y el de la desviación estándar se hicieron en paralelo, sobre la misma confirmación de partida (`e8353d3`). Git los unió con una fusión (`714c574`) sin conflictos, porque cada cambio estaba en un archivo distinto.

Nota: la confirmación `dcd85e1` agrega `proyecto/Dockerfile`; su mensaje quedó por error igual al de la confirmación anterior.

## 4. Versión 1.1 (M4)

Tabla obtenida por Esteban Díaz con `./reproducir.sh` sobre la imagen `lab05-viajes:1.1`:

| ciudad | n_viajes | distancia_media_km | duracion_media_min | tarifa_media_cop | tarifa_p50_cop | tarifa_sd_cop |
|---|---|---|---|---|---|---|
| Barranquilla | 5126 | 5.96 | 17.89 | 16367.81 | 14438.0 | 8867.54 |
| Bogota | 22462 | 5.99 | 18.00 | 16448.88 | 14339.0 | 9188.16 |
| Bucaramanga | 2485 | 5.96 | 17.90 | 16383.86 | 14252.0 | 9010.00 |
| Cali | 7445 | 5.90 | 17.70 | 16250.58 | 14180.0 | 9101.52 |
| Medellin | 9950 | 5.97 | 17.86 | 16396.02 | 14171.0 | 9218.13 |
| Pereira | 2532 | 5.97 | 17.91 | 16402.67 | 14447.0 | 8934.61 |

Huellas obtenidas:

```
f3be1441539ca17baab5402f302485e799741ea4fd24960202317b4a98ce3efe  datos/viajes.csv
1343a787d52fcff776f058ce3b7057e78eaf2d9ba1a931bd8e8f67847c01081f  resumen_ciudad.parquet
8160729ebe9c436dc295431cb93e1767ce3333521210ecac635c07efd52c5874  resumen_ciudad.csv
7a75390c4f5e44653226f7eea0c53b84238810163fa3c76420af63545870cab8  tarifa_media_ciudad.png

Reproducción exacta: 3 de 3 salidas coinciden.
```

Las cuatro huellas coinciden con los valores de referencia de la versión 1.1. Después de verificarlas se publicó la etiqueta `v1.1`.

**Por qué Bogotá, Medellín y Cali no cambiaron.** El generador asigna la ciudad de cada viaje comparando un número aleatorio con los pesos acumulados de las ciudades. Como la semilla es la misma, la secuencia de números aleatorios es idéntica en las dos versiones. Los tres primeros tramos acumulados (Bogotá 0–0.45, Medellín 0.45–0.65 y Cali 0.65–0.80) no cambiaron, así que los viajes que caían en ellos siguen asignados a las mismas ciudades y con los mismos valores. Solo se modificaron los dos últimos tramos (Barranquilla de 0.12 a 0.10 y Bucaramanga de 0.08 a 0.05) para abrir el espacio de Pereira (0.05), y por eso solo cambian esas ciudades.

**Incidencias en M0.**

- Síntoma: `docker: command not found`. El codespace arrancaba en modo de recuperación (recovery mode) porque el contenedor definido en `.devcontainer/devcontainer.json` no lograba construirse. Solución: se apartó temporalmente ese archivo (`mv .devcontainer /tmp/`), se reconstruyó el contenedor (Codespaces: Rebuild Container) con la imagen por defecto de Codespaces, que incluye Docker, y luego se restauró el archivo con `git restore .devcontainer`, sin publicar ningún cambio.
- Síntoma: el conteo por autor mostraba un solo autor. El codespace había clonado solo la última confirmación (clon superficial). Solución: `git fetch --unshallow` trajo el historial completo.
- El codespace se detuvo por inactividad durante la sesión. Al reabrirlo, los archivos y las imágenes de Docker seguían disponibles y el trabajo continuó sin pérdidas.

## 5. Diagnósticos (M5)

### 5.1 Cambio de semilla (20260917 → 20260918)

```
DIFIERE   resumen_ciudad.csv
DIFIERE   resumen_ciudad.parquet
DIFIERE   tarifa_media_ciudad.png

Reproducción fallida: 0 de 3 salidas coinciden.
```

La semilla fija el punto de partida del generador de números aleatorios. Al cambiarla en una sola unidad, el generador produce una secuencia completamente distinta, así que cambian la ciudad, la distancia, la duración y la tarifa de los 50 000 viajes. Como cambian los datos de entrada, cambian las tres salidas y sus huellas SHA-256. El archivo se restauró con `git checkout -- src/generar_datos.py`.

### 5.2 Versión sin fijar (`numpy==2.1.3` → `numpy>=2.1`)

```
IDENTICO  resumen_ciudad.csv
IDENTICO  resumen_ciudad.parquet
IDENTICO  tarifa_media_ciudad.png

Reproducción exacta: 3 de 3 salidas coinciden.
```

Versión de numpy instalada por pip en la imagen de prueba: 2.5.3.

Hoy las huellas coinciden, pero la reproducibilidad ya no está garantizada. Con `numpy>=2.1`, pip instala la versión más reciente disponible el día de la construcción, de modo que la misma receta puede producir imágenes distintas en fechas distintas. Una versión futura de numpy podría cambiar el generador aleatorio o los redondeos y, con ellos, las huellas. Fijar la versión exacta (`==`) hace que la imagen sea la misma sin importar cuándo se construya. El archivo se restauró con `git checkout -- requirements.txt`.

### 5.3 Qué protege el .gitignore

`git status` responde `nothing to commit, working tree clean`, aunque `salidas_a/` y `salidas_b/` contienen `manifiesto.json`, `resumen_ciudad.csv`, `resumen_ciudad.parquet` y `tarifa_media_ciudad.png`. El `.gitignore` excluye `datos/*`, `salidas/*`, `salidas_a/` y `salidas_b/`.

Sin el `.gitignore`, el repositorio público incluiría el conjunto de datos y las salidas: archivos pesados, derivados y que cambian con cada experimento. No hace falta versionarlos porque se regeneran idénticos a partir de la receta (código, Dockerfile, dependencias fijadas y semilla), como lo demuestran las huellas SHA-256. Lo que se versiona es la receta, no el resultado.

## 6. Semilla del proyecto (M6)

Idea elegida: **brechas en Saber 11 entre colegios oficiales y privados**, con los resultados del ICFES publicados en datos.gov.co.

- Descripción del proyecto: [proyecto/README.md](proyecto/README.md)
- Dependencias fijadas: [proyecto/requirements.txt](proyecto/requirements.txt)
- Entorno: [proyecto/Dockerfile](proyecto/Dockerfile)

Salida de `docker run --rm proyecto:0.1`:

```
Entorno listo, pandas 2.2.3
```
