# Datos

**Esta carpeta no se versiona.** Contiene datos de estudiantes y solo existe en el equipo de quien trabaja el proyecto.

| Carpeta | Contenido | Generado por |
|---|---|---|
| `raw/` | Archivos de origen entregados por el IP: `Contactabilidad_SGE.xlsx`, `encuesta_caracterizacion_2024.xlsx`, `encuesta_caracterizacion_2025.xlsx`, `encuesta_caracterizacion_2026.xlsx`, `rendimiento_academico_2024-2025.xlsx` | Registro Académico / SGE |
| `interim/` | `contactabilidad_log_limpio.pkl` | `python -m fuga_ipss.pipeline` |
| `processed/` | `base_objetivo.pkl`, `resumen_cohortes.csv` | `python -m fuga_ipss.pipeline` |

La descripción de cada variable está en [`docs/03_diccionario_variables/`](../docs/03_diccionario_variables/).
