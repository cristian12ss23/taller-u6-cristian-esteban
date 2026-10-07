# Proyecto: Brechas en Saber 11 entre colegios oficiales y privados

## Pregunta de análisis
¿Cuál es la diferencia en el puntaje global y por áreas de Saber 11 entre colegios oficiales y no oficiales en Colombia, y cómo varía por departamento, zona (urbana/rural) y periodo? El resultado sirve para orientar decisiones de inversión y focalización de programas en la educación pública.

## Fuente de datos
- Conjunto: Resultados únicos Saber 11
- Entidad: ICFES, publicado en datos.gov.co
- Enlace: https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe
- Licencia y fecha de actualización: las indicadas en la ficha del conjunto en datos.gov.co, registradas al momento de la descarga

## Variables previstas
- PERIODO: año y semestre de la prueba
- COLE_NATURALEZA: oficial o no oficial
- COLE_AREA_UBICACION: urbana o rural
- COLE_DEPTO_UBICACION: departamento del colegio
- COLE_JORNADA: jornada del colegio
- FAMI_ESTRATOVIVIENDA: estrato de la vivienda del estudiante
- PUNT_GLOBAL: puntaje global
- PUNT_MATEMATICAS, PUNT_LECTURA_CRITICA: puntajes por área

## Herramientas del curso
- pandas para la exploración inicial sobre una muestra.
- PySpark (Databricks) para procesar el conjunto completo, que tiene millones de registros.
- Docker para fijar el entorno y garantizar resultados reproducibles.

## Cómo reproducir
docker build --tag proyecto:0.1 proyecto/
docker run --rm proyecto:0.1
