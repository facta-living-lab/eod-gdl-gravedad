"""Cartografia de respaldo del gravitacional por zona EOD 2023 (AMG).

Reutiliza la carga de datos y las funciones de ajuste de gravedad_eod_zonas.py (todo lo que va antes de la
seccion de ajuste). Variables de entorno: EOD_DATA_DIR (entradas, por defecto data/raw/) y EOD_OUT_DIR (salidas, por defecto salida/).
Salidas: mapa_1..mapa_6 (PNG), figura_ajuste.png y zonas_resultados.gpkg (capa para QGIS).
"""
import os, io, contextlib
MODELO = os.environ.get("MODELO_PY", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gravedad_eod_zonas.py"))
src = open(MODELO).read().split("rows = []; preds = {}")[0]
exec(src)                                    # define z, ids, k, D, att, t, od, cpc, fit_fe, fit_att, props, U, OUT

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.colors as mcolors
from matplotlib.collections import LineCollection

PROPS = {"trabajo": ["EMP", "POCUPADA"], "estudio": ["POBTOT"], "otros": ["EMP", "POBTOT"]}
zall = gpd.read_parquet(U + "AMG_Zonificacion_para_encuesta.parquet")
gates = zall[zall.ID_ZONAEOD.str.startswith("9999")]
xmin, ymin, xmax, ymax = zall.total_bounds
area_km2 = z.area.values / 1e6

# ---------- matrices observadas y modeladas ----------
Tobs, Mat, Mfe = {}, {}, {}
for p in PROPS:
    Tobs[p] = od(t[t.prop == p])
    Mfe[p] = fit_fe(Tobs[p], "potencia")[2]
    Mat[p] = fit_att(Tobs[p], att, "potencia", PROPS[p])[2]

# ---------- metricas por zona ----------
Z = z[["ID_ZONAEOD", "geometry"]].copy(); Z["area_km2"] = area_km2
mod = t[t.prop != "retorno"]
Z["n_reg_origen"] = np.bincount(mod.o, minlength=k); Z["n_reg_destino"] = np.bincount(mod.d, minlength=k)
for c in ["POBTOT", "POCUPADA", "EMP"]: Z[c] = att[c].values
Z["emp_por_ocupado"] = np.where(Z.POCUPADA > 0, Z.EMP / Z.POCUPADA.replace(0, np.nan), np.nan)
for p in PROPS:
    T, M = Tobs[p], Mat[p]
    Z[f"prod_{p}"] = T.sum(1); Z[f"atr_obs_{p}"] = T.sum(0); Z[f"atr_mod_{p}"] = M.sum(0)
    Z[f"lnres_{p}"] = np.where((T.sum(0) > 0) & (M.sum(0) > 0), np.log(M.sum(0) / np.where(T.sum(0) > 0, T.sum(0), 1)), np.nan)
    Z[f"intra_{p}"] = np.diag(T) / np.where(T.sum(1) > 0, T.sum(1), np.nan)

# ---------- Moran I de los residuos (k=5 vecinos mas cercanos, 999 permutaciones) ----------
cen = np.c_[z.geometry.centroid.x, z.geometry.centroid.y]
dd = np.hypot(cen[:, None, 0] - cen[None, :, 0], cen[:, None, 1] - cen[None, :, 1]); np.fill_diagonal(dd, np.inf)
W = np.zeros((k, k)); 
for i in range(k): W[i, np.argsort(dd[i])[:5]] = 1
W /= W.sum(1, keepdims=True)
def moran(x, rng_):
    ok = np.isfinite(x); idx = np.where(ok)[0]; Wk = W[np.ix_(idx, idx)]; Wk = Wk / Wk.sum(1, keepdims=True)
    v = x[idx] - x[idx].mean(); I = (v @ Wk @ v) / (v @ v)
    sim = [(lambda q: (q @ Wk @ q) / (q @ q))(rng_.permutation(v)) for _ in range(999)]
    return I, (1 + np.sum(np.array(sim) >= I)) / 1000, len(idx)
rg = np.random.default_rng(7); MOR = {p: moran(Z[f"lnres_{p}"].values, rg) for p in PROPS}
print("\nMoran I de residuos de atraccion (ln modelo/obs):")
for p, (I, pv, n) in MOR.items(): print(f"  {p}: I={I:.3f}  p(pseudo)={pv:.3f}  n={n}")

# ---------- utilidades cartograficas ----------
BG = "#f4f1ea"
def base(ax, labels=False):
    zall.plot(ax=ax, color="#e7e3da", edgecolor="white", linewidth=.35)
    gates.plot(ax=ax, color="none", edgecolor="#555", linewidth=.8, hatch="////")
    ax.set_xlim(xmin - 3e3, xmax + 3e3); ax.set_ylim(ymin - 3e3, ymax + 3e3); ax.set_aspect("equal"); ax.axis("off")
    x0, y0 = xmin, ymin - 1e3
    ax.plot([x0, x0 + 10e3], [y0, y0], color="k", lw=2.2); ax.text(x0 + 5e3, y0 - 2.6e3, "10 km", ha="center", fontsize=7)
    ax.annotate("N", xy=(xmax - 2e3, ymax + 2e3), xytext=(xmax - 2e3, ymax - 6e3), ha="center", fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2))
