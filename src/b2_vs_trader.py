"""¿Por qué el trader gana ~75 % y B2 no? Mismo cálculo para sus 93 entradas y para las señales B2 (jul–sep 2026):
probabilidad de que el precio avance +X ATR a favor ANTES de ir −Y ATR en contra (velas de 1m, horizonte 4 h)."""
from pathlib import Path
import numpy as np, polars as pl
import b2_barrida as bb, b2_timing as bt

RAIZ = Path(__file__).resolve().parent.parent
m = bb.minutos().sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
t, h, l, atr = (m[x].to_numpy() for x in ("open_time", "high", "low", "atr14"))
def gana(ts_, lado, p, x, y):
    i = int(np.searchsorted(t, ts_)); sg = 1 if lado == "long" else -1; a = atr[i]
    hh, ll = h[i + 1:i + 241], l[i + 1:i + 241]
    fav = (hh - p) / a if sg > 0 else (p - ll) / a
    con = (p - ll) / a if sg > 0 else (hh - p) / a
    kf = np.argmax(fav >= x) if (fav >= x).any() else 10**9
    kc = np.argmax(con >= y) if (con >= y).any() else 10**9
    return kf < kc
tr = pl.read_parquet(RAIZ / "reports/trader_sep/entradas.parquet").filter(pl.col("t_entrada").is_not_null())
ent = [(a, b, c - 20) for a, b, c in tr.select("t_entrada", "lado", "entrada").iter_rows()]
s = bt.senales(m, "hondo_ag")
b2s = [(a, b, c) for a, b, c in s.iter_rows()]
l_ = ["| Salida: +X ATR a favor antes de −Y ATR en contra | Sus entradas (93) | Señales B2 (" + str(len(b2s)) + ") |", "|---|---|---|"]
for x, y in [(0.5, 1), (1, 1), (1, 2), (1, 0.5), (2, 1), (3, 1.5), (3, 1)]:
    a = np.mean([gana(*e, x, y) for e in ent]); b = np.mean([gana(*e, x, y) for e in b2s])
    l_.append(f"| +{x:g} / −{y:g} ATR | {a:.0%} | {b:.0%} |")
txt = "\n".join(l_); (RAIZ / "reports/b2/trader_vs_b2.md").write_text(txt + "\n"); print(txt)
