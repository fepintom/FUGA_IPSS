# Diccionario de variables

Un diccionario por fuente de datos. Cada archivo parte con una hoja **Documento**, que describe la fuente (origen, granularidad, cobertura, llave), y sigue con las variables. Para cada variable se indica descripción, tipo de dato, tipo de variable, % de nulos, valores o rango, sensibilidad y observaciones.

| Archivo | Fuente | Hojas | Variables |
|---|---|---|---|
| [`Diccionario_Encuesta_Caracterizacion.xlsx`](Diccionario_Encuesta_Caracterizacion.xlsx) | Encuesta de caracterización de ingreso (LimeSurvey), cohortes 2024, 2025 y 2026 en un solo diccionario | Documento · Variables · Resumen por sección | 365 |
| [`Diccionario_Rendimiento_Academico.xlsx`](Diccionario_Rendimiento_Academico.xlsx) | Notas por evaluación, 2024-P1 a 2025-P1 | Documento · Variables | 20 |
| [`Diccionario_Contactabilidad.xlsx`](Diccionario_Contactabilidad.xlsx) | Log de interacciones funcionario-estudiante del SGE, ene-2024 a ago-2026 | Documento · Variables originales · Variables derivadas | 12 originales + 25 derivadas |

## Llave de unión

Las tres fuentes usan el mismo identificador pseudonimizado (`EST-…`), con nombres distintos:

| Fuente | Columna |
|---|---|
| Encuesta | `token` |
| Rendimiento | `RUT` |
| Contactabilidad | `RUT_ALUMNO` |

## Variables construidas por el proyecto

| Variable | Definición | Dónde se construye |
|---|---|---|
| `DESERCION` | 1 si el estado académico es ELIMINADO o SUSPENDIDO; 0 si es VIGENTE, TITULADO o EGRESADO; vacío si es SIN DATO | `src/fuga_ipss/objetivo.py` |
| `DESERCION_ESTRICTA` | 1 solo si es ELIMINADO; SUSPENDIDO y SIN DATO quedan vacíos | `src/fuga_ipss/objetivo.py` |
| `meses_exposicion` | Meses entre la respuesta de la encuesta y la fecha de corte (supuesto: 31-08-2026) | `src/fuga_ipss/objetivo.py` |
| `TX_*` | Indicadores de texto de las observaciones de contactabilidad (no contesta, inasistencia, financiero, etc.) | `src/fuga_ipss/contactabilidad.py` |
| `ES_PLANTILLA` | 1 si el texto es una plantilla o correo masivo; no genera señales | `src/fuga_ipss/contactabilidad.py` |

Las reglas exactas de cada indicador `TX_*` están en la hoja *Variables derivadas* del diccionario de contactabilidad y en `src/fuga_ipss/config.py`.

## Variables sensibles

Los diccionarios marcan en la columna **Sensibilidad** los datos personales y sensibles (identificador, nacionalidad, situación migratoria, pueblo originario, discapacidad, salud y salud mental, situación socioeconómica, sexo, identidad de género y orientación sexual). Antes de usar cualquiera como predictor se evalúa su sesgo (fase 5 de CRISP-DM).
