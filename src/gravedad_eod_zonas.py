"""Gravitacional PPML por zona EOD 2023 (AMG). Primera pasada exploratoria.

Entradas en EOD_DATA_DIR (por defecto data/raw/); salidas en EOD_OUT_DIR (por defecto salida/). Ver data/README.md.
"""
import os, numpy as np, pandas as pd, geopandas as gpd, statsmodels.api as sm, warnings
warnings.filterwarnings("ignore")
U = os.environ.get("EOD_DATA_DIR", "data/raw/"); OUT = os.environ.get("EOD_OUT_DIR", "salida/")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)

# ---------- datos ----------
z = gpd.read_parquet(U + "AMG_Zonificacion_para_encuesta.parquet")
z = z[~z.ID_ZONAEOD.str.startswith("9999")].reset_index(drop=True)          # 64 zonas internas
ids = list(z.ID_ZONAEOD); k = len(ids); ix = {a: i for i, a in enumerate(ids)}
cen = np.c_[z.geometry.centroid.x, z.geometry.centroid.y]
D = np.hypot(cen[:, None, 0] - cen[None, :, 0], cen[:, None, 1] - cen[None, :, 1]) / 1000.0   # km
r = np.sqrt(z.area.values / np.pi) / 1000.0
D[np.diag_indices(k)] = (2 / 3) * r                                           # distancia intrazonal

m = gpd.read_parquet(U + "AMG_MicroZONAS2023.parquet")
m["zid"] = m.ZONAEOD202.astype(str).str.replace("+", "", regex=False).str.replace("*", "", regex=False)
m = m[m.zid.isin(ids)]
att = m.groupby("zid")[["POBTOT", "POCUPADA", "EMP_IND_CO", "EMP_SERVIC", "EMP_OTROS"]].sum().reindex(ids).fillna(0)
att["EMP"] = att.EMP_IND_CO + att.EMP_SERVIC + att.EMP_OTROS

t = pd.read_csv(U + "IMEPLAN_Base_Viajes_Master.csv", encoding="latin-1", low_memory=False,
                usecols=["Folio Vivienda", "Zona origen", "Zona Destino", "Motivo de su viaje", "Ponderador"],
                dtype={"Zona origen": str, "Zona Destino": str})
t = t.rename(columns={"Folio Vivienda": "viv", "Zona origen": "zo", "Zona Destino": "zd", "Motivo de su viaje": "motivo", "Ponderador": "w"})
n0 = len(t); t = t[t.zo.isin(ids) & t.zd.isin(ids)].copy()
print(f"viajes {n0} -> {len(t)} tras excluir zonas externas ({100*(1-len(t)/n0):.1f}%)")
t["prop"] = np.select([t.motivo == "Regresar a Casa", t.motivo == "Trabajar", t.motivo == "Estudiar"],
                      ["retorno", "trabajo", "estudio"], "otros")
t["o"] = t.zo.map(ix); t["d"] = t.zd.map(ix)
print(t.groupby("prop").agg(n=("w", "size"), w=("w", "sum")).assign(pct=lambda d: 100 * d.w / d.w.sum()).round(1))

def od(df):
    M = np.zeros((k, k)); np.add.at(M, (df.o.values, df.d.values), df.w.values); return M

def cpc(a, b, mask=None):
    if mask is not None: a, b = a[mask], b[mask]
    return 2 * np.minimum(a, b).sum() / (a.sum() + b.sum())

OO, DD = np.meshgrid(range(k), range(k), indexing="ij"); OO, DD = OO.ravel(), DD.ravel()
off = np.eye(k, dtype=bool).ravel() == False
def dummies(idx, drop_first):
    X = np.zeros((len(idx), k)); X[np.arange(len(idx)), idx] = 1
    return X[:, 1:] if drop_first else X
FEo = dummies(OO, False); FEd = dummies(DD, True)
dist = D.ravel(); ld = np.log(dist)

def design(spec):
    base = {"potencia": [ld], "exponencial": [dist], "combinada": [ld, dist]}[spec]
    return np.column_stack(base), len(base)

def fit_fe(T, spec):
    """Origen y destino con efectos fijos: estima la funcion de impedancia sin atractores."""
    Z, nz = design(spec); X = np.column_stack([Z, FEo, FEd])
    res = sm.GLM(T.ravel(), X, family=sm.families.Poisson()).fit(maxiter=200, tol=1e-8)
    return res, res.params[:nz], np.asarray(res.mu).reshape(k, k)

