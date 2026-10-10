<p align="center"><img src="assets/logo_facta_living_lab.jpeg" alt="Facta Living Lab" width="180"></p>

# EOD 2023 Guadalajara: una lectura independiente

**Gravitacional por zona, cartografía de respaldo y auditoría de consistencia de la Encuesta Origen-Destino 2023 del Área Metropolitana de Guadalajara (AMG).**

© 2026 Facta Living Lab (Facta Terrae). Código bajo Apache-2.0; tablas, mapas, figuras y texto bajo CC BY 4.0. Ver [Licencia](#licencia).

> *English summary.* Independent re-analysis of the 2023 Guadalajara Origin-Destination Survey (IMEPLAN): a zone-level PPML gravity model by trip purpose, residual cartography, sensitivity to the external bus calibration, and a reproducible consistency audit. Code, derived tables and maps are shared; the raw microdata are **not** redistributed.

## Qué responde

1. ¿Las cifras que publica IMEPLAN se sostienen desde la base? **Sí, al dato exacto** (total, 30 de 30 totales por zona leídos del visualizador, modos, motivos, edad, sexo y duración).
2. ¿Cuánto pesa la distancia en los viajes y dónde falla un modelo clásico? Exponentes por propósito, acierto fuera de muestra y mapas de residuos.
3. ¿Cuánto dependen las cifras principales de los ajustes externos? Prueba de sensibilidad a la calibración de camión (factor SETRAN 0.5677).
4. ¿Qué conviene aclarar en los datos? Auditoría reproducible: zonas AGEB, fechas, duración y cadenas de viaje.

## Resultados clave

| Propósito | CPC modelo libre | CPC con atractores | Techo de ruido | Exponente de distancia (IC 95%, bootstrap por vivienda) |
| --- | --- | --- | --- | --- |
| Trabajo | 0.80 | 0.75 | 0.77 | -1.60 (-1.62, -1.58) |
| Estudio | 0.80 | 0.74 | 0.81 | -2.58 (-2.62, -2.53) |
| Otros | 0.86 | 0.85 | 0.87 | -2.65 (-2.67, -2.62) |

Duplicar la distancia reduce los viajes a ×0.33 (trabajo), ×0.17 (estudio) y ×0.16 (otros). Los intervalos son cotas inferiores: la vivienda no es la unidad primaria del diseño muestral y el ponderador se trata como fijo.

## Estructura

```
src/        gravedad_eod_zonas.py  modelo, validación split-half y bootstrap
            mapas_eod_zonas.py     6 mapas, figura de ajuste y tabla por zona
            sensibilidad_setran.py prueba sin la calibración de camión
            auditoria_eod.py       verificaciones de consistencia
tablas/     resultados del modelo, sensibilidad, auditoría y métricas por zona (CSV)
mapas/      6 mapas y la figura de ajuste (PNG)
data/       instrucciones para obtener las entradas (no se incluyen datos crudos)
assets/     logotipo (no cubierto por las licencias abiertas)
```

## Cómo reproducir

```bash
pip install -r requirements.txt
# 1. Coloca las entradas en data/raw/ (ver data/README.md)
python src/gravedad_eod_zonas.py      # puede tardar más de 10 minutos
python src/mapas_eod_zonas.py         # mapas y tabla por zona
python src/sensibilidad_setran.py     # robustez a la calibración de camión
python src/auditoria_eod.py           # auditoría de consistencia
```

Las rutas se controlan con `EOD_DATA_DIR` (por defecto `data/raw/`) y `EOD_OUT_DIR` (por defecto `salida/`).

## Datos: lo que no está aquí

Este repositorio **no redistribuye** la base de viajes de IMEPLAN ni las capas de zonificación y microzonas. Quien reproduzca el análisis debe obtenerlas por su cuenta y respetar sus condiciones de uso (ver `data/README.md`). Las tablas y mapas incluidos son agregados derivados, con IMEPLAN, INEGI y el Centro Futuro Ciudades como fuentes de los insumos.

## Decisiones y límites

- Distancia entre centros de zona, no tiempos de viaje; la distancia intrazonal es un supuesto que influye en el exponente.
- 64 zonas internas; se excluyen 7 accesos externos y el aeropuerto (2.0% de los viajes) y el regreso a casa (48% de los viajes).
- El atractor de estudio es población (no matrícula escolar) y el empleo registrado cubre 1.54 de 2.70 millones de ocupados.
- Solo días hábiles de 2023.
- Las inconsistencias de la auditoría **no son prueba de intención**; son puntos por aclarar. De los 51 AGEB con diferencias contra la tabla AGEB-zona, 31 tienen otra zona asignada y 20 aparecen con zona "NA".
- Las cifras del visualizador se capturaron a mano el 2026-10-10 y viven como constantes en `auditoria_eod.py`.

## Licencia

| Qué | Licencia |
| --- | --- |
| Código (`src/`) | [Apache-2.0](LICENSE) |
| Tablas, mapas, figuras y texto (`tablas/`, `mapas/`, `README.md`, `data/README.md`) | [CC BY 4.0](LICENSE-CC-BY-4.0.txt) |
| Nombre, logotipo y marcas Facta Living Lab y Facta Terrae | Todos los derechos reservados (ver [NOTICE](NOTICE)) |
| Datos de terceros (IMEPLAN, INEGI, Centro Futuro Ciudades) | No incluidos ni cubiertos |

## Cómo citar

Facta Living Lab. (2026). *EOD 2023 Guadalajara: una lectura independiente* (v0.1.0) [Software y datos derivados]. GitHub. https://github.com/facta-living-lab/eod-gdl-gravedad

Véase también `CITATION.cff`.

## Contacto

[factaterrae.com](https://factaterrae.com) · Issues y correcciones son bienvenidos.
