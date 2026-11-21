"""Pipeline reproducible: de los archivos de origen a la tabla base del modelo.

Uso, desde la raíz del repositorio:

    python -m fuga_ipss.pipeline                  # rutas por defecto (data/raw)
    python -m fuga_ipss.pipeline --raw otra/ruta  # otra carpeta de origen

Genera:
    data/interim/contactabilidad_log_limpio.pkl
    data/processed/base_objetivo.pkl
    data/processed/resumen_cohortes.csv   (solo cifras agregadas)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from . import config, contactabilidad, encuesta, objetivo, rendimiento

log = logging.getLogger("fuga_ipss")


def ejecutar(raw: Path = config.DATA_RAW, interim: Path = config.DATA_INTERIM,
             processed: Path = config.DATA_PROCESSED,
             conservar_contactos_mismo_dia: bool = False) -> pd.DataFrame:
    interim.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    log.info("Contactabilidad: limpieza")
    log_limpio = contactabilidad.limpiar(pd.read_excel(raw / config.ARCHIVO_CONTACTABILIDAD),
                                         conservar_contactos_mismo_dia)
    log_limpio.to_pickle(interim / "contactabilidad_log_limpio.pkl")
    log.info("  %s interacciones de %s estudiantes", len(log_limpio), log_limpio["RUT_ALUMNO"].nunique())

    log.info("Encuesta: unificación de cohortes")
    enc = encuesta.unificar({a: pd.read_excel(raw / f) for a, f in config.ARCHIVOS_ENCUESTA.items()})
    log.info("  %s respuestas, %s estudiantes", len(enc), enc["token"].nunique())

    log.info("Rendimiento: agregación por estudiante")
    rend = rendimiento.agregar_por_estudiante(rendimiento.preparar(pd.read_excel(raw / config.ARCHIVO_RENDIMIENTO)))

    log.info("Variable objetivo")
    base = objetivo.construir_base(enc, rend.index, log_limpio["RUT_ALUMNO"].dropna().unique())
    base.to_pickle(processed / "base_objetivo.pkl")
    resumen = objetivo.resumen_por_cohorte(base)
    resumen.round(3).to_csv(processed / "resumen_cohortes.csv")
    log.info("  %s estudiantes, tasa de deserción %.1f%%", len(base), 100 * base["DESERCION"].mean())
    return resumen


def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline de datos FUGA IPSS")
    p.add_argument("--raw", type=Path, default=config.DATA_RAW)
    p.add_argument("--interim", type=Path, default=config.DATA_INTERIM)
    p.add_argument("--processed", type=Path, default=config.DATA_PROCESSED)
    p.add_argument("--conservar-contactos-mismo-dia", action="store_true",
                   help="No eliminar contactos del mismo día con texto distinto")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(ejecutar(a.raw, a.interim, a.processed, a.conservar_contactos_mismo_dia).round(3).to_string())


if __name__ == "__main__":
    main()
