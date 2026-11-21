"""Predictores del Modelo A (al ingreso) a partir de la encuesta de caracterización.

Las variables se eligen con reglas sobre el diccionario de variables, no a mano,
para que la selección sea auditable y se mantenga cuando cambie la encuesta.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config

DICCIONARIO_ENCUESTA = config.RAIZ / "docs" / "03_diccionario_variables" / "Diccionario_Encuesta_Caracterizacion.xlsx"

SECCIONES_PREDICTORAS = [
    "ANTECEDENTES PERSONALES",
    "ANTECEDENTES FAMILIARES Y SOCIOECONÓMICOS",
    "TRAYECTORIA FORMATIVA Y LABORAL",
    "ANTECEDENTES DE LA INSTITUCIÓN Y PROGRAMA",
    "ESTILO DE VIDA Y SUSTENTABILIDAD",
    "BIENESTAR PARA EL PROCESO EDUCATIVO",
    "DISPOSICIÓN HACIA LA EDUCACIÓN SUPERIOR",
]
# Datos sensibles que sí pueden usarse: el contexto socioeconómico (ingreso,
# financiamiento) es un factor legítimo y accionable de retención (ayudas).
SENSIBLES_PERMITIDOS = ["situación socioeconómica"]
MAX_CATEGORIAS = 40
VAR_ANIO_EGRESO = "G03Q30"   # año de egreso de la educación media
VAR_INGRESO = "G02Q17"       # ingreso mensual del grupo familiar


def codigo(columna: str) -> str:
    """'G01Q19[SQ002]. ¿Cómo vas...' -> 'G01Q19[SQ002]'."""
    return str(columna).split(". ", 1)[0].strip()


def seleccionar_variables(diccionario: Path = DICCIONARIO_ENCUESTA) -> pd.DataFrame:
    """Aplica las reglas de selección y devuelve las filas elegidas del diccionario."""
    d = pd.read_excel(diccionario, sheet_name="Variables")
    sens = d["Sensibilidad"].fillna("—").astype(str)
    permitido = (sens == "—") | sens.str.contains("|".join(SENSIBLES_PERMITIDOS), regex=True)
    tipo = d["Tipo de pregunta"].fillna("").astype(str)
    reglas = (
        d["Sección"].isin(SECCIONES_PREDICTORAS)
        & (d[["En 2024", "En 2025", "En 2026"]] == "Sí").all(axis=1)   # comparable entre cohortes
        & permitido
        & ~tipo.str.contains("Texto abierto|Consentimiento", regex=True)
        & ~d["Variable"].astype(str).str.contains(r"\[other\]", regex=True)
        & ((d["N° valores distintos"].fillna(0) <= MAX_CATEGORIAS) | (tipo == "Numérica"))
    )
    return d.loc[reglas].reset_index(drop=True)


def _etiqueta(fila) -> str:
    p = str(fila["Pregunta"]).strip()
    p = p if len(p) <= 90 else p[:87].rsplit(" ", 1)[0] + "…"
    item = fila["Ítem / opción"]
    return f"{p} [{item}]" if pd.notna(item) else p


def etiquetas(seleccion: pd.DataFrame) -> dict[str, str]:
    """Código de variable -> texto legible para reportes."""
    return {r["Variable"]: _etiqueta(r) for _, r in seleccion.iterrows()}


def construir_matriz(encuestas: dict[int, pd.DataFrame], seleccion: pd.DataFrame) -> pd.DataFrame:
    """Una fila por respuesta (token, cohorte) con los predictores elegidos.

    Las variables numéricas quedan como número; el resto como texto
    categórico. Agrega `anios_desde_egreso_media` y `log_ingreso_familiar`.
    """
    codigos = list(seleccion["Variable"])
    partes = []
    for anio, df in encuestas.items():
        ren = {c: codigo(c) for c in df.columns}
        x = df.rename(columns=ren)
        x = x.loc[:, ~x.columns.duplicated()]
        p = x.reindex(columns=["token"] + codigos).copy()
        p["carrera"] = df["Carrera"].values
        p["jornada"] = df["Jornada / modalidad"].values
        p["cohorte"] = anio
        partes.append(p)
    m = pd.concat(partes, ignore_index=True).copy()
    m["token"] = m["token"].astype(str).str.strip().str.upper()

    anio_egreso = pd.to_numeric(m.pop(VAR_ANIO_EGRESO), errors="coerce") if VAR_ANIO_EGRESO in m else None
    if anio_egreso is not None:
        m["anios_desde_egreso_media"] = (m["cohorte"] - anio_egreso).clip(lower=0, upper=40)
    if VAR_INGRESO in m:
        ing = pd.to_numeric(m.pop(VAR_INGRESO), errors="coerce").clip(lower=0)
        m["log_ingreso_familiar"] = np.log1p(ing.clip(upper=ing.quantile(0.99)))

    for c in m.columns.difference(["token", "cohorte"]):
        num = pd.to_numeric(m[c], errors="coerce")
        if m[c].notna().sum() and num.notna().sum() >= 0.95 * m[c].notna().sum():
            m[c] = num
        else:
            t = m[c].astype("string").str.strip()
            m[c] = t.astype(object).where(t.notna(), np.nan)   # scikit-learn no acepta pd.NA
    return m


def tipos(m: pd.DataFrame, excluir=("token", "cohorte")) -> tuple[list[str], list[str]]:
    """Separa columnas numéricas y categóricas."""
    cols = [c for c in m.columns if c not in excluir]
    num = [c for c in cols if pd.api.types.is_numeric_dtype(m[c])]
    return num, [c for c in cols if c not in num]
