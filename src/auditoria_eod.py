"""Auditoria de consistencia de la EOD 2023 (AMG).

Compara la base de viajes con lo que IMEPLAN publica (informe tecnico y visualizador) y revisa su consistencia interna.
Entradas (en EOD_DATA_DIR, por defecto data/raw/):
  IMEPLAN_Base_Viajes_Master.csv, RELACION_AGEBS-ZONA_con_datos_censales.parquet
Salidas (en EOD_OUT_DIR, por defecto salida/): auditoria_*.csv
Las cifras del tablero se capturaron a mano del visualizador (Power BI) el 2026-10-10; son constantes de este archivo.
Una inconsistencia no es prueba de intencion: solo senala algo que conviene aclarar.
"""
import os
import numpy as np
import pandas as pd

DATA = os.environ.get("EOD_DATA_DIR", "data/raw/"); OUT = os.environ.get("EOD_OUT_DIR", "salida/")
os.makedirs(OUT, exist_ok=True)
t = pd.read_csv(DATA + "IMEPLAN_Base_Viajes_Master.csv", encoding="latin-1", low_memory=False,
                dtype={"Origen": str, "Destino": str, "Zona origen": str, "Zona Destino": str})
w = t["Ponderador"]; W = w.sum()
rows = []
def add(grupo, indicador, tablero, base):
    rows.append(dict(grupo=grupo, indicador=indicador, tablero=tablero, base=round(float(base), 2) if base is not None else None,
                     diferencia=None if tablero is None or base is None else round(float(base) - float(tablero), 2)))

# ---- 1. Reproduccion de las cifras del visualizador ----
add("total", "viajes diarios", 11796386, W)
m = t["Medio del viaje"]; g = w.groupby(m).sum() / W * 100
pub = g[["Línea 1 Sitren", "Línea 2 Sitren", "Línea 3 Sitren", "Servicio suburbano"]].sum()
modos = {"a pie (%)": (43.2, g["A PIE"]),
         "transporte particular (%)": (28.1, g["AUTOMÓVIL PARTICULAR"] + g["MOTOCICLETA"]),
         "transporte publico (%)": (21.6, g["CAMIÓN O AUTOBÚS"] + g["TREN LIGERO"] + g["MI MACRO"] + pub),
         "transporte especial (%)": (2.4, g["Transporte de personal"] + g["Transporte escolar"] + g["Transporte escolar particular"]),
         "taxi (%)": (2.1, g["Taxi"] + g["Taxi plataforma (Uber/Didi)"]),
         "bicicleta (%)": (1.9, g["Bicicleta"] + g["Mi Bici"])}
for k_, (tab, b) in modos.items(): add("modo", k_, tab, b)
mo = t["Motivo de su viaje"]; gm = w.groupby(mo).sum() / W * 100
add("motivo", "trabajo (%)", 18.2, gm["Trabajar"]); add("motivo", "estudio (%)", 6.9, gm["Estudiar"])
add("motivo", "hogar = compras + tramite + pago (%)", 14.8,
    gm[["Compras (comida)", "Compras (bienes, productos y servicios)", "Hacer un trámite", "Pagar algún servicio o al banco"]].sum())
add("motivo", "cuidados = llevar/recoger + medico + guarderia (%)", 5.1, gm[["Llevar o recoger a alguien", "Al médico o atención de salud", "Guardería"]].sum())
add("motivo", "regreso a casa (%)", 48.5, gm["Regresar a Casa"])
ge = w.groupby(t["Grupo de Edad"]).sum() / W * 100
for k_, tab in {"6-11": 8.5, "12-17": 9.9, "18-34": 30.3, "35-54": 32.1, "55 y +": 19.2}.items(): add("edad", f"{k_} (%)", tab, ge[k_])
add("sexo", "hombres (%)", 48.0, w[t["Sexo de nacimiento"].str.startswith("Hombre")].sum() / W * 100)
add("viaje interno", "misma zona de origen y destino (%)", 52.0, w[t["Zona origen"] == t["Zona Destino"]].sum() / W * 100)
mins = t[[f"Traslados que utilizó para su viaje: | Traslado {i} | Minutos" for i in range(1, 6)]].sum(axis=1)
lab = ["<6", "6-10", "11-15", "16-30", "31-45", "46-60", "61-90", "91-120", "121+"]
b = pd.cut(mins, bins=[-1, 5, 10, 15, 30, 45, 60, 90, 120, 10**6], labels=lab)
gd = w.groupby(b, observed=False).sum() / W * 100
for l, tab in zip(lab, [15.4, 19.7, 17.4, 21.0, 11.6, 7.9, 4.8, 1.9, 0.3]): add("duracion (suma de traslados)", f"{l} min (%)", tab, gd[l])
add("duracion", "promedio (min)", 26, (mins * w).sum() / W)
# totales por zona (valores leidos del visualizador, pagina Lineas de deseo)
orig = {"Las Águilas - Miramar": 537239, "Centro Tlaquepaque": 513979, "Parque Solidaridad - Tetlán": 497485, "Huentitán": 478964,
        "Oblatos": 452403, "Santa Fe - Chulavista": 451766, "Miravalle": 448820, "Centro Sur - Balcones de Santa María": 428867,
        "San Martín de las Flores - Las Huertas": 375484, "San Juan de Dios": 359395, "Centro Tonalá": 331116,
        "Constitución - Auditorio": 315510, "La Estancia - Chapalita": 310865, "Expo - Chapalita": 295107}
