"""Variable objetivo y tabla base del modelo (secciones 3.4 y 3.5)."""
from __future__ import annotations

import pandas as pd

from . import config, encuesta

COLUMNAS_BASE = ["token", "cohorte", "fecha_encuesta", "carrera", "jornada", "estado",
                 "DESERCION", "DESERCION_ESTRICTA", "meses_exposicion",
                 "tiene_rendimiento", "tiene_contacto"]


def construir_base(enc: pd.DataFrame, ids_rendimiento, ids_contacto,
                   fecha_corte: pd.Timestamp = config.FECHA_CORTE) -> pd.DataFrame:
    """Una fila por estudiante encuestado con DESERCION y su tiempo de exposición.

    SIN DATO queda como NaN en ambas etiquetas; SUSPENDIDO queda como NaN en
    DESERCION_ESTRICTA. `meses_exposicion` debe controlarse al modelar porque
    el estado académico no trae fecha del evento.
    """
    base = encuesta.primera_cohorte(enc).copy()
    base["DESERCION"] = base["estado"].map(config.MAPA_DESERCION)
    base["DESERCION_ESTRICTA"] = base["estado"].map(config.MAPA_DESERCION_ESTRICTA)
    base["meses_exposicion"] = ((fecha_corte - base["fecha_encuesta"]).dt.days
                                / config.DIAS_POR_MES).round(1)
    base["tiene_rendimiento"] = base["token"].isin(set(ids_rendimiento))
    base["tiene_contacto"] = base["token"].isin(set(ids_contacto))
    return base[COLUMNAS_BASE].reset_index(drop=True)


def resumen_por_cohorte(base: pd.DataFrame) -> pd.DataFrame:
    """Tasas de deserción y cobertura de datos por cohorte, con fila Total."""
    def _agg(g):
        return pd.Series({
            "estudiantes": len(g),
            "con_etiqueta": g["DESERCION"].count(),
            "tasa_desercion": g["DESERCION"].mean(),
            "tasa_desercion_estricta": g["DESERCION_ESTRICTA"].mean(),
            "meses_exposicion_mediana": g["meses_exposicion"].median(),
            "pct_con_rendimiento": g["tiene_rendimiento"].mean(),
            "pct_con_contacto": g["tiene_contacto"].mean(),
        })
    por_cohorte = pd.DataFrame({k: _agg(g) for k, g in base.groupby("cohorte")}).T
    por_cohorte.loc["Total"] = _agg(base)
    return por_cohorte
