"""Unificación de la encuesta de caracterización por cohorte (sección 3.2)."""
from __future__ import annotations

import pandas as pd

from . import config


def unificar(encuestas: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Une las encuestas anuales en una tabla con la columna `cohorte`.

    Solo toma las columnas clave (config.COLS_CLAVE_ENCUESTA). Los ítems de la
    encuesta se incorporan como predictores en la fase de modelado.
    """
    partes = []
    for anio, df in encuestas.items():
        p = df[list(config.COLS_CLAVE_ENCUESTA)].rename(columns=config.COLS_CLAVE_ENCUESTA)
        p["cohorte"] = anio
        partes.append(p)
    enc = pd.concat(partes, ignore_index=True)
    enc["token"] = enc["token"].astype(str).str.strip().str.upper()
    enc["fecha_encuesta"] = pd.to_datetime(enc["fecha_encuesta"], errors="coerce")
    return enc


def primera_cohorte(enc: pd.DataFrame) -> pd.DataFrame:
    """Un registro por estudiante; los repetidos conservan su primera cohorte."""
    return enc.sort_values("cohorte", kind="stable").drop_duplicates("token", keep="first")
