"""¿Qué distingue las entradas del trader de las señales B2 que NO tomó? Rasgos todavía no medidos:
niveles del día previo, nPOC, EMAs de 4h, niveles semanales/mensuales, estructura de 5m (septiembre 2026).

Grupos (todos en extremos, así que la comparación es justa, sin placebo):
  ganadas      sus 93 entradas (tarjetas)
  perdidas     sus 15 calaveras
  no tomadas   señales B2 (V10_hondo_ag) en las horas en que operó, a > 20 min de cualquier entrada suya
Rasgos al cierre de la vela previa, "a favor" del lado (long: el nivel está debajo o en el precio = soporte):
  soporte_X    hay un nivel del grupo X entre 0,5 ATR en contra y 0,25 ATR a favor del precio (el precio está apoyado)
  tend4h       long sobre la EMA 200 de 4h (short debajo); ema4h_cerca: alguna EMA 4h a ≤ 0,5 ATR
  5m_minimo_mayor  la vela de 5m en formación no hace un mínimo menor que la anterior (long)
  ash5_gira    la brecha del ASH 5m mejora respecto de la vela de 5m anterior
Salida: reports/b2/filtro_niveles.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import trader_sep as ts
import volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
GRUPOS = {
    "día previo (pdVAH/pdVAL/pdPOC/pdVWAP)": ["pdVAH", "pdVAL", "pdPOC", "pdVWAP"],
    "nPOC (POC diario sin revisitar)": ["nPOC_abajo", "nPOC_arriba"],
    "EMAs de 4h (13/21/34/100/200)": ["h4_13", "h4_21", "h4_34", "h4_100", "h4_200"],
    "semana (VWAP semanal ±1σ, pwVAH/pwVAL/pwVWAP, WO, PWH/PWL)": ["vwap_w", "vwap_w_p1", "vwap_w_m1", "pwVAH_vivo", "pwVAL_vivo", "pwVWAP_vivo", "WO", "PWH", "PWL"],
    "mes (mVAH/mVAL/mVWAP)": ["mVAH_vivo", "mVAL_vivo", "mVWAP_vivo"],
    "lunes y apertura (MNDAY-H/L, DO)": ["MNDAY_H_vivo", "MNDAY_L_vivo", "DO"],
    "perfil del día (dVAH/dVAL/dPOC)": ["dVAH", "dVAL", "dPOC"],
    "rolling 24 h (rVAH/rVAL/rVWAP)": ["rVAH", "rVAL", "rVWAP"],
}


def npoc(df: pl.DataFrame) -> pl.DataFrame:
    """POC diario más cercano por debajo y por encima del precio que todavía no fue revisitado (ningún precio posterior
    lo tocó), con la información disponible en cada minuto."""
    d = df.group_by(pl.col("open_time") // 86_400_000).agg(poc=pl.col("dPOC").last()).sort("open_time")
    dias, pocs = d["open_time"].to_numpy(), d["poc"].to_numpy()
    t, h, l, c = (df[x].to_numpy() for x in ("open_time", "high", "low", "close"))
    dia = t // 86_400_000
    vivos: list[float] = []
    abajo, arriba = np.full(t.size, np.nan), np.full(t.size, np.nan)
    di = 0
    for i in range(t.size):
        if i > 0 and dia[i] != dia[i - 1]:              # cerró un día: su POC entra a la lista
            k = np.searchsorted(dias, dia[i - 1])
            if k < dias.size and np.isfinite(pocs[k]):
                vivos.append(float(pocs[k]))
        vivos = [p for p in vivos if not (l[i] <= p <= h[i])]
        if vivos:
            v = np.array(vivos)
            ab, ar = v[v <= c[i]], v[v > c[i]]
            abajo[i] = ab.max() if ab.size else np.nan
            arriba[i] = ar.min() if ar.size else np.nan
        di += 1
    return df.with_columns(nPOC_abajo=pl.Series(abajo), nPOC_arriba=pl.Series(arriba))


def con_5m(df: pl.DataFrame) -> pl.DataFrame:
    b = pl.col("open_time") // 300_000
    df = df.with_columns(b5=b)
    df = df.with_columns(lo5=pl.col("low").cum_min().over("b5"), hi5=pl.col("high").cum_max().over("b5"))
    prev = df.group_by("b5").agg(lo5p=pl.col("low").min(), hi5p=pl.col("high").max(),
                                 g5p=((pl.col("ash_bulls_5m_vivo") - pl.col("ash_bears_5m_vivo")) /
                                      (pl.col("ash_bulls_5m_vivo") + pl.col("ash_bears_5m_vivo"))).last()).with_columns(pl.col("b5") + 1)
    return df.join(prev, on="b5", how="left").sort("open_time")


def rasgos(df: pl.DataFrame, ev: pl.DataFrame) -> pl.DataFrame:
    x = ev.with_columns(k=pl.col("t") - 60_000).join(df, left_on="k", right_on="open_time", how="left")
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    out = {"grupo": x["grupo"]}
    for nom, cols in GRUPOS.items():
        cols = [c for c in cols if c in x.columns]
        d = pl.concat_list([(sg * (pl.col("close") - pl.col(c)) / pl.col("atr14")) for c in cols])
        out[f"soporte · {nom}"] = x.select(d.list.eval(pl.element().is_between(-0.25, 0.5)).list.any()).to_series()
    out["tendencia 4h a favor (sobre la EMA 200 de 4h en un long)"] = x.select((sg * (pl.col("close") - pl.col("h4_200"))) > 0).to_series()
    out["5m: la vela en formación no rompe el extremo de la anterior"] = x.select(
        pl.when(sg > 0).then(pl.col("lo5") >= pl.col("lo5p")).otherwise(pl.col("hi5") <= pl.col("hi5p"))).to_series()
    g5 = (pl.col("ash_bulls_5m_vivo") - pl.col("ash_bears_5m_vivo")) / (pl.col("ash_bulls_5m_vivo") + pl.col("ash_bears_5m_vivo"))
    out["ASH 5m mejorando respecto de la vela de 5m anterior"] = x.select((sg * (g5 - pl.col("g5p"))) > 0).to_series()
    out["precio del lado a favor del VWAP de la semana previa (pwVWAP)"] = x.select((sg * (pl.col("close") - pl.col("pwVWAP_vivo"))) > 0).to_series()
    return pl.DataFrame(out)


def main() -> None:
    df = volumen.agregar(ts.base("2026-07", "2026-09"), "2026-07", "2026-09", con_segundos=False)
    df = con_5m(npoc(df.sort("open_time")))
    gan = pl.read_parquet(RAIZ / "reports/trader_sep/entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    per = pl.read_parquet(RAIZ / "reports/trader_sep/perdidas.parquet")
    s = pl.read_parquet(OUT / "senales_sep_V10_hondo_ag.parquet")
    ent = gan.select("t_entrada", "lado").vstack(per.select("t_entrada", "lado"))
    dias = ent.group_by(pl.col("t_entrada") // 86_400_000).agg(a=pl.col("t_entrada").min() - 3_600_000, b=pl.col("t_entrada").max() + 3_600_000)
    te = ent["t_entrada"].to_numpy()
    no_tom = [(a, l) for a, l in s.select("t_senal", "lado").iter_rows()
              if any(x <= a <= y for _, x, y in dias.iter_rows()) and np.min(np.abs(te - a)) > 20 * 60_000]
    ev = pl.concat([
        gan.select(pl.col("t_entrada").alias("t"), "lado").with_columns(grupo=pl.lit("ganadas")),
        per.select(pl.col("t_entrada").alias("t"), "lado").with_columns(grupo=pl.lit("perdidas")),
        pl.DataFrame(no_tom, schema={"t": pl.Int64, "lado": pl.Utf8}, orient="row").with_columns(grupo=pl.lit("no tomadas")),
    ])
    r = rasgos(df, ev)
    n = {g: r.filter(pl.col("grupo") == g).height for g in ("ganadas", "perdidas", "no tomadas")}
    l = [f"Septiembre 2026. Ganadas {n['ganadas']} · perdidas {n['perdidas']} · señales B2 no tomadas en sus horas {n['no tomadas']}.",
         "Soporte = nivel entre 0,25 ATR a favor y 0,5 ATR en contra del precio (apoyado en el nivel).", "",
         "| Al entrar… | Ganadas | Perdidas | B2 no tomadas | Ganadas − no tomadas |", "|---|---|---|---|---|"]
    filas = []
    for c in r.columns[1:]:
        v = {g: float(r.filter(pl.col("grupo") == g)[c].cast(pl.Float64).mean()) for g in n}
        filas.append((v["ganadas"] - v["no tomadas"], c, v))
    for dif, c, v in sorted(filas, key=lambda x: -abs(x[0])):
        l.append(f"| {c} | {v['ganadas']:.0%} | {v['perdidas']:.0%} | {v['no tomadas']:.0%} | {dif * 100:+.0f} pts |")
    txt = "\n".join(l)
    (OUT / "filtro_niveles.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
