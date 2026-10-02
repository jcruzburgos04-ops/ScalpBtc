"""B2 FINAL (congelada 2026-10-02, aprobada por Juan). No se vuelve a tocar: se mide en la reserva oct–dic 2026.

Señal (long; short espejo), al cierre de cada vela de 1m:
  setup     precio más allá de −1,5σ del VWAP de sesión · volumen 15 min ≥ 1,5× lo normal · absorción ≥ 1
            (en alguna de las últimas 10 velas)
  disparo   la vela no hace un mínimo nuevo de 5 velas, cierra verde y con delta comprador; 15 min entre señales;
            nunca en los primeros 30 min del día UTC
  tendencia precio sobre la EMA 200 de 45m (vela de 45m en formación)
Salida: la elegida en calibración (jul–sep 2026) entre las 36 de b2_tp.py, con filtro R ≥ 2. Sin comisiones.
Uso: python src/b2_final.py [AAAA-MM AAAA-MM]  → con meses: mide la regla congelada en ese tramo.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import polars as pl

import b2_tendencia as bten
import b2_tendencias as btd
import b2_tp

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
FILTRO = "precio a favor de la EMA 200 de 45m"
SALIDA = (0.25, "vwap", 1.0)   # SL ext10 ± 0,25 ATR · TP VWAP de sesión · breakeven +1R (elegida en calibración)


def preparar(m: pl.DataFrame):
    m = btd.agregar(m.sort("open_time")).with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    return m, btd.filtrar(m, b2_tp.bt.senales(m, "hondo_ag"), FILTRO)


def ic(r):
    rng = np.random.default_rng(0)
    bs = [r[rng.integers(0, r.size, r.size)].mean() for _ in range(2000)]
    return np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main() -> None:
    cal = preparar(bten.minutos("2026-01", "2026-09", None, "cal"))
    tests = [preparar(bten.minutos(f"{a - 1}-01", f"{a}-12", a, str(a))) for a in (2023, 2024, 2025)]
    filas = []
    for b, tp, be in itertools.product((0.25, 0.5, 1.0), ("2R", "2.5R", "3R", "vwap", "banda", "nivel"), (None, 1.0)):
        rc = b2_tp.simular(*cal, b, tp, be)
        rt = np.concatenate([b2_tp.simular(*t, b, tp, be) for t in tests])
        filas.append((b, tp, be, rc, rt))
    elegible = [f for f in filas if f[3].size >= 100]
    b, tp, be, rc, rt = max(elegible, key=lambda f: f[3].mean())
    lo, hi = ic(rt)
    l = ["# B2 final (congelada 2026-10-02)", "",
         "Señal: más allá de ±1,5σ del VWAP de sesión + volumen 15 min ≥ 1,5× + absorción ≥ 1, disparo en la primera vela",
         "que agota la agresión en contra, solo a favor de la EMA 200 de 45m. Filtro R ≥ 2, una pata, sin comisiones.", "",
         f"**Salida elegida en calibración:** SL extremo de 10 velas ± {b:g} ATR · TP {tp} · breakeven {'+1R' if be else 'no'}", "",
         "| Tramo | Trades | Gana | R medio | IC 95 % |", "|---|---|---|---|---|",
         f"| Calibración jul–sep 2026 | {rc.size} | {(rc > 0).mean():.0%} | {rc.mean():+.3f} | {ic(rc)[0]:+.3f} a {ic(rc)[1]:+.3f} |",
         f"| Test 2023–2025 | {rt.size} | {(rt > 0).mean():.0%} | {rt.mean():+.3f} | {lo:+.3f} a {hi:+.3f} |", "",
         "Todas las salidas con este filtro (calibración → test):", "", "| SL | TP | BE | Calib. | Test |", "|---|---|---|---|---|"]
    for f in filas:
        l.append(f"| {f[0]:g} | {f[1]} | {'+1R' if f[2] else 'no'} | {f[3].size} · {f[3].mean():+.3f} | {f[4].size} · {f[4].mean():+.3f} |")
    txt = "\n".join(l)
    (OUT / "b2_final.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
