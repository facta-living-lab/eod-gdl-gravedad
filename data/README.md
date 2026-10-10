# Datos de entrada

Este repositorio **no incluye** datos crudos. Para reproducir el análisis, coloca en `data/raw/` estos archivos:

| Archivo | Contenido |
| --- | --- |
| `IMEPLAN_Base_Viajes_Master.csv` | Base de viajes de la EOD 2023 (codificación latin-1) |
| `RELACION_AGEBS-ZONA_con_datos_censales.parquet` | Relación AGEB-zona con datos censales (solo para la auditoría) |
| `AMG_Zonificacion_para_encuesta.parquet` | Zonificación EOD: 71 polígonos (64 zonas internas y 7 accesos externos), UTM 13N |
| `AMG_MicroZONAS2023.parquet` | 601 microzonas con atributos censales y empleo |

## De dónde los obtuvimos

Los archivos se obtuvieron del repositorio público del Centro Futuro Ciudades, [`eodgdl`](https://github.com/CentroFuturoCiudades/eodgdl) (carpeta `data/`), que cita a IMEPLAN como fuente. Los nombres y la versión pueden diferir de los de esta tabla: renombra o ajusta las constantes de los scripts.

- Commit del repositorio fuente: ______
- Fecha de descarga: ______

## Condiciones de uso

El repositorio fuente no mostraba una licencia en su página principal (revisado el 2026-10-10), así que no redistribuimos las bases. Antes de reutilizarlas o publicarlas, confirma las condiciones con IMEPLAN y con el Centro Futuro Ciudades.

## Advertencia sobre el archivo de zonificación

Si descargas el archivo de zonificación desde la web de GitHub y no desde el repositorio, verifica que sea un Parquet válido: una descarga equivocada puede guardar una página HTML con extensión `.parquet`.
