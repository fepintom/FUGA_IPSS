"""Parámetros del proyecto FUGA IPSS.

Todo lo que es una decisión de negocio o un supuesto queda aquí, en un solo
lugar, para que cambiarlo no exija tocar la lógica del pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
DATA_RAW = RAIZ / "data" / "raw"
DATA_INTERIM = RAIZ / "data" / "interim"
DATA_PROCESSED = RAIZ / "data" / "processed"

ARCHIVO_CONTACTABILIDAD = "Contactabilidad_SGE.xlsx"
ARCHIVO_RENDIMIENTO = "rendimiento_academico_2024-2025.xlsx"
ARCHIVOS_ENCUESTA = {
    2024: "encuesta_caracterizacion_2024.xlsx",
    2025: "encuesta_caracterizacion_2025.xlsx",
    2026: "encuesta_caracterizacion_2026.xlsx",
}

# --------------------------------------------------------------------------
# Variable objetivo
# --------------------------------------------------------------------------
# SUPUESTO: fecha de corte del Estado académico. Se usa el fin del log de
# contactabilidad hasta que Registro Académico informe la fecha real (R2).
FECHA_CORTE = pd.Timestamp("2026-08-31")

# DESERCION (principal): salió del sistema, definitiva o temporalmente.
MAPA_DESERCION = {"ELIMINADO": 1, "SUSPENDIDO": 1, "VIGENTE": 0, "TITULADO": 0, "EGRESADO": 0}
# DESERCION_ESTRICTA (sensibilidad): solo ELIMINADO; SUSPENDIDO queda fuera.
MAPA_DESERCION_ESTRICTA = {"ELIMINADO": 1, "VIGENTE": 0, "TITULADO": 0, "EGRESADO": 0}

DIAS_POR_MES = 30.44

# Columnas de la encuesta (LimeSurvey) que se usan para construir la base.
COLS_CLAVE_ENCUESTA = {
    "token. Código de acceso": "token",
    "submitdate. Fecha de envío": "fecha_encuesta",
    "Carrera": "carrera",
    "Jornada / modalidad": "jornada",
    "Estado académico": "estado",
}

# --------------------------------------------------------------------------
# Contactabilidad
# --------------------------------------------------------------------------
# Un texto repetido al menos este número de veces se trata como plantilla.
UMBRAL_PLANTILLA = 20
PATRON_VOZ_FUNCIONARIO = r"^ESTIMAD|JUNTO CON SALUDAR"
SEPARADOR_RESPUESTA = "SE LE RESPONDE"

LLAVES_DUPLICADO = ["RUT_ALUMNO", "FECHA_COMUNICO", "ASUNTO", "TIPO_COMUNICACION", "Rut_responsable"]

# Indicadores TX_* derivados del texto de las observaciones.
PATRONES_TX = {
    "NO_CONTESTA": r"\bNO CONTEST|\bNO RESPONDE|SIN EXITO|\bNO LE LLEGA|ERRONEO|NO CORRESPONDE AL|BUZON|APAGADO|SE INTENT[OA] (?:CONTACT|COMUNIC)",
    "RESPONDE": r"(?:ALUMN[OA]|ESTUDIANTE) (?:CONTESTA|RESPONDE|INDICA|SENALA|COMENTA|CONFIRMA)",
    "INICIA_ALUMNO": r"(?:ALUMN[OA]|ESTUDIANTE) SE CONTACTA",
    "INASISTENCIA": r"\bNO (?:HA |A )?ASISTID|INASISTENCIA|\bNO ASISTE|AUSENT|NO HA (?:ENTRADO|INGRESADO|CONECTADO)",
    "SIN_ENTREGAS": r"\bENTREGAS?\b|INCUMPLIMIENTO|\bEVA ?\d|NO PARTICIPA",
    "INSCRIPCION": r"INSCRI|TOMA DE RAMOS",
    "NO_MATRICULADO": r"\bNO SE (?:A |HA )?MATRICUL|\bNO (?:ESTA|SE ENCUENTRA) MATRICUL|AUN NO (?:SE )?MATRICUL",
    "MATRICULADO": r"\bSE MATRICULO|YA (?:SE )?MATRICUL|YA ESTA MATRICUL",
    "FINANCIERO": r"FINANCI|DEUDA|MOROS|\bPAGOS?\b|ARANCEL|BECA|\bCAE\b|GRATUIDAD|CREDITO",
    "DESISTE": r"DESIST|SUSPEN|ELIMINACION|\bRETIR|CONGEL|ABANDON",
    "CONTINUA": r"(?:QUIERE|DESEA|VA A|INDICA QUE) (?:SEGUIR|CONTINUAR)|PONERSE AL DIA|PONDRA AL DIA",
    "NO_CONTINUA": r"\bNO (?:VA A |QUIERE |DESEA |PODRA |PUEDE )?(?:CONTINUAR|SEGUIR)\b|\bNO CONTINUARA|\bNO SEGUIRA",
    "CANAL_WSP": r"WTSP|\bWSP|WHATSAPP|WASAP|\bWTS\b",
    "CANAL_CORREO": r"CORREO(?! INSTITUCIONAL)",
    "TITULACION": r"TITULACION|\bTITULAR|EGRESAD",
}
# Indicadores que deben leerse solo en la voz del estudiante.
TX_VOZ_ALUMNO = ["DESISTE", "CONTINUA", "NO_CONTINUA"]
# Indicadores que se anulan en plantillas (el texto masivo siempre los contiene).
TX_ANULAR_EN_PLANTILLA = TX_VOZ_ALUMNO + ["FINANCIERO"]

# Señales contemporáneas o posteriores a la deserción: NO son predictores.
TX_LEAKAGE = ["TX_DESISTE", "TX_NO_CONTINUA", "TX_NO_MATRICULADO"]
CAT_ASUNTO_LEAKAGE = ["RETENCION"]
