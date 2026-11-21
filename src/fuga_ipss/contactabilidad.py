"""Limpieza del log de contactabilidad del SGE (sección 3.1 del notebook)."""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from . import config


def norm_txt(s) -> str | float:
    """Mayúsculas, sin tildes ni saltos de línea y con espacios simples."""
    if pd.isna(s):
        return np.nan
    s = str(s).replace("\\n", " ").replace("\n", " ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def categoria_asunto(a) -> str:
    """Agrupa el asunto libre del contacto en categorías de negocio."""
    if pd.isna(a):
        return "OTRO"
    if "NO CONTESTA" in a or "ERRONEO" in a:
        return "NO_CONTACTO"
    if "RETENCION" in a:
        return "RETENCION"
    if "FINANZ" in a or "FINANCIAMIENTO" in a:
        return "FINANZAS"
    if "NO PARTICIPACION" in a or "EVALUACION" in a:
        return "EVALUACION"
    if "EXPERIENCIA" in a:
        return "EXPERIENCIA"
    if "ACADEM" in a or "INSCRIPCION" in a:
        return "ACADEMICO"
    if "IMPORTANTE" in a:
        return "IMPORTANTE"
    return "OTRO"


def limpiar(raw: pd.DataFrame, conservar_contactos_mismo_dia: bool = False) -> pd.DataFrame:
    """Devuelve el log limpio, una fila por interacción, con indicadores TX_*.

    conservar_contactos_mismo_dia:
        False (por defecto) reproduce el notebook y las cifras informadas
        (38.616 interacciones): elimina registros con igual estudiante, fecha,
        asunto, tipo y responsable aunque el texto difiera.
        True conserva esos registros cuando el texto es distinto, que es lo
        que describe el registro de decisiones. Decisión pendiente.
    """
    c = raw.drop(columns=["Número"], errors="ignore").copy()

    c["ASUNTO"] = c["Asunto"].map(norm_txt).str.replace(r"[^A-Z0-9 /-]", "", regex=True).str.strip()
    c["OBS_LIMPIA"] = c["OBSERVACION"].map(norm_txt)
    for col in ["RUT_ALUMNO", "CODCARR", "Rut_responsable", "TIPO_COMUNICACION"]:
        c[col] = c[col].astype("string").str.strip().str.upper()
    c["FECHA_COMUNICO"] = pd.to_datetime(c["FECHA_COMUNICO"], errors="coerce")

    # Carrera faltante: moda de la carrera del mismo estudiante.
    moda = (c.dropna(subset=["CODCARR"]).groupby("RUT_ALUMNO")["CODCARR"]
              .agg(lambda s: s.mode().iat[0]))
    c["CODCARR"] = c["CODCARR"].fillna(c["RUT_ALUMNO"].map(moda))

    c = c.drop(columns=["Asunto", "OBSERVACION", "Nombre_responsable", "DIA", "MES", "ANIO"], errors="ignore")

    llaves = config.LLAVES_DUPLICADO + (["OBS_LIMPIA"] if conservar_contactos_mismo_dia else [])
    c = c.drop_duplicates(subset=llaves)

    c["CAT_ASUNTO"] = c["ASUNTO"].map(categoria_asunto)
    c["ES_SEGUIMIENTO"] = c["ASUNTO"].str.contains("SEGUIMIENTO", na=False).astype(int)

    # Correos fuera del texto y marca de plantillas o correos masivos.
    c["OBS_LIMPIA"] = c["OBS_LIMPIA"].str.replace(r"\S+@\S+", "EMAIL", regex=True)
    freq = c["OBS_LIMPIA"].map(c["OBS_LIMPIA"].value_counts())
    voz_staff = c["OBS_LIMPIA"].str.contains(config.PATRON_VOZ_FUNCIONARIO, regex=True, na=False)
    c["ES_PLANTILLA"] = ((freq >= config.UMBRAL_PLANTILLA) | voz_staff).astype(int)

    return agregar_indicadores_tx(c)


def agregar_indicadores_tx(c: pd.DataFrame) -> pd.DataFrame:
    """Crea los indicadores TX_* a partir de OBS_LIMPIA y ES_PLANTILLA."""
    c = c.drop(columns=[k for k in c if k.startswith("TX_")])
    obs_alumno = c["OBS_LIMPIA"].str.split(config.SEPARADOR_RESPUESTA, n=1, regex=False).str[0]
    for k, patron in config.PATRONES_TX.items():
        texto = obs_alumno if k in config.TX_VOZ_ALUMNO else c["OBS_LIMPIA"]
        c[f"TX_{k}"] = texto.str.contains(patron, regex=True, na=False).astype(int)
    for k in config.TX_ANULAR_EN_PLANTILLA:
        c.loc[c["ES_PLANTILLA"] == 1, f"TX_{k}"] = 0
    return c


def agregar_por_estudiante(log: pd.DataFrame, hasta: pd.Timestamp | None = None,
                           excluir_leakage: bool = True) -> pd.DataFrame:
    """Resume el log por estudiante con contactos anteriores a `hasta`.

    Es la regla temporal de la fase 4: para predecir solo se usan contactos
    anteriores al momento de predicción, y se excluyen las señales
    contemporáneas a la deserción (config.TX_LEAKAGE y asunto RETENCION).
    """
    d = log if hasta is None else log[log["FECHA_COMUNICO"] < hasta]
    tx = [k for k in d if k.startswith("TX_")]
    if excluir_leakage:
        d = d[~d["CAT_ASUNTO"].isin(config.CAT_ASUNTO_LEAKAGE)]
        tx = [k for k in tx if k not in config.TX_LEAKAGE]
    personal = d[d["ES_PLANTILLA"] == 0]
    agg = personal.groupby("RUT_ALUMNO")[tx].mean().add_prefix("pct_")
    agg["n_contactos"] = d.groupby("RUT_ALUMNO").size()
    agg["n_contactos_personalizados"] = personal.groupby("RUT_ALUMNO").size()
    agg["ultimo_contacto"] = d.groupby("RUT_ALUMNO")["FECHA_COMUNICO"].max()
    agg.index.name = "token"
    return agg.fillna({"n_contactos_personalizados": 0})
