"""Ejemplos dibujados de la ruptura de trendline aceitada (v2), para que Juan revise cómo se trazan las líneas.

Período de calibración (2024), pivots de 10 velas, filtro EMA 200 de 45m, TP en el nivel opuesto (primero a ≥ 2R).
Cada panel: velas de 1m (hora ART), los dos pivots y la línea hasta la ruptura, entrada al cierre, SL (extremo de 10
velas ± 0,25 ATR) y TP con el nombre del nivel. Se ven 60 velas después de la entrada para juzgar el resultado.
Salida: reports/trendlines/ejemplos_v2.png
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

import a_tp_nivel as atn
import indicadores as ind
from f3_correr import filtro_ema45
from trendlines import RVOL_MIN, senales_tl

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trendlines"
ART = ZoneInfo("America/Argentina/Buenos_Aires")
NOMBRE = {"MNDAY_H_vivo": "MNDAY-H", "MNDAY_L_vivo": "MNDAY-L", "vwap_d_p2": "VWAP sesión +2σ", "vwap_d_m2": "VWAP sesión −2σ",
          "dVAH": "dVAH", "dVAL": "dVAL", "vwap_w_p2": "VWAP semanal +2σ", "vwap_w_m2": "VWAP semanal −2σ",
          "mVAH_vivo": "mVAH", "mVAL_vivo": "mVAL", "rVAH": "rVAH", "rVAL": "rVAL"}


def velas(ax, x, o, h, l, c):
    col = np.where(c >= o, "#26a69a", "#ef5350")
    ax.vlines(x, l, h, color=col, lw=0.8)
    ax.bar(x, np.maximum(np.abs(c - o), 1e-9), bottom=np.minimum(o, c), color=col, width=0.7)


def main(desde: str = "2024-01", hasta: str = "2024-12", n: int = 10, cuantos: int = 6, semilla: int = 7,
         rvol_min: float | None = RVOL_MIN) -> None:
    atn.NIV = atn.NIV + ["mVAH_vivo", "mVAL_vivo", "rVAH", "rVAL"]
    s = senales_tl(desde, hasta, n, v2=True, rvol_min=rvol_min)
    s = atn.con_tp(filtro_ema45(s, desde).drop("tp"), desde, hasta)
    rng = np.random.default_rng(semilla)
    elegidas = pl.concat([s.filter(pl.col("lado") == ld).sample(cuantos // 2, seed=int(rng.integers(1e9))) for ld in ("long", "short")])
    df = ind.cargar(desde, hasta).select("open_time", "open", "high", "low", "close", "volume").sort("open_time")
    vma = df["volume"].rolling_mean(20).to_numpy()
    t = df["open_time"].to_numpy()
    fig = plt.figure(figsize=(16, 5.6 * cuantos // 2))
    gs = fig.add_gridspec(cuantos // 2, 2)
    celdas = [gs[r, col].subgridspec(2, 1, height_ratios=(3, 1), hspace=0.05) for col in range(2) for r in range(cuantos // 2)]
    for cel, f in zip(celdas, elegidas.sort("lado", "open_time").iter_rows(named=True)):
        ax, av = fig.add_subplot(cel[0]), None
        av = fig.add_subplot(cel[1], sharex=ax)
        i1, i2, ib = (int(np.searchsorted(t, f[k])) for k in ("t_piv1", "t_piv2", "open_time"))
        a, b = max(i1 - 25, 0), min(ib + 60, t.size - 1)
        x = np.arange(a, b + 1) - ib
        velas(ax, x, *(df[k].to_numpy()[a:b + 1] for k in ("open", "high", "low", "close")))
        larga = f["lado"] == "long"
        p1, p2 = (df["high" if larga else "low"][k] for k in (i1, i2))
        xs = np.array([i1, ib + 5]) - ib
        ax.plot(xs, p2 + (p2 - p1) / (i2 - i1) * (xs + ib - i2), color="#1e88e5", lw=1.6)
        ax.plot([i1 - ib, i2 - ib], [p1, p2], "o", color="#1e88e5", ms=6)
        ax.plot(0, f["close"], marker="^" if larga else "v", color="green" if larga else "red", ms=12, mec="k")
        ax.hlines(f["sl"], 0, x[-1], color="red", ls="--", lw=1.2)
        ax.hlines(f["tp"], 0, x[-1], color="green", ls="--", lw=1.2)
        nivel = next((NOMBRE[k] for k in atn.NIV if f.get(k) is not None and abs(f[k] - f["tp"]) < 1e-6), "?")
        r_tp = abs(f["tp"] - f["close"]) / abs(f["close"] - f["sl"])
        ax.text(x[-1], f["tp"], f" TP {nivel}\n ({r_tp:.1f}R)", va="center", fontsize=8, color="green")
        ax.text(x[-1], f["sl"], " SL", va="center", fontsize=8, color="red")
        ax.axvline(0, color="grey", lw=0.6, ls=":")
        hora = dt.datetime.fromtimestamp(f["open_time"] / 1000, ART).strftime("%a %d-%b-%Y %H:%M ART")
        ax.set_title(f"{f['lado'].upper()} · ruptura {hora} · {f['toques']} toques · pivots a {i2 - i1} velas", fontsize=10)
        tk = np.arange(x[0] - x[0] % 15, x[-1] + 1, 15)
        av.set_xticks(tk, [dt.datetime.fromtimestamp(t[min(k + ib, t.size - 1)] / 1000, ART).strftime("%H:%M") for k in tk], fontsize=8)
        lo = min(df["low"][a:b + 1].min(), f["sl"], f["tp"])
        hi = max(df["high"][a:b + 1].max(), f["sl"], f["tp"])
        ax.set_ylim(lo - 0.04 * (hi - lo), hi + 0.04 * (hi - lo))
        ax.grid(alpha=0.2)
        o_, c_, v_ = (df[k].to_numpy()[a:b + 1] for k in ("open", "close", "volume"))
        av.bar(x, v_, color=np.where(c_ >= o_, "#26a69a", "#ef5350"), width=0.7, alpha=0.6)
        av.bar([0], [v_[ib - a]], color="gold", edgecolor="k", width=0.9)
        av.plot(x, vma[a:b + 1], color="k", lw=0.8)
        av.plot(x, (rvol_min or 1.5) * vma[a:b + 1], color="k", lw=0.6, ls=":")
        av.text(0.01, 0.85, f"RVOL ruptura {f['rvol']:.1f} · delta {f['delta1']:+.2f}", transform=av.transAxes, fontsize=8)
        av.tick_params(labelsize=7); av.grid(alpha=0.2)
        plt.setp(ax.get_xticklabels(), visible=False)
    fig.suptitle("Ruptura de trendline v2 (línea limpia, vence a 2× la distancia entre pivots) · pivots 10 · EMA 200 45m a favor · "
                 f"ruptura con RVOL ≥ {rvol_min} · TP nivel opuesto ≥ 2R · calibración 2024", fontsize=11)
    fig.subplots_adjust(left=0.05, right=0.92, top=0.95, bottom=0.03, hspace=0.25, wspace=0.18)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "ejemplos_v2.png", dpi=110)
    print(elegidas.select("open_time", "lado", "close", "sl", "tp", "toques", "rvol", "delta1"))


if __name__ == "__main__":
    main()
