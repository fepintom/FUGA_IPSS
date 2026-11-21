"""Rendimiento académico: carga y agregación por estudiante (sección 3.3)."""
from __future__ import annotations

import pandas as pd

COLS_DESCARTAR = ["Número", "NOMBRE", "PATERNO", "MATERNO", "ESTADO_ASIGNATURA"]


def preparar(raw: pd.DataFrame) -> pd.DataFrame:
    """Descarta columnas anonimizadas o constantes y normaliza tipos."""
    r = raw.drop(columns=COLS_DESCARTAR, errors="ignore").copy()
    r["RUT"] = r["RUT"].astype(str).str.strip().str.upper()
    r["FECHAINICIO"] = pd.to_datetime(r["FECHAINICIO"], dayfirst=True)
    r["FECHAFIN"] = pd.to_datetime(r["FECHAFIN"], dayfirst=True)
    return r


def agregar_por_estudiante(r: pd.DataFrame, hasta: pd.Timestamp | None = None) -> pd.DataFrame:
    """Indicadores de desempeño y desconexión académica por estudiante.

    `hasta` limita a evaluaciones cuyo periodo terminó antes de esa fecha
    (regla temporal para el Modelo B, al cierre del primer periodo).
    """
    d = r if hasta is None else r[r["FECHAFIN"] < hasta]
    agg = d.groupby("RUT").agg(
        primera_clase=("FECHAINICIO", "min"),
        ultima_clase=("FECHAFIN", "max"),
        n_evaluaciones=("Nota", "size"),
        nota_promedio=("Nota", "mean"),
        pct_reprobadas=("ESTADO", lambda s: (s == "R").mean()),
        pct_nota_minima=("Nota", lambda s: (s <= 1.0).mean()),
        cursa_2025=("ANO", lambda s: (s == 2025).any()),
    )
    agg.index.name = "token"
    return agg
