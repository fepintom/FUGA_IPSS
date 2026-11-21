"""Modelo de referencia de riesgo de deserción y su evaluación orientada al negocio.

Uso, desde la raíz del repositorio (después de `python -m fuga_ipss.pipeline`):

    python -m fuga_ipss.modelo

Genera (solo cifras agregadas, versionables):
    reports/resultados_modelo.json
    reports/figures/*.png
y, sin versionar (datos por estudiante):
    data/processed/lista_riesgo_2026.csv
    models/modelo_a.joblib

Es un modelo PRELIMINAR: la etiqueta no tiene fecha del evento (ver R1 y R2 en
docs/registro_decisiones.md), así que las cifras deben leerse como evidencia
de que el enfoque funciona, no como el desempeño final.
"""
from __future__ import annotations

import json
import logging
from datetime import date

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config, contactabilidad, features, rendimiento

log = logging.getLogger("fuga_ipss")
SEMILLA = 42
CORTES = (0.10, 0.20, 0.30)
REPORTS = config.RAIZ / "reports"
FIGURES = REPORTS / "figures"
MODELS = config.RAIZ / "models"


# --------------------------------------------------------------------------
# Construcción del modelo
# --------------------------------------------------------------------------
def preprocesador(num: list[str], cat: list[str]) -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                          ("esc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="Sin respuesta")),
                          ("ohe", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                                                sparse_output=False))]), cat),
    ], verbose_feature_names_out=False)


def candidatos(num, cat) -> dict[str, Pipeline]:
    return {
        "Regresión logística": Pipeline([
            ("prep", preprocesador(num, cat)),
            ("clf", LogisticRegression(C=0.05, class_weight="balanced", max_iter=5000))]),
        "Gradient boosting": Pipeline([
            ("prep", preprocesador(num, cat)),
            ("clf", HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15,
                                                   min_samples_leaf=40, l2_regularization=1.0,
                                                   class_weight="balanced", random_state=SEMILLA))]),
    }