dest = {"Centro Guadalajara": 758298, "Centro Zapopan": 577381, "Las Águilas - Miramar": 539250, "Centro Tlaquepaque": 508853,
        "Parque Solidaridad - Tetlán": 497665, "Huentitán": 478522, "Santa Fe - Chulavista": 456136, "Oblatos": 454300,
        "Miravalle": 453211, "Centro Sur - Balcones de Santa María": 429191, "San Martín de las Flores - Las Huertas": 378106,
        "San Juan de Dios": 359220, "Centro Tonalá": 332466, "Constitución - Auditorio": 315448, "La Estancia - Chapalita": 308386,
        "Expo - Chapalita": 294930}
zo = w.groupby(t["Zona origen"]).sum(); zd = w.groupby(t["Zona Destino"]).sum()
mapa_o, mapa_d, zrows = {}, {}, []
for nom, v in orig.items():
    ids_ = zo.index[zo == v].tolist(); mapa_o[nom] = ids_[0] if ids_ else None
    zrows.append(dict(lista="origen", nombre_zona=nom, valor_tablero=v, id_zona_en_base=mapa_o[nom], existe_exacto=bool(ids_)))
for nom, v in dest.items():
    ids_ = zd.index[zd == v].tolist(); mapa_d[nom] = ids_[0] if ids_ else None
    zrows.append(dict(lista="destino", nombre_zona=nom, valor_tablero=v, id_zona_en_base=mapa_d[nom], existe_exacto=bool(ids_)))
Z = pd.DataFrame(zrows); Z.to_csv(OUT + "auditoria_totales_por_zona.csv", index=False)
cons = [(n, mapa_o[n], mapa_d[n]) for n in orig if n in dest and mapa_o[n] and mapa_d[n]]
print(f"Totales por zona: {Z.existe_exacto.sum()} de {len(Z)} valores del tablero existen exactos en la base; "
      f"nombre -> mismo ID en origen y destino: {sum(a == b for _, a, b in cons)} de {len(cons)}")
pd.DataFrame(rows).to_csv(OUT + "auditoria_reproduccion_tablero.csv", index=False)

# ---- 2. Zona de la encuesta frente a la tabla AGEB-zona ----
r = pd.read_parquet(DATA + "RELACION_AGEBS-ZONA_con_datos_censales.parquet")
mz = dict(zip(r.CVEGEO_EOD.astype(str), r["EOD2023"].astype(str))); res = []
for ag, zn, lado in [("Origen", "Zona origen", "origen"), ("Destino", "Zona Destino", "destino")]:
    zc = t[ag].map(mz); dis = (zc != t[zn]) | zc.isna()
    d = pd.DataFrame({"clave_ageb": t.loc[dis, ag], "zona_encuesta": t.loc[dis, zn], "zona_tabla_censal": zc[dis], "ponderados": w[dis], "lado": lado})
    res.append(d)
C = pd.concat(res); C["zona_tabla_censal"] = C["zona_tabla_censal"].fillna("sin fila en la tabla")
C = C.groupby(["clave_ageb", "zona_encuesta", "zona_tabla_censal", "lado"]).agg(registros=("ponderados", "size"), ponderados=("ponderados", "sum")).reset_index()
C["tipo"] = np.select([C.zona_tabla_censal == "sin fila en la tabla", C.zona_tabla_censal == "NA"],
                      ["AGEB sin fila en la tabla censal", "zona NA (sin asignar) en la tabla censal"], "zona distinta")
C.sort_values("ponderados", ascending=False).to_csv(OUT + "auditoria_zonas_ageb_conflictos.csv", index=False)
dist = C[C.tipo == "zona distinta"]
print(f"AGEB con otra zona asignada en la tabla censal: {dist.clave_ageb.nunique()} | viajes ponderados (origen): {100*dist[dist.lado=='origen'].ponderados.sum()/W:.2f}%")
for tp in ["zona NA (sin asignar) en la tabla censal", "AGEB sin fila en la tabla censal"]:
    print(f"  {tp}: {C[C.tipo==tp].clave_ageb.nunique()} AGEB")