def fit_att(T, A, spec, logs):
    """Restringido en produccion: FE de origen + atractores (elasticidades libres) + impedancia."""
    Z, nz = design(spec); L = np.column_stack([np.log(np.maximum(A[c].values, 1))[DD] for c in logs])
    X = np.column_stack([Z, L, FEo])
    res = sm.GLM(T.ravel(), X, family=sm.families.Poisson()).fit(maxiter=200, tol=1e-8)
    return res, res.params[:nz + len(logs)], np.asarray(res.mu).reshape(k, k)

def dev_explained(T, mu):
    y = T.ravel(); mu = mu.ravel(); ll = lambda m_: np.sum(np.where(y > 0, y * np.log(np.maximum(m_, 1e-12) / np.where(y > 0, y, 1)), 0) - (m_ - y))
    return 1 - (-2 * ll(mu)) / (-2 * ll(np.full_like(mu, y.mean())))

rows = []; preds = {}
props = {"trabajo": ["EMP", "POCUPADA"], "estudio": ["POBTOT"], "otros": ["EMP", "POBTOT"]}
for p in ["trabajo", "estudio", "otros"]:
    T = od(t[t.prop == p]); tot = T.sum()
    for spec in ["potencia", "exponencial", "combinada"]:
        res, b, mu = fit_fe(T, spec)
        rows.append(dict(proposito=p, modelo="FE origen+destino", impedancia=spec, params=np.round(b, 4).tolist(),
                         CPC=cpc(T, mu), CPC_sin_diag=cpc(T, mu, off.reshape(k, k)), dev_expl=dev_explained(T, mu)))
        preds[(p, "FE", spec)] = mu
    for spec in ["potencia", "combinada"]:
        res, b, mu = fit_att(T, att, spec, props[p])
        rows.append(dict(proposito=p, modelo="Restringido produccion + atractores", impedancia=spec, params=np.round(b, 4).tolist(),
                         CPC=cpc(T, mu), CPC_sin_diag=cpc(T, mu, off.reshape(k, k)), dev_expl=dev_explained(T, mu)))
        preds[(p, "ATT", spec)] = mu
R = pd.DataFrame(rows); pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60)
print("\n=== AJUSTE EN MUESTRA ==="); print(R.round(3).to_string(index=False))
R.to_csv(OUT + "resultados_ajuste.csv", index=False)

# ---------- techo de ruido y validacion split-half por vivienda ----------
vivs = t.viv.unique(); S = []
for rep in range(30):
    half = set(rng.choice(vivs, len(vivs) // 2, replace=False))
    a = t[t.viv.isin(half)]; b = t[~t.viv.isin(half)]
    for p in ["trabajo", "estudio", "otros"]:
        TA, TB = od(a[a.prop == p]), od(b[b.prop == p]); TB = TB * TA.sum() / TB.sum()
        row = dict(rep=rep, proposito=p, techo=cpc(TA, TB))
        _, _, mu = fit_fe(TA, "potencia"); row["FE_potencia"] = cpc(TB, mu)
        _, _, mu = fit_att(TA, att, "potencia", props[p]); row["ATT_potencia"] = cpc(TB, mu)
        _, _, mu = fit_att(TA, att, "combinada", props[p]); row["ATT_combinada"] = cpc(TB, mu)
        S.append(row)
S = pd.DataFrame(S); sm_ = S.groupby("proposito")[["techo", "FE_potencia", "ATT_potencia", "ATT_combinada"]].agg(["mean", "std"]).round(3)
print("\n=== FUERA DE MUESTRA (entrena en mitad de viviendas, evalua en la otra mitad; 30 repeticiones) ==="); print(sm_.to_string())
S.to_csv(OUT + "validacion_split_half.csv", index=False)

# ---------- bootstrap por vivienda del parametro de impedancia (modelo FE, potencia) ----------
B = []
for rep in range(40):
    s = rng.choice(vivs, len(vivs), replace=True); cnt = pd.Series(s).value_counts()
    bb = t[t.viv.isin(cnt.index)].copy(); bb["w"] = bb.w * bb.viv.map(cnt)
    for p in ["trabajo", "estudio", "otros"]:
        _, b, _ = fit_fe(od(bb[bb.prop == p]), "potencia"); B.append(dict(proposito=p, beta_ldist=b[0]))
B = pd.DataFrame(B); bs = B.groupby("proposito").beta_ldist.agg(media="mean", p2_5=lambda x: x.quantile(.025), p97_5=lambda x: x.quantile(.975)).round(3)
print("\n=== Exponente de distancia (potencia, FE), bootstrap por vivienda, 40 reps ==="); print(bs.to_string())
B.to_csv(OUT + "bootstrap_beta.csv", index=False); bs.to_csv(OUT + "beta_intervalos.csv")