def qbins(x, q=5):
    return np.unique(np.quantile(x[np.isfinite(x)], np.linspace(0, 1, q + 1)))
def choro(ax, col, cmap, bins, ttl, fmt="{:,.0f}", extend=False, cbar=True):
    cm = plt.get_cmap(cmap); norm = mcolors.BoundaryNorm(bins, cm.N, extend="both" if extend else "neither")
    base(ax); Z.plot(column=col, cmap=cm, norm=norm, ax=ax, edgecolor="#8f8a7e", linewidth=.25,
                     missing_kwds=dict(color="#c9c4b8", hatch="..", edgecolor="white"))
    if cbar:
        cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cm), ax=ax, shrink=.62, pad=.01, fraction=.04, ticks=bins)
        cb.ax.set_yticklabels([fmt.format(v) for v in bins], fontsize=7)
    ax.set_title(ttl, fontsize=9.5, loc="left"); return cm, norm
def cbar_comun(fig, axes, cm, norm, bins, fmt, etiqueta):
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cm), ax=list(axes), orientation="horizontal", shrink=.42, pad=.03, aspect=40, ticks=bins)
    cb.ax.set_xticklabels([fmt.format(v) for v in bins], fontsize=7.5); cb.set_label(etiqueta, fontsize=8)
def pie(fig, nota):
    fig.text(.01, .008, nota, fontsize=6.8, color="#444", ha="left", va="bottom", wrap=True)
def guardar(fig, nombre):
    fig.patch.set_facecolor(BG); fig.savefig(OUT + nombre, dpi=170, facecolor=BG, bbox_inches="tight"); plt.close(fig)
FUENTE = "Fuente: IMEPLAN, EOD 2023 (viajes ponderados, lunes a viernes); zonificacion EOD 2023; microzonas 2023. Proyeccion UTM 13N. " \
         "Achurado: accesos externos excluidos (2.0% de los viajes)."

# ===== Mapa 1: soporte muestral =====
fig, ax = plt.subplots(1, 2, figsize=(13, 6.6))
b = qbins(np.r_[Z.n_reg_origen, Z.n_reg_destino], 5)
choro(ax[0], "n_reg_origen", "YlGnBu", b, "Registros de viaje por zona de ORIGEN (sin ponderar)")
choro(ax[1], "n_reg_destino", "YlGnBu", b, "Registros de viaje por zona de DESTINO (sin ponderar)")
fig.suptitle("Mapa 1. Soporte muestral: cuantos viajes observados sostienen cada zona", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE + f"  Se cuentan solo viajes modelados (trabajo, estudio, otros): {len(mod):,}. Clases por cuantiles comunes a ambos paneles.")
guardar(fig, "mapa_1_soporte_muestral.png")

# ===== Mapa 2: produccion y atraccion de trabajo (densidad) =====
fig, ax = plt.subplots(1, 2, figsize=(13, 6.6))
dp = Z.prod_trabajo / Z.area_km2; da = Z.atr_obs_trabajo / Z.area_km2; Z["dens_prod_trabajo"] = dp; Z["dens_atr_trabajo"] = da
b = qbins(np.r_[dp, da], 5)
choro(ax[0], "dens_prod_trabajo", "YlOrRd", b, "Viajes de trabajo PRODUCIDOS (viajes/dia por km2)")
choro(ax[1], "dens_atr_trabajo", "YlOrRd", b, "Viajes de trabajo ATRAIDOS (viajes/dia por km2)")
fig.suptitle("Mapa 2. Patron observado que el modelo debe reproducir (trabajo)", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE + f"  Total ponderado: {Tobs['trabajo'].sum():,.0f} viajes/dia. Se muestra densidad (no totales) porque las zonas varian de 1 a 37 km2.")
guardar(fig, "mapa_2_produccion_atraccion_trabajo.png")