# ---- 3. Fechas y dia de viaje ----
f = pd.to_datetime(t["Fecha"], format="%d-%b-%y"); dn = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
dd = t["Día de la semana que realizó los viajes:"].map(dn)
def prev_wd(x):
    d = x - pd.Timedelta(days=1)
    while d.weekday() >= 5: d -= pd.Timedelta(days=1)
    return d.weekday()
ok = dd == f.map(prev_wd)
fe = pd.DataFrame([
    dict(indicador="primer dia de entrevista", valor=str(f.min().date())), dict(indicador="ultimo dia de entrevista", valor=str(f.max().date())),
    dict(indicador="registros con dia = ultimo dia habil previo (%)", valor=round(100 * ok.mean(), 1)),
    dict(indicador="ponderados con dia = ultimo dia habil previo (%)", valor=round(100 * w[ok].sum() / W, 1)),
    dict(indicador="registros por mes (ene/feb/mar/abr)", valor="/".join(str(int((f.dt.month == m_).sum())) for m_ in (1, 2, 3, 4)))])
fe.to_csv(OUT + "auditoria_fechas.csv", index=False)
print(f"Dia reportado = ultimo dia habil previo: {100*ok.mean():.1f}% de registros ({100*w[ok].sum()/W:.1f}% ponderado). Fechas {f.min().date()} a {f.max().date()}")

# ---- 4. Duracion: rango declarado frente a suma de traslados ----
labs = ["Menos de 6", "6 a 10", "11 a 15", "16 a 30", "31 a 45", "46 a 60", "61 a 90", "91 a 120", "121 y +"]
bb = pd.cut(mins, bins=[-1, 5, 10, 15, 30, 45, 60, 90, 120, 10**6], labels=labs).astype(str)
dec = t["¿Cuántos minutos duró su viaje sumando todos los traslados?"].astype(str)
mis = bb != dec; rk = {l: i for i, l in enumerate(labs)}; df = (bb.map(rk) - dec.map(rk)).dropna()
du = pd.DataFrame([dict(indicador="viajes con rango declarado distinto al de la suma de traslados (%)", valor=round(100 * mis.mean(), 1)),
                   dict(indicador="de ellos, suma de traslados en rango menor (%)", valor=round(100 * (df < 0).sum() / (df != 0).sum(), 1)),
                   dict(indicador="promedio por suma de traslados, ponderado (min)", valor=round((mins * w).sum() / W, 1))])
du.to_csv(OUT + "auditoria_duracion.csv", index=False)

# ---- 5. Cadenas de viaje ----
ts = t.sort_values(["Folio Vivienda", "Folio Habitante", "Folio Viaje"]); gp = ts.groupby(["Folio Vivienda", "Folio Habitante"])
nxt = gp["Origen"].shift(-1); br = nxt.notna() & (nxt != ts["Destino"])
ca = pd.DataFrame([dict(indicador="transiciones evaluadas", valor=int(nxt.notna().sum())), dict(indicador="rupturas (origen siguiente != destino previo)", valor=int(br.sum())),
                   dict(indicador="rupturas (%)", valor=round(100 * br.sum() / nxt.notna().sum(), 2))])
ca.to_csv(OUT + "auditoria_cadenas.csv", index=False)

# ---- 6. Efecto de la calibracion de camion (factor SETRAN 0.56767147) en el reparto modal ----
F = 0.56767147; bus = m == "CAMIÓN O AUTOBÚS"; w2 = np.where(bus, w / F, w)
def reparto(ww):
    s = pd.Series(ww).groupby(m.values).sum(); tot = s.sum()
    return dict(viajes_millones=tot / 1e6, a_pie=100 * s["A PIE"] / tot, auto=100 * s["AUTOMÓVIL PARTICULAR"] / tot, camion=100 * s["CAMIÓN O AUTOBÚS"] / tot,
                pie_mas_transporte_publico=100 * (s["A PIE"] + s["CAMIÓN O AUTOBÚS"] + s["TREN LIGERO"] + s["MI MACRO"]) / tot)
cal = pd.DataFrame({"publicado": reparto(w), "sin_calibracion_camion": reparto(w2)}).round(2); cal.index.name = "indicador"; cal.to_csv(OUT + "auditoria_calibracion_modos.csv")
print(cal)
print("Listo: auditoria_*.csv en", OUT)
