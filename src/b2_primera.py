"""B2 · ¿qué distingue, AL MOMENTO de la 1.ª señal, las jugadas donde barren el extremo de las que no? (jul–sep 2026)"""
from pathlib import Path
import numpy as np, polars as pl
import b2_barrida as bb

OUT = Path(__file__).resolve().parent.parent / "reports" / "b2"
m = bb.minutos().sort("open_time")
m = m.with_columns(
    z=(pl.col("close") - pl.col("vwap_d")) / (pl.col("vwap_d_p1") - pl.col("vwap_d")),
    ret15=(pl.col("close") - pl.col("close").shift(15)) / pl.col("atr14"),
    ret60=(pl.col("close") - pl.col("close").shift(60)) / pl.col("atr14"),
    ret240=(pl.col("close") - pl.col("close").shift(240)) / pl.col("atr14"),
    pend_rv=(pl.col("rVWAP") - pl.col("rVWAP").shift(60)) / pl.col("atr14"),
    wv=(pl.col("close") - pl.col("vwap_w")) / pl.col("atr14"),
    atr_rel=pl.col("atr14") / pl.col("atr14").rolling_median(1440),
    hora=(pl.col("open_time") // 3_600_000) % 24)
r = pl.read_parquet(OUT / "barrida_senales.parquet").filter(pl.col("orden") == 1)
x = r.join(m, left_on="t_senal", right_on="open_time", how="left")
sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
x = x.with_columns(z_f=sg * pl.col("z"), ret15_f=sg * pl.col("ret15"), ret60_f=sg * pl.col("ret60"), ret240_f=sg * pl.col("ret240"),
                   tend_rv=sg * pl.col("pend_rv"), lado_semana=sg * pl.col("wv"), delta_f=sg * pl.col("delta1"),
                   d10_f=sg * pl.col("delta10s"), cvd_f=sg * pl.col("cvd15"),
                   burb_contra=pl.when(sg > 0).then(pl.col("ns15")).otherwise(pl.col("nb15")))
cols = {"z_f": "Profundidad (σ del VWAP, a favor)", "ret15_f": "Caída de los últimos 15 min (ATR, a favor)",
        "ret60_f": "Últimos 60 min (ATR)", "ret240_f": "Últimas 4 h (ATR)", "tend_rv": "Pendiente del rolling VWAP 60 min (ATR, a favor)",
        "lado_semana": "Distancia al VWAP semanal (ATR, a favor)", "vol15_rel": "Volumen 15 min relativo", "absorcion5": "Absorción",
        "delta_f": "Delta de la vela (a favor)", "d10_f": "Delta últimos 10 s", "cvd_f": "CVD 15 min (a favor)",
        "burb_contra": "Burbujas grandes en contra 15 min", "atr_rel": "ATR / ATR típico de 24 h", "hora": "Hora UTC"}
a, b = x.filter(~pl.col("barre_ext")), x.filter(pl.col("barre_ext"))
l = [f"1.ª señal de cada jugada, jul–sep 2026: {a.height} sin barrida vs {b.height} con barrida del extremo antes del VWAP.", "",
     "| Al momento de la 1.ª señal | Mediana sin barrida | Mediana con barrida |", "|---|---|---|"]
for c, nom in cols.items():
    l.append(f"| {nom} | {a[c].median():.2f} | {b[c].median():.2f} |")
# por cuartiles de las dos variables más prometedoras
for c in ("ret240_f", "tend_rv", "lado_semana", "atr_rel"):
    q = np.nanquantile(x[c].to_numpy(), [0.25, 0.5, 0.75]); g = np.digitize(x[c].to_numpy(), q)
    br = x["barre_ext"].to_numpy()
    l.append(f"\n{cols[c]} por cuartil (bajo → alto): barrida " + " · ".join(f"{br[g == k].mean():.0%}" for k in range(4)))
txt = "\n".join(l); (OUT / "primera_senal_rasgos.md").write_text(txt + "\n"); print(txt)