# ===== Mapa 3: residuos de atraccion del modelo con atractores =====
fig, ax = plt.subplots(1, 3, figsize=(16, 6.6)); bins = np.array([-1.5, -1, -.5, -.2, .2, .5, 1, 1.5])
for a, p in zip(ax, PROPS):
    cm, norm = choro(a, f"lnres_{p}", "RdBu_r", bins, f"{p.capitalize()}: atraccion modelada frente a observada", extend=True, cbar=False)
    I, pv, n = MOR[p]; c_ = cpc(Tobs[p], Mat[p]); cs = cpc(Tobs[p], Mat[p], ~np.eye(k, dtype=bool))
    a.text(.01, .985, f"CPC {c_:.2f} (sin diagonal {cs:.2f})\nMoran I {I:+.2f}, p = {pv:.2f}", transform=a.transAxes, fontsize=8, va="top",
           bbox=dict(fc="white", ec="#999", alpha=.9, pad=3))
cbar_comun(fig, ax, cm, norm, bins, "{:+.1f}", "ln(modelo / observado):  rojo = el modelo sobreestima,  azul = subestima   (+0.69 = el doble, -0.69 = la mitad)")
fig.suptitle("Mapa 3. Donde falla el modelo con atractores: residuos de atraccion por zona", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE + "  Gris con puntos: zona sin viajes observados o modelados. Moran I: 5 vecinos mas cercanos, 999 permutaciones.")
guardar(fig, "mapa_3_residuos_atraccion.png")

# ===== Mapa 4: lineas de deseo, trabajo, observado vs modelo =====
def lineas(ax, M, n, ttl, vmax):
    o = ~np.eye(k, dtype=bool); flat = np.where(o, M, 0).ravel(); top = np.argsort(flat)[::-1][:n]
    i_, j_ = np.divmod(top, k); seg = [[cen[a], cen[b]] for a, b in zip(i_, j_)]; v = flat[top]
    base(ax); lc = LineCollection(seg, linewidths=0.4 + 5.0 * (v / vmax), colors=plt.cm.magma_r(.25 + .7 * v / vmax), alpha=.75, capstyle="round")
    ax.add_collection(lc); ax.set_title(ttl, fontsize=9.5, loc="left"); return set(top.tolist()), v
N = 120; offd = ~np.eye(k, dtype=bool)
vmax = max(np.where(offd, Tobs["trabajo"], 0).max(), np.where(offd, Mat["trabajo"], 0).max())
fig, ax = plt.subplots(1, 2, figsize=(13, 6.4))
s1, v1 = lineas(ax[0], Tobs["trabajo"], N, f"OBSERVADO: {N} mayores flujos interzonales de trabajo", vmax)
s2, v2 = lineas(ax[1], Mat["trabajo"], N, f"MODELO (atractores): {N} mayores flujos interzonales", vmax)
ov = len(s1 & s2) / N
from matplotlib.lines import Line2D
refs = [vmax * f for f in (.1, .4, 1.0)]
ax[1].legend(handles=[Line2D([0], [0], color=plt.cm.magma_r(.25 + .7 * r_ / vmax), lw=.4 + 5 * r_ / vmax, label=f"{r_:,.0f} viajes/dia") for r_ in refs],
             loc="lower right", fontsize=7.5, frameon=True, framealpha=.9, title="Escala comun", title_fontsize=7.5)
fig.suptitle("Mapa 4. Lineas de deseo de trabajo: observado contra modelo", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE + f"  Grosor y color proporcionales al flujo, con la misma escala en ambos paneles. {100*ov:.0f}% de los {N} pares principales coincide. Sin flujos intrazonales.")
guardar(fig, "mapa_4_lineas_deseo_trabajo.png")
print(f"\nCoincidencia top-{N} pares trabajo observado vs modelo: {100*ov:.0f}%")
# pares observados grandes que el modelo no reproduce (para el texto)
flat_o = np.where(offd, Tobs["trabajo"], 0).ravel(); flat_m = np.where(offd, Mat["trabajo"], 0).ravel()
gap = pd.DataFrame({"o": [ids[i] for i in np.divmod(np.arange(k*k), k)[0]], "d": [ids[j] for j in np.divmod(np.arange(k*k), k)[1]],
                    "obs": flat_o, "mod": flat_m, "km": dist})
gap["ratio"] = gap.obs / np.maximum(gap["mod"], 1)
print(gap.sort_values("obs", ascending=False).head(12).round(1).to_string(index=False))
print("pares top-120 observados con ratio obs/mod > 3:"); print(gap.sort_values("obs", ascending=False).head(N).query("ratio>3").round(1).to_string(index=False))

