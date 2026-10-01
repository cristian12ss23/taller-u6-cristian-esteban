# Laboratorio 5. Contenedores y reproducibilidad

Repositorio de referencia del Laboratorio 5 del curso Computación en la Nube para Análisis de Datos (Unidad 6: contenedores y reproducibilidad). Contiene un análisis de datos empaquetado en una imagen Docker, versionado con Git y verificable mediante huellas SHA-256 de sus salidas.

## Estructura

```
lab05_reproducibilidad/
├── .devcontainer/
│   └── devcontainer.json      Definición declarativa del entorno para GitHub Codespaces
├── src/
│   ├── generar_datos.py       Generación sintética y reproducible del conjunto de viajes
│   ├── analisis.py            Resumen por ciudad, gráfica y manifiesto de huellas
│   └── verificar.py           Comparación de manifiestos entre dos corridas
├── datos/                     Conjunto de datos generado (no se versiona)
├── salidas/                   Salidas del análisis (no se versionan)
├── Dockerfile                 Receta de la imagen
├── requirements.txt           Dependencias con versión fijada
├── ejecutar_analisis.sh       Punto de entrada del contenedor
├── reproducir.sh              Construcción, doble ejecución y verificación
├── .dockerignore
└── .gitignore
```

## Ejecución mínima

Entorno de referencia: terminal Linux con Docker Engine 24 o superior y Python 3.12 (GitHub Codespaces o Google Cloud Shell).

```bash
docker build --tag lab05-viajes:1.0 .
docker run --rm --volume "$(pwd)/salidas:/app/salidas" lab05-viajes:1.0
```

Salida esperada al final de la ejecución: tabla resumen de cinco ciudades y tres huellas SHA-256, una por archivo de salida.

## Verificación de reproducibilidad

```bash
./reproducir.sh
```

Salida esperada en la última línea:

```
Reproducción exacta: 3 de 3 salidas coinciden.
```

## Versiones de referencia

| Componente | Versión |
|---|---|
| Imagen base | python:3.12-slim-bookworm |
| numpy | 2.1.3 |
| pandas | 2.2.3 |
| pyarrow | 17.0.0 |
| matplotlib | 3.9.2 |

Fecha de referencia: septiembre de 2026. Las versiones se fijan en `requirements.txt`; toda actualización debe registrarse allí y validarse con `./reproducir.sh`.
