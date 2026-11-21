"""Pruebas del pipeline con datos sintéticos (nunca con datos reales)."""
import pandas as pd
import pytest

from fuga_ipss import contactabilidad as ct
from fuga_ipss import encuesta, objetivo, rendimiento


def _log_raw():
    filas = [
        # estudiante, fecha, asunto, observación, carrera
        ("EST-1", "2025-03-10", "Académico", "Se contacta a alumno. No contesta", "C1"),
        ("EST-1", "2025-03-10", "Académico", "Alumno contesta e indica que quiere continuar", "C1"),
        ("EST-2", "2025-04-01", "Retención", "Alumna indica que desea suspender. SE LE RESPONDE que puede retirarse", None),
        ("EST-2", "2025-04-02", "Finanzas", "Tiene deuda de arancel", "C2"),
    ]
    plantilla = "Estimado estudiante, si deseas desistir o tienes problemas financieros escribe a x@ipss.cl"
    filas += [(f"EST-{i}", "2025-05-01", "Académico", plantilla, "C3") for i in range(10, 35)]
    df = pd.DataFrame(filas, columns=["RUT_ALUMNO", "FECHA_COMUNICO", "Asunto", "OBSERVACION", "CODCARR"])
    df["Número"] = range(len(df))
    df["TIPO_COMUNICACION"] = "LLAMADO"
    df["Rut_responsable"] = "F1"
    df["Nombre_responsable"] = "X"
    f = pd.to_datetime(df["FECHA_COMUNICO"])
    df["DIA"], df["MES"], df["ANIO"] = f.dt.day, f.dt.month, f.dt.year
    df.loc[2, "CODCARR"] = None
    return df


def test_norm_txt():
    assert ct.norm_txt("  Matrícula\nPendiente ") == "MATRICULA PENDIENTE"
    assert pd.isna(ct.norm_txt(None))


@pytest.mark.parametrize("asunto,esperado", [
    ("SEGUIMIENTO RETENCION", "RETENCION"), ("ACADEMICO", "ACADEMICO"),
    ("NO CONTESTA", "NO_CONTACTO"), (None, "OTRO"),
])
def test_categoria_asunto(asunto, esperado):
    assert ct.categoria_asunto(asunto) == esperado


def test_limpieza_y_plantillas():
    log = ct.limpiar(_log_raw())
    # Mismo estudiante, día, asunto, tipo y responsable: se deduplica por defecto
    assert (log["RUT_ALUMNO"] == "EST-1").sum() == 1
    assert (ct.limpiar(_log_raw(), conservar_contactos_mismo_dia=True)["RUT_ALUMNO"] == "EST-1").sum() == 2
    # Carrera imputada con la moda del estudiante
    assert log.loc[log["RUT_ALUMNO"] == "EST-2", "CODCARR"].eq("C2").all()
    # Las plantillas no generan señales de voz del alumno ni financieras
    pl = log[log["ES_PLANTILLA"] == 1]
    assert len(pl) == 25 and pl[["TX_DESISTE", "TX_FINANCIERO"]].sum().sum() == 0
    assert not pl["OBS_LIMPIA"].str.contains("@").any()
    # DESISTE se lee solo en la voz del alumno, antes de "SE LE RESPONDE"
    e2 = log[(log["RUT_ALUMNO"] == "EST-2") & (log["CAT_ASUNTO"] == "RETENCION")].iloc[0]
    assert e2["TX_DESISTE"] == 1


def test_agregacion_excluye_leakage_y_respeta_corte():
    log = ct.limpiar(_log_raw(), conservar_contactos_mismo_dia=True)
    agg = ct.agregar_por_estudiante(log, hasta=pd.Timestamp("2025-04-01"))
    assert "pct_TX_DESISTE" not in agg and "pct_TX_NO_CONTESTA" in agg
    assert "EST-2" not in agg.index          # sus contactos son posteriores al corte
    assert agg.loc["EST-1", "n_contactos"] == 2


def test_variable_objetivo():
    enc = encuesta.unificar({
        2024: pd.DataFrame({"token. Código de acceso": ["est-a", "EST-B"],
                            "submitdate. Fecha de envío": ["2024-03-01", "2024-03-01"],
                            "Carrera": ["C1", "C1"], "Jornada / modalidad": ["D", "D"],
                            "Estado académico": ["ELIMINADO", "SUSPENDIDO"]}),
        2025: pd.DataFrame({"token. Código de acceso": ["EST-A", "EST-C", "EST-D"],
                            "submitdate. Fecha de envío": ["2025-03-01"] * 3,
                            "Carrera": ["C1"] * 3, "Jornada / modalidad": ["V"] * 3,
                            "Estado académico": ["VIGENTE", "TITULADO", "SIN DATO"]}),
    })
    base = objetivo.construir_base(enc, ids_rendimiento=["EST-A"], ids_contacto=[])
    b = base.set_index("token")
    assert len(base) == 4 and b.loc["EST-A", "cohorte"] == 2024      # primera cohorte
    assert b.loc["EST-A", "DESERCION"] == 1 and b.loc["EST-B", "DESERCION"] == 1
    assert pd.isna(b.loc["EST-B", "DESERCION_ESTRICTA"])
    assert b.loc["EST-C", "DESERCION"] == 0 and pd.isna(b.loc["EST-D", "DESERCION"])
    assert b.loc["EST-A", "tiene_rendimiento"]
    r = objetivo.resumen_por_cohorte(base)
    assert r.loc["Total", "estudiantes"] == 4


def test_rendimiento():
    raw = pd.DataFrame({"RUT": [" est-1", "EST-1"], "Nota": [1.0, 5.0], "ESTADO": ["R", "A"],
                        "ANO": [2024, 2025], "FECHAINICIO": ["01-03-2024"] * 2,
                        "FECHAFIN": ["30-06-2024", "30-06-2025"], "NOMBRE": ["x"] * 2})
    agg = rendimiento.agregar_por_estudiante(rendimiento.preparar(raw))
    assert agg.loc["EST-1", "pct_nota_minima"] == 0.5 and agg.loc["EST-1", "cursa_2025"]
    assert rendimiento.agregar_por_estudiante(rendimiento.preparar(raw), hasta=pd.Timestamp("2025-01-01")
                                              ).loc["EST-1", "n_evaluaciones"] == 1