# ===== Mapa 5: intrazonalidad =====
fig, ax = plt.subplots(1, 3, figsize=(16, 6.6)); b = np.array([0, .2, .4, .6, .8, 1.0])
for a, p in zip(ax, PROPS):
    cm, norm = choro(a, f"intra_{p}", "Purples", b, f"{p.capitalize()}", fmt="{:.0%}", cbar=False)
    a.text(.01, .985, f"{100*np.trace(Tobs[p])/Tobs[p].sum():.0f}% del total ponderado es intrazonal", transform=a.transAxes, fontsize=8, va="top",
           bbox=dict(fc="white", ec="#999", alpha=.9, pad=3))
cbar_comun(fig, ax, cm, norm, b, "{:.0%}", "% de los viajes producidos en la zona que no salen de ella")
fig.suptitle("Mapa 5. Por que el CPC se infla: proporcion de viajes en la diagonal de la matriz", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE)
guardar(fig, "mapa_5_intrazonalidad.png")

# ===== Mapa 6: cobertura de los atractores de empleo =====
fig, ax = plt.subplots(1, 2, figsize=(13, 6.6)); Z["emp_dens"] = Z.EMP / Z.area_km2
choro(ax[0], "emp_dens", "BuGn", qbins(Z.emp_dens.values, 5), "Empleo en microzonas (EMP_*), empleos por km2")
choro(ax[1], "emp_por_ocupado", "PuOr", np.array([0, .25, .5, .75, 1, 1.5, 3, 10]), "Empleo registrado / residentes ocupados (censo)", fmt="{:.2f}", extend=True)
fig.suptitle("Mapa 6. Atractor de empleo: ubicacion y cobertura frente a los ocupados del censo", x=.01, ha="left", fontsize=12, fontweight="bold")
pie(fig, FUENTE + f"  Total EMP: {Z.EMP.sum():,.0f}; ocupados (censo): {Z.POCUPADA.sum():,.0f}. Razon <1 = menos empleo registrado que residentes ocupados (informalidad, "
         "subregistro o zona dormitorio); >1 = polo de empleo.")
guardar(fig, "mapa_6_cobertura_atractor_empleo.png")

# ===== Figura de ajuste (observado vs estimado, distribucion por distancia) =====
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
for a, p in zip(ax[:2], ["trabajo", "otros"]):
    T = Tobs[p]; o = ~np.eye(k, dtype=bool); y = T[o]; s = y > 0
    a.scatter(Mfe[p][o][s], y[s], s=4, alpha=.25, label=f"FE origen+destino (CPC {cpc(T, Mfe[p]):.2f})")
    a.scatter(Mat[p][o][s], y[s], s=4, alpha=.25, label=f"Atractores (CPC {cpc(T, Mat[p]):.2f})")
    lim = [y[s].min(), y[s].max()]; a.plot(lim, lim, "k--", lw=1); a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("Viajes estimados"); a.set_ylabel("Viajes observados (ponderados)"); a.set_title(f"Pares interzonales con flujo observado, {p}")
    a.legend(fontsize=7, markerscale=3)
bins_d = np.array([0, 2, 4, 6, 8, 11, 15, 20, 30, 60]); lab = [f"{bins_d[i]}-{bins_d[i+1]}" for i in range(len(bins_d) - 1)]
for p, c in zip(PROPS, ["C0", "C1", "C2"]):
    T, mu = Tobs[p], Mfe[p]
    ob = [T.ravel()[(dist >= bins_d[i]) & (dist < bins_d[i+1])].sum() / T.sum() for i in range(len(lab))]
    mo = [mu.ravel()[(dist >= bins_d[i]) & (dist < bins_d[i+1])].sum() / mu.sum() for i in range(len(lab))]
    ax[2].plot(lab, ob, "o-", c=c, label=f"{p} obs."); ax[2].plot(lab, mo, "x--", c=c, label=f"{p} modelo FE")
ax[2].set_xlabel("Distancia entre centroides (km)"); ax[2].set_ylabel("Proporcion de viajes"); ax[2].tick_params(axis="x", rotation=45)
ax[2].set_title("Distribucion por distancia"); ax[2].legend(fontsize=7, ncol=2)
plt.tight_layout(); fig.savefig(OUT + "figura_ajuste.png", dpi=140); plt.close(fig)

# ===== Capa SIG =====
Zout = Z.drop(columns=["dens_prod_trabajo", "dens_atr_trabajo", "emp_dens"]).copy()
Zout.to_file(OUT + "zonas_resultados.gpkg", layer="zonas", driver="GPKG")
Zout.drop(columns="geometry").to_csv(OUT + "zonas_resultados.csv", index=False)
print("\nlisto: 6 mapas, figura_ajuste.png, zonas_resultados.gpkg/.csv")
