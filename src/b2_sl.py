"""B2 · ¿cuánto barren el extremo? Para cada señal (jul–sep 2026, V10_hondo_ag): excursión en contra MÁS ALLÁ del
extremo de 10 velas antes de tocar el TP (VWAP de sesión), en ATR, y resultado con distintos SL:
  ext10 + b · ATR (b = 0,25 / 0,5 / 0,75 / 1 / 1,5)  ·  extremo de 60 min + 0,25 ATR  ·  extremo de la jugada hasta la
señal + 0,25 ATR. Velas de 1m, sin breakeven, sin comisiones (diagnóstico). Salida: reports/b2/sl_barrida.md"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import b2_barrida as bb
import b2_timing as bt

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"


def simular(m, s, modo, b):
    t = m["open_time"].to_numpy()
    h, l, c, atr, vw = (m[x].to_numpy() for x in ("high", "low", "close", "atr14", "vwap_d"))
    res = []
    for ts_, lado in s.select("t_senal", "lado").iter_rows():
        i = int(np.searchsorted(t, ts_)); sg = 1 if lado == "long" else -1
        n = {"ext10": 10, "ext60": 60}[modo]
        ext = l[i - n + 1:i + 1].min() if sg > 0 else h[i - n + 1:i + 1].max()
        sl = ext - sg * b * atr[i]; tp, fill = vw[i], c[i]; rg = sg * (fill - sl)
        if sg * (tp - fill) <= 0 or rg <= 0:
            continue
        fin = min(i + 1440, t.size); hh, ll = h[i + 1:fin], l[i + 1:fin]
        tt = (hh >= tp) if sg > 0 else (ll <= tp); ss = (ll <= sl) if sg > 0 else (hh >= sl)
        ktp = int(np.argmax(tt)) if tt.any() else 10**9; ksl = int(np.argmax(ss)) if ss.any() else 10**9
        r = -1.0 if ksl <= ktp and ksl < 10**9 else (sg * (tp - fill) / rg if ktp < 10**9 else sg * (c[fin - 1] - fill) / rg)
        # excursión más allá del extremo antes del TP (en ATR)
        hasta = ktp if ktp < 10**9 else fin - i - 1
        adv = (ext - ll[:hasta + 1].min()) if sg > 0 else (hh[:hasta + 1].max() - ext)
        res.append((r, sg * (tp - fill) / rg, max(adv, 0) / atr[i], ktp < 10**9))
    return np.array(res)


def main():
    m = bb.minutos().sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    s = bt.senales(m, "hondo_ag")
    base = simular(m, s, "ext10", 0.25)
    adv = base[:, 2]; llega = base[:, 3].astype(bool)
    l = [f"Señales: {len(base)}. Llegan al VWAP alguna vez en 24 h: {llega.mean():.0%}.",
         "Cuánto pasa el precio más allá del extremo de 10 velas antes de llegar al VWAP (en ATR), entre las que llegan:",
         "  " + " · ".join(f"p{q}: {np.percentile(adv[llega], q):.2f}" for q in (25, 50, 75, 90)),
         f"  no lo pasa: {(adv[llega] == 0).mean():.0%} · lo pasa ≤ 0,25 ATR: {(adv[llega] <= 0.25).mean():.0%} · "
         f"≤ 0,5: {(adv[llega] <= 0.5).mean():.0%} · ≤ 1: {(adv[llega] <= 1).mean():.0%}", "",
         "| SL | Trades | Gana (llega al VWAP) | R hasta el TP (mediana) | R medio |", "|---|---|---|---|---|"]
    for modo, b in [("ext10", 0.25), ("ext10", 0.5), ("ext10", 0.75), ("ext10", 1.0), ("ext10", 1.5), ("ext60", 0.25), ("ext60", 0.5)]:
        x = simular(m, s, modo, b)
        nom = f"extremo de {modo[3:]} velas + {b:g} ATR"
        l.append(f"| {nom} | {len(x)} | {(x[:, 0] > 0).mean():.0%} | {np.median(x[:, 1]):.2f} | {x[:, 0].mean():+.3f} |")
    txt = "\n".join(l); (OUT / "sl_barrida.md").write_text(txt + "\n"); print(txt)


if __name__ == "__main__":
    main()