# --------------------------------------------------------------------------
# Métricas de negocio
# --------------------------------------------------------------------------
def metricas(y, score) -> dict:
    """Discriminación y captura de desertores al contactar al k% de mayor riesgo."""
    y, score = np.asarray(y), np.asarray(score)
    orden = np.argsort(-score, kind="stable")
    base = y.mean()
    out = {"n": int(len(y)), "desertores": int(y.sum()), "tasa_base": base,
           "roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score)}
    for k in CORTES:
        top = orden[: int(round(k * len(y)))]
        cap = y[top].sum()
        out[f"recall_top{int(k*100)}"] = cap / y.sum()
        out[f"precision_top{int(k*100)}"] = cap / len(top)
        out[f"lift_top{int(k*100)}"] = (cap / len(top)) / base
    return out


def intervalos(y, score, n_boot=1000, claves=("roc_auc", "recall_top20", "precision_top20")) -> dict:
    """Intervalos bootstrap al 95% para las métricas principales."""
    rng = np.random.default_rng(SEMILLA)
    y, score = np.asarray(y), np.asarray(score)
    res = {k: [] for k in claves}
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        m = metricas(y[i], score[i])
        for k in claves:
            res[k].append(m[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in res.items()}


def curva_captura(y, score) -> pd.DataFrame:
    y = np.asarray(y)[np.argsort(-np.asarray(score), kind="stable")]
    pct = np.arange(1, len(y) + 1) / len(y)
    return pd.DataFrame({"pct_contactado": pct, "pct_desertores_capturados": np.cumsum(y) / y.sum()})


def tasa_por_decil(y, score) -> pd.Series:
    d = pd.DataFrame({"y": y, "s": score})
    d["decil"] = pd.qcut(d["s"].rank(method="first", ascending=False), 10, labels=range(1, 11))
    return d.groupby("decil", observed=True)["y"].mean()


# --------------------------------------------------------------------------
# Interpretación y equidad
# --------------------------------------------------------------------------
def factores(modelo: Pipeline, etiquetas: dict[str, str], n: int = 12) -> dict[str, list]:
    """Coeficientes de la regresión logística traducidos a lenguaje de negocio.

    Son asociaciones, no causas: indican qué perfiles concentran más riesgo.
    """
    nombres = modelo.named_steps["prep"].get_feature_names_out()
    coef = modelo.named_steps["clf"].coef_[0]
    filas = []
    for nom, c in zip(nombres, coef):
        if nom.startswith("missingindicator_"):
            base, txt = nom.replace("missingindicator_", ""), "no responde"
        elif nom.startswith(("carrera_", "jornada_")):
            base, txt = nom.split("_", 1)
        else:
            base, txt = nom, None
            for cod in sorted(etiquetas, key=len, reverse=True):
                if nom.startswith(cod + "_"):
                    base, txt = cod, nom[len(cod) + 1:]
                    break
        legible = {"carrera": "Carrera", "jornada": "Jornada",
                   "anios_desde_egreso_media": "Años desde que egresó de la educación media",
                   "log_ingreso_familiar": "Ingreso familiar (escala logarítmica)"}.get(base, etiquetas.get(base, base))
        filas.append({"variable": base, "factor": legible + (f" = {txt}" if txt else ""),
                      "coef": float(c), "odds_ratio": float(np.exp(c))})
    f = pd.DataFrame(filas)
    f = f[~f["factor"].str.contains("infrequent_sklearn", regex=False)]
    return {"riesgo": f.nlargest(n, "coef").to_dict("records"),
            "protectores": f.nsmallest(n, "coef").to_dict("records")}


def equidad(y, score, grupos: pd.Series, k: float = 0.20, n_min: int = 30) -> list[dict]:
    """Tasa de alerta y captura de desertores por grupo, con el corte global."""
    y, score = np.asarray(y), np.asarray(score)
    umbral = np.quantile(score, 1 - k)
    alerta = score >= umbral
    out = []
    for g in grupos.dropna().unique():
        i = (grupos == g).to_numpy()
        if i.sum() < n_min:
            continue
        out.append({"grupo": str(g), "n": int(i.sum()), "tasa_desercion": float(y[i].mean()),
                    "tasa_alerta": float(alerta[i].mean()),
                    "recall": float(alerta[i & (y == 1)].sum() / max(1, (y[i] == 1).sum()))})
    return sorted(out, key=lambda r: -r["n"])


# --------------------------------------------------------------------------
# Modelo B: conducta del primer periodo (solo cohorte 2024)
# --------------------------------------------------------------------------
def conducta_primer_periodo(rend_raw: pd.DataFrame, log_contactos: pd.DataFrame) -> pd.DataFrame:
    """Notas del primer periodo cursado y contactos anteriores a su cierre."""
    r = rendimiento.preparar(rend_raw)
    per = (r.groupby(["RUT", "ANO", "PERIODO"])["FECHAINICIO"].min().reset_index()
             .sort_values(["RUT", "FECHAINICIO"]).drop_duplicates("RUT"))
    r1 = r.merge(per[["RUT", "ANO", "PERIODO"]], on=["RUT", "ANO", "PERIODO"])
    notas = rendimiento.agregar_por_estudiante(r1)[["n_evaluaciones", "nota_promedio",
                                                     "pct_reprobadas", "pct_nota_minima"]]
    corte = r1.groupby("RUT")["FECHAFIN"].max().rename("fin_primer_periodo")
    lg = log_contactos.merge(corte, left_on="RUT_ALUMNO", right_index=True)
    lg = lg[lg["FECHA_COMUNICO"] < lg["fin_primer_periodo"]]
    cont = contactabilidad.agregar_por_estudiante(lg).drop(columns=["ultimo_contacto"])
    out = notas.add_prefix("p1_").join(cont.add_prefix("c1_"), how="left")
    out[["c1_n_contactos", "c1_n_contactos_personalizados"]] = out[
        ["c1_n_contactos", "c1_n_contactos_personalizados"]].fillna(0)
    return out


def cv_comparada(X_a, X_b, y, modelo_fn, folds=5) -> dict:
    """Validación cruzada con los mismos folds para comparar A contra B."""
    skf = StratifiedKFold(folds, shuffle=True, random_state=SEMILLA)
    pa, pb = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in skf.split(X_a, y):
        for X, p in ((X_a, pa), (X_b, pb)):
            num, cat = features.tipos(X)
            m = modelo_fn(num, cat).fit(X.iloc[tr], y.iloc[tr])
            p[te] = m.predict_proba(X.iloc[te])[:, 1]
    return {"A": metricas(y, pa), "B": metricas(y, pb)}


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------
def _corta(t: str, n: int = 78) -> str:
    """Acorta la pregunta y conserva la respuesta, que es lo que se interpreta."""
    if len(t) <= n:
        return t
    if " = " in t:
        q, a = t.rsplit(" = ", 1)
        q = q if len(q) <= n - len(a) - 4 else q[: max(10, n - len(a) - 5)].rstrip() + "…"
        return f"{q} = {a}"[: n + 25]
    return t[: n - 1] + "…"


def _figuras(curva, deciles, tasa_base, fact, comparacion_b):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": "#888888"})
    ROJO, GRIS, AZUL = "#B8433E", "#9AA3AE", "#4C78A8"
    FIGURES.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.plot(curva["pct_contactado"] * 100, curva["pct_desertores_capturados"] * 100, color=ROJO, lw=2,
            label="Con el modelo (orden por riesgo)")
    ax.plot([0, 100], [0, 100], color=GRIS, ls="--", lw=1.2, label="Sin modelo (orden al azar)")
    for k in (10, 20, 30):
        v = np.interp(k / 100, curva["pct_contactado"], curva["pct_desertores_capturados"]) * 100
        ax.scatter([k], [v], color=ROJO, zorder=3, s=18)
        ax.annotate(f"{v:.0f}%", (k, v), textcoords="offset points", xytext=(-6, 7), fontsize=8.5,
                    color=ROJO, fontweight="bold", ha="right")
    ax.set_xlabel("% de la cohorte 2026 contactada, de mayor a menor riesgo")
    ax.set_ylabel("% de desertores alcanzados")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.grid(color="#EEEEEE"); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Desertores alcanzados según cuántos estudiantes se contacten", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(FIGURES / "captura_desertores_2026.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.bar(deciles.index.astype(str), deciles.values * 100,
           color=[ROJO if i <= 2 else GRIS for i in deciles.index.astype(int)], width=0.65)
    ax.axhline(tasa_base * 100, color="#333333", ls="--", lw=1)
    ax.text(9.6, tasa_base * 100 + 1.5, f"Promedio {tasa_base*100:.0f}%", ha="right", fontsize=8.5)
    for x, v in enumerate(deciles.values * 100):
        ax.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_xlabel("Decil de riesgo (1 = 10% de mayor riesgo)")
    ax.set_ylabel("% que desertó")
    ax.set_title("Deserción real por decil de riesgo · cohorte 2026", loc="left", fontsize=10)
    ax.yaxis.grid(True, color="#EEEEEE"); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(FIGURES / "desercion_por_decil_2026.png"); plt.close(fig)

    r = pd.DataFrame(fact["riesgo"][:8]).iloc[::-1]
    p = pd.DataFrame(fact["protectores"][:8])
    fig, axs = plt.subplots(2, 1, figsize=(7.2, 6.0))
    for ax, d, col, tit in ((axs[0], r, ROJO, "Factores asociados a MÁS riesgo"),
                            (axs[1], p.iloc[::-1], AZUL, "Factores asociados a MENOS riesgo")):
        lab = [_corta(t) for t in d["factor"]]
        ax.barh(lab, d["odds_ratio"] - 1, left=1, color=col, height=0.6)
        ax.axvline(1, color="#333333", lw=0.8)
        ax.set_title(tit, loc="left", fontsize=9.5); ax.tick_params(axis="y", labelsize=7.5)
        ax.set_xlabel("Razón de odds (1 = sin efecto)", fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "factores_riesgo.png"); plt.close(fig)

    if comparacion_b:
        fig, ax = plt.subplots(figsize=(5.8, 3.2))
        lab = ["A · Solo encuesta\n(al ingreso)", "B · Encuesta + notas y\ncontactos del 1er periodo"]
        vals = [comparacion_b["A"]["recall_top20"] * 100, comparacion_b["B"]["recall_top20"] * 100]
        ax.bar(lab, vals, color=[GRIS, ROJO], width=0.5)
        for x, v in enumerate(vals):
            ax.text(x, v + 1.5, f"{v:.0f}%", ha="center", fontweight="bold")
        ax.set_ylim(0, 100); ax.set_ylabel("% de desertores alcanzados\nal contactar al 20% de mayor riesgo", fontsize=8)
        ax.set_title("Cuánto mejora la alerta con la conducta académica · cohorte 2024", loc="left", fontsize=9.5)
        fig.tight_layout(); fig.savefig(FIGURES / "modelo_a_vs_b_2024.png"); plt.close(fig)


# --------------------------------------------------------------------------
# Ejecución
# --------------------------------------------------------------------------
def ejecutar(raw=config.DATA_RAW, processed=config.DATA_PROCESSED, interim=config.DATA_INTERIM) -> dict:
    base = pd.read_pickle(processed / "base_objetivo.pkl")
    encuestas = {a: pd.read_excel(raw / f) for a, f in config.ARCHIVOS_ENCUESTA.items()}
    sel = features.seleccionar_variables()
    etq = features.etiquetas(sel)
    m = features.construir_matriz(encuestas, sel)
    m = m.sort_values("cohorte", kind="stable").drop_duplicates("token")
    # Atributos sensibles SOLO para auditar equidad (no entran al modelo)
    partes_sens = []
    for anio in sorted(encuestas):
        df = encuestas[anio].rename(columns=features.codigo)
        df = df.loc[:, ~df.columns.duplicated()]
        partes_sens.append(df.reindex(columns=["token", "G00Q02", "G01Q07"]))
    sens = pd.concat(partes_sens, ignore_index=True)
    sens["token"] = sens["token"].astype(str).str.strip().str.upper()
    sens = sens.drop_duplicates("token").set_index("token")

    datos = base.dropna(subset=["DESERCION"]).merge(m.drop(columns=["cohorte", "carrera", "jornada"]), on="token")
    y = datos["DESERCION"].astype(int)
    X = datos[[c for c in m.columns if c not in ("token", "cohorte")]]
    num, cat = features.tipos(X)
    log.info("Modelo A: %s estudiantes, %s predictores (%s numéricos, %s categóricos)",
             len(X), X.shape[1], len(num), len(cat))

    # Validación temporal: entrenar con 2024-2025, predecir la cohorte 2026
    tr, te = datos["cohorte"].isin([2024, 2025]).to_numpy(), (datos["cohorte"] == 2026).to_numpy()
    temporal, scores = {}, {}
    for nombre, mod in candidatos(num, cat).items():
        s = clone(mod).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        temporal[nombre], scores[nombre] = metricas(y[te], s), s
        log.info("  %-20s AUC %.3f | captura top20 %.0f%%", nombre, temporal[nombre]["roc_auc"],
                 100 * temporal[nombre]["recall_top20"])
    elegido = max(temporal, key=lambda k: temporal[k]["pr_auc"])
    s26 = scores[elegido]

    # Validación cruzada dentro de cada cohorte (controla el tiempo de exposición)
    cv = {}
    for coh in (2024, 2025, 2026):
        i = (datos["cohorte"] == coh).to_numpy()
        Xi, yi = X[i].reset_index(drop=True), y[i].reset_index(drop=True)
        oof = np.zeros(len(yi))
        for a, b in StratifiedKFold(5, shuffle=True, random_state=SEMILLA).split(Xi, yi):
            oof[b] = clone(candidatos(num, cat)[elegido]).fit(Xi.iloc[a], yi.iloc[a]).predict_proba(Xi.iloc[b])[:, 1]
        cv[str(coh)] = metricas(yi, oof)

    # Interpretación: regresión logística entrenada con las tres cohortes
    logit = clone(candidatos(num, cat)["Regresión logística"]).fit(X, y)
    fact = factores(logit, etq)

    # Equidad en la cohorte 2026 (atributos sensibles no usados por el modelo)
    d26 = datos[te].reset_index(drop=True)
    grupos = {"sexo": d26["token"].map(sens["G00Q02"]), "nacionalidad": d26["token"].map(sens["G01Q07"]),
              "jornada": d26["jornada"]}
    eq = {g: equidad(y[te], s26, v) for g, v in grupos.items()}

    # Modelo B: cohorte 2024 con notas y contactos del primer periodo
    comp_b = None
    try:
        cond = conducta_primer_periodo(pd.read_excel(raw / config.ARCHIVO_RENDIMIENTO),
                                       pd.read_pickle(interim / "contactabilidad_log_limpio.pkl"))
        d24 = datos[datos["cohorte"] == 2024].merge(cond, left_on="token", right_index=True)
        Xa = d24[X.columns].reset_index(drop=True)
        Xb = d24[list(X.columns) + list(cond.columns)].reset_index(drop=True)
        comp_b = cv_comparada(Xa, Xb, d24["DESERCION"].astype(int).reset_index(drop=True),
                              lambda n, c: candidatos(n, c)["Regresión logística"])
        log.info("  Modelo B 2024: captura top20 A %.0f%% -> B %.0f%%",
                 100 * comp_b["A"]["recall_top20"], 100 * comp_b["B"]["recall_top20"])
    except Exception as e:  # el modelo B es exploratorio: no debe impedir el resto
        log.warning("Modelo B no ejecutado: %s", e)

    deciles = tasa_por_decil(y[te], s26)
    _figuras(curva_captura(y[te], s26), deciles, y[te].mean(), fact, comp_b)

    # Lista priorizada (producto para el equipo de seguimiento). NO se versiona.
    lista = d26[["token", "carrera", "jornada"]].assign(prob_desercion=s26)
    lista["decil_riesgo"] = pd.qcut(lista["prob_desercion"].rank(method="first", ascending=False),
                                    10, labels=range(1, 11)).astype(int)
    lista.sort_values("prob_desercion", ascending=False).to_csv(processed / "lista_riesgo_2026.csv", index=False)
    try:
        import joblib
        MODELS.mkdir(exist_ok=True)
        joblib.dump({"modelo": logit if elegido == "Regresión logística" else
                     clone(candidatos(num, cat)[elegido]).fit(X, y), "predictores": list(X.columns)},
                    MODELS / "modelo_a.joblib")
    except Exception as e:
        log.warning("Modelo no guardado: %s", e)

    res = {
        "fecha": date.today().isoformat(), "version": "0.4.0-preliminar",
        "etiqueta": "DESERCION (ELIMINADO o SUSPENDIDO)", "supuesto_fecha_corte": str(config.FECHA_CORTE.date()),
        "predictores": {"n": int(X.shape[1]), "numericos": len(num), "categoricos": len(cat),
                        "variables_diccionario": int(len(sel))},
        "validacion_temporal": {"entrenamiento": "cohortes 2024-2025", "prueba": "cohorte 2026",
                                "n_entrenamiento": int(tr.sum()), "modelos": temporal, "elegido": elegido,
                                "ic95_elegido": intervalos(y[te], s26)},
        "desercion_por_decil_2026": {str(k): float(v) for k, v in deciles.items()},
        "cv_dentro_de_cohorte": cv, "factores": fact, "equidad_2026": eq, "modelo_b_2024": comp_b,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "resultados_modelo.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float))
    return res


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    r = ejecutar()
    t = r["validacion_temporal"]
    print(f"\nModelo elegido: {t['elegido']}")
    print(pd.DataFrame(t["modelos"]).T.round(3).to_string())


if __name__ == "__main__":
    main()
