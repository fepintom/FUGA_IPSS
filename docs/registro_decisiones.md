# Registro de decisiones, problemas abiertos y solicitudes

Documento vivo del proyecto FUGA IPSS. Se actualiza cada vez que se toma una decisión de método o llega información nueva del IP.

## Decisiones

| Fecha | Decisión | Fase CRISP-DM |
|---|---|---|
| 10-11-2026 | Variable objetivo `DESERCION` = ELIMINADO o SUSPENDIDO (1) frente a VIGENTE, TITULADO o EGRESADO (0); SIN DATO excluido | 3 |
| 10-11-2026 | Versión estricta `DESERCION_ESTRICTA` (solo ELIMINADO) para análisis de sensibilidad | 3 |
| 10-11-2026 | Estudiantes repetidos entre cohortes: se conserva la primera cohorte | 3 |
| 10-11-2026 | Señales `TX_DESISTE`, `TX_NO_CONTINUA`, `TX_NO_MATRICULADO` y asunto RETENCION excluidas como predictores (leakage) | 4 |
| 17-11-2026 | Notebook reorganizado según CRISP-DM | — |
| 21-11-2026 | Proyecto publicado como repositorio; pipeline de producción en `src/fuga_ipss/`, validado contra el notebook con resultados idénticos | 6 |
| 21-11-2026 | Predictores del Modelo A elegidos por reglas sobre el diccionario: secciones sustantivas, presentes en los 3 años, sin texto abierto. Se excluyen los atributos protegidos (sexo, identidad de género, orientación sexual, pueblo originario, discapacidad, salud, nacionalidad, situación migratoria); el contexto socioeconómico se permite | 4 |
| 21-11-2026 | Modelo de referencia: regresión logística con pesos de clase y C = 0,05 fijado de antemano, elegida sobre gradient boosting por PR-AUC en la validación temporal | 4 |
| 21-11-2026 | Validación principal temporal: entrenar con 2024–2025, probar con 2026. Métrica de negocio: captura de desertores en el 20% de mayor riesgo | 5 |
| 21-11-2026 | El Modelo A no se usa para alertas individuales mientras su discriminación y equidad sigan en el nivel actual; producto principal propuesto: Modelo B al cierre del primer periodo | 6 |

## Problemas abiertos

1. **Sin fecha del evento.** El estado académico no trae fecha de corte ni fecha de cambio de estado, así que no se puede fijar un horizonte de predicción ni cortar los predictores en el tiempo.
2. **Exposición desigual entre cohortes** (≈ 31, 18 y 7,5 meses). Hay que controlar `meses_exposicion` o modelar por cohorte.
3. **Significado institucional** de ELIMINADO y SUSPENDIDO. Además, falta explicar por qué la cohorte 2026 tiene más eliminados que la 2025.
4. **Cobertura.** Solo los encuestados tienen etiqueta; 3.588 estudiantes contactados quedan fuera.
5. **Leakage.** Las señales contemporáneas a la deserción no pueden ser predictores sin una fecha de corte.
6. **Contactos del mismo día.** La limpieza elimina 4.599 registros con igual estudiante, fecha, asunto, tipo y responsable, aunque el texto de la observación sea distinto (por ejemplo, un llamado sin respuesta y luego un WhatsApp). La intención documentada era conservarlos. Las cifras informadas (38.616 interacciones) corresponden a la versión que los elimina. Conservarlos deja 43.202 interacciones y está disponible con `--conservar-contactos-mismo-dia`. **Pendiente de decidir** antes del modelado, porque afecta los indicadores de frecuencia de contacto.

7. **Equidad del Modelo A.** Con el corte del 20%, alerta al 37% de la jornada vespertina y al 13% de la online, con tasas de deserción parecidas. También alerta más a mujeres y a extranjeros. Hay que corregirlo (umbral por jornada o recalibración) antes de cualquier uso individual.

## Solicitudes a Registro Académico

| N° | Solicitud | Prioridad | Qué habilita |
|---|---|---|---|
| R1 | Historial de cambios de estado académico con fecha (matrícula 2024–2026) | Crítica | Etiqueta a horizonte fijo y corte temporal exacto de los predictores |
| R2 | Fecha de extracción del Estado académico en cada archivo de encuesta | Crítica | Cálculo correcto de `meses_exposicion` |
| R3 | Definición oficial de los estados y explicación de la tasa de la cohorte 2026 | Alta | Validar la etiqueta |
| R4 | Estado académico de toda la matrícula | Alta | Más población etiquetada y control del sesgo de quienes responden la encuesta |
| R5 | Notas desde 2025-P2 (incluida la cohorte 2026) | Alta | Modelo B para las cohortes 2025 y 2026 |
| R6 | Tabla de equivalencias entre códigos y nombres de carrera | Media | Cruzar contactabilidad (`CODCARR`) con la carrera de la encuesta |
