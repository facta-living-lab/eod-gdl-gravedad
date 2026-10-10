"""Prueba de robustez: gravitacional con y sin la calibracion de camion (factor SETRAN 0.56767147). Requiere gravedad_eod_zonas.py."""
import os
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'gravedad_eod_zonas.py')).read().split("rows = []; preds = {}")[0]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()): exec(src)
med=pd.read_csv(U+"IMEPLAN_Base_Viajes_Master.csv",encoding="latin-1",usecols=["Medio del viaje"],low_memory=False)["Medio del viaje"]
t["bus"]=(med.loc[t.index]=="CAMIÓN O AUTOBÚS").values
t2=t.copy(); t2["w"]=np.where(t2.bus,t2.w/0.56767147,t2.w)
props={"trabajo":["EMP","POCUPADA"],"estudio":["POBTOT"],"otros":["EMP","POBTOT"]}
rows=[]
for p in props:
    for nombre,d in [("publicado (con calibracion SETRAN)",t),("sin calibracion SETRAN",t2)]:
        T=od(d[d.prop==p]); _,b,mu=fit_fe(T,"potencia"); _,b2,mu2=fit_att(T,att,"potencia",props[p])
        rows.append(dict(proposito=p,ponderacion=nombre,viajes=T.sum(),beta_FE=b[0],CPC_FE=cpc(T,mu),beta_ATT=b2[0],elast=np.round(b2[1:],2).tolist(),CPC_ATT=cpc(T,mu2)))
R=pd.DataFrame(rows); pd.set_option("display.width",220); print(R.round(3).to_string(index=False)); R.to_csv(OUT+"sensibilidad_calibracion_setran.csv",index=False)
# correlacion de la matriz OD entre ponderaciones
for p in props:
    A=od(t[t.prop==p]).ravel(); B=od(t2[t2.prop==p]).ravel(); print(p,"CPC entre OD publicada y sin calibrar (misma escala): %.3f"%cpc(A*B.sum()/A.sum(),B))
