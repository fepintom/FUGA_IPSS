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

## Problemas abiertos

1. **Sin fecha del evento.** El estado académico no trae fecha de corte ni fecha de cambio de estado, así que no se puede fijar un horizonte de predicción ni cortar los predictores en el tiempo.
2. **Exposición desigual entre cohortes** (≈ 31, 18 y 7,5 meses). Hay que controlar `meses_exposicion` o modelar por cohorte.
3. **Significado institucional** de ELIMINADO y SUSPENDIDO. Además, falta explicar por qué la cohorte 2026 tiene más eliminados que la 2025.
4. **Cobertura.** Solo los encuestados tienen etiqueta; 3.588 estudiantes contactados quedan fuera.
5. **Leakage.** Las señales contemporáneas a la deserción no pueden ser predictores sin una fecha de corte.
6. **Contactos del mismo día.** La limpieza elimina 4.599 registros con igual estudiante, fecha, asunto, tipo y responsable, aunque el texto de la observación sea distinto (por ejemplo, un llamado sin respuesta y luego un WhatsApp). La intención documentada era conservarlos. Las cifras informadas (38.616 interacciones) corresponden a la versión que los elimina. Conservarlos deja 43.202 interacciones y está disponible con `--conservar-contactos-mismo-dia`. **Pendiente de decidir** antes del modelado, porque afecta los indicadores de frecuencia de contacto.

## Solicitudes a Registro Académico

| N° | Solicitud | Prioridad | Qué habilita |
|---|---|---|---|
| R1 | Historial de cambios de estado académico con fecha (matrícula 2024–2026) | Crítica | Etiqueta a horizonte fijo y corte temporal exacto de los predictores |
| R2 | Fecha de extracción del Estado académico en cada archivo de encuesta | Crítica | Cálculo correcto de `meses_exposicion` |
| R3 | Definición oficial de los estados y explicación de la tasa de la cohorte 2026 | Alta | Validar la etiqueta |
| R4 | Estado académico de toda la matrícula | Alta | Más población etiquetada y control del sesgo de quienes responden la encuesta |
| R5 | Notas desde 2025-P2 (incluida la cohorte 2026) | Alta | Modelo B para las cohortes 2025 y 2026 |
| R6 | Tabla de equivalencias entre códigos y nombres de carrera | Media | Cruzar contactabilidad (`CODCARR`) con la carrera de la encuesta |
