"""¿Qué niveles usa el trader como SALIDA? (pedido de Juan 2026-10-02)

Las cajas long/short de sus capturas son demasiado tenues para leerlas automáticamente (la detección por color se
confunde con el perfil de volumen), así que se usan dos fuentes:
  1. Órdenes de cierre con hora (lista del 28-sep, UTC+2): precio de cada cierre → niveles a ≤ 0,25 ATR.
  2. Fin del recorrido a favor de cada entrada GANADORA (93 tarjetas): el extremo a favor alcanzado antes de que el
     precio vuelva a la entrada (o en 4 h). Es el mejor lugar posible para salir; se mira qué nivel había ahí.
Cada nivel se compara con 50 placebos (el mismo nivel desplazado ±0,2–1 % por día).
Salida: reports/trader_sep/salidas.md
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

import f5_niveles as f5
import trader_sep as ts
from b2_filtro_niveles import npoc

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trader_sep"
TZ = dt.timezone(dt.timedelta(hours=2))
CIERRES_28 = [("08:07:16", 83233.5), ("08:11:17", 83259.6), ("08:12:11", 83273.3), ("14:53:55", 83530.9),
              ("15:39:08", 83709.7), ("15:55:58", 83674.4), ("15:56:15", 83627.1)]


def cerca(df, idx_t, precios, rng, nreps=50):
    t = df["open_time"].to_numpy()
    dia = t // 86_400_000
    ii = np.array([int(np.searchsorted(t, x)) for x in idx_t])
    a = df["atr14"].to_numpy()[ii]
    res = []
    for nom, col in f5.NIVELES.items():
        if col not in df.columns:
            continue
        L = df[col].cast(pl.Float64).to_numpy()
        real = np.abs(precios - L[ii]) <= 0.25 * a
        pla = np.mean([np.mean(np.abs(precios - f5.placebo(L, dia, rng)[ii]) <= 0.25 * a) for _ in range(nreps)])
        res.append((nom, int(real.sum()), real.mean(), pla))
    return sorted(res, key=lambda x: -(x[2] - x[3]))


def main() -> None:
    rng = np.random.default_rng(1)
    df = npoc(ts.base("2026-07", "2026-09").sort("open_time"))
    t, h, l, c = (df[x].to_numpy() for x in ("open_time", "high", "low", "close"))
    # 1. cierres con hora
    tc = [int(dt.datetime.fromisoformat(f"2026-09-28T{hh}").replace(tzinfo=TZ).timestamp() * 1000) // 60_000 * 60_000 for hh, _ in CIERRES_28]
    pc = np.array([p - 20 for _, p in CIERRES_28])
    r1 = cerca(df, tc, pc, rng)
    # 2. fin del recorrido a favor de las ganadoras
    g = pl.read_parquet(OUT / "entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    fin_t, fin_p, mfe = [], [], []
    for te, lado, p in g.select("t_entrada", "lado", "entrada").iter_rows():
        i = int(np.searchsorted(t, te))
        sg = 1 if lado == "long" else -1
        e = p - 20
        j1 = min(i + 240, t.size - 1)
        vuelve = np.flatnonzero((l[i + 1:j1] <= e) if sg > 0 else (h[i + 1:j1] >= e))
        k = i + 1 + (vuelve[vuelve > 5][0] if (vuelve > 5).any() else j1 - i - 1)
        seg = slice(i, k + 1)
        j = i + int(np.argmax(h[seg]) if sg > 0 else np.argmin(l[seg]))
        fin_t.append(int(t[j]))
        fin_p.append(h[j] if sg > 0 else l[j])
        mfe.append(sg * ((h[j] if sg > 0 else l[j]) - e) / df["atr14"][i])
    r2 = cerca(df, fin_t, np.array(fin_p), rng)
    m = np.array(mfe)
    lin = ["# Salidas del trader", "",
           "Las cajas long/short de TradingView de sus capturas son muy tenues para leerlas automáticamente; por eso se usan "
           "sus cierres con hora (28-sep) y el punto donde terminó el recorrido a favor de cada entrada ganadora.", "",
           f"Recorrido a favor de sus 93 ganadoras hasta que el precio vuelve a la entrada (o 4 h): mediana {np.median(m):.1f} ATR "
           f"(p25 {np.percentile(m, 25):.1f}, p75 {np.percentile(m, 75):.1f}).", "",
           "## 1. Sus 7 cierres con hora del 28-sep: niveles a ≤ 0,25 ATR", "", "| Nivel | Cierres | Placebo |", "|---|---|---|"]
    for nom, n, a1, a0 in r1[:10]:
        if n:
            lin.append(f"| {nom} | {n} de 7 | {a0:.0%} |")
    lin += ["", "## 2. Dónde terminó el recorrido a favor de sus 93 ganadoras", "",
            "| Nivel | Finales a ≤ 0,25 ATR | Placebo | Veces más |", "|---|---|---|---|"]
    for nom, n, a1, a0 in r2[:15]:
        lin.append(f"| {nom} | {n} ({a1:.0%}) | {a0:.0%} | {a1 / a0:.1f}× |" if a0 > 0 else f"| {nom} | {n} ({a1:.0%}) | 0 % | – |")
    txt = "\n".join(lin)
    (OUT / "salidas.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
