"""B2 · distintos TP con filtro R ≥ 2 (Juan, 2026-10-01: Variational no cobra comisiones; el VWAP no es el TP habitual
del trader; mínimo 1:2).

Señal V10_hondo_ag, una pata, una posición por lado a la vez. Long (short espejo):
  SL   extremo de 10 velas − b · ATR (b = 0,25 / 0,5 / 1)
  TP   2R · 2,5R · 3R (fijos) · vwap (VWAP de sesión) · banda (+1σ del VWAP de sesión) · nivel (primer nivel del gráfico
       a ≥ 2R: bandas ±1σ/±2σ y VWAP de sesión, VWAP semanal, rolling VWAP, dVAH/dVAL)
  filtro: no se entra si el R hasta el TP es < 2
  manejo: sin breakeven / breakeven al llegar a +1R
Velas de 1m (si SL y TP caen en la misma vela, SL), horizonte 24 h, sin comisiones.
Se elige en calibración (jul–sep 2026) y se muestran TODAS en el test 2023–2025.
Salida: reports/b2/tp_r2.md
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import polars as pl

import b2_barrida as bb
import b2_timing as bt
import trader_sep as ts
import volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
NIV = ["vwap_d", "vwap_d_p1", "vwap_d_m1", "vwap_d_p2", "vwap_d_m2", "vwap_w", "rVWAP", "dVAH", "dVAL"]
COLS = ["open_time", "open", "high", "low", "close", "atr14", "delta1", "vol15_rel", "absorcion5", "nb15", "ns15"] + NIV


def minutos_test(a: int) -> pl.DataFrame:
    f = OUT / f"minutos_{a}.parquet"
    if f.exists():
        return pl.read_parquet(f)
    df = volumen.agregar(ts.base(f"{a - 1}-12", f"{a}-12"), f"{a - 1}-12", f"{a}-12", con_segundos=False).select(COLS)
    df = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.year() == a)
    df.write_parquet(f)
    return df


def simular(m: pl.DataFrame, s: pl.DataFrame, b: float, tp_modo: str, be: float | None) -> np.ndarray:
    t = m["open_time"].to_numpy()
    h, l, c, atr = (m[x].to_numpy() for x in ("high", "low", "close", "atr14"))
    niv = np.column_stack([m[x].to_numpy() for x in NIV])
    idx = {v: i for i, v in enumerate(t)}
    res = []
    for lado in ("long", "short"):
        sg = 1 if lado == "long" else -1
        libre = -1
        for ts_ in s.filter(pl.col("lado") == lado)["t_senal"].to_list():
            i = idx[ts_]
            if i <= libre:
                continue
            ext = l[i - 9:i + 1].min() if sg > 0 else h[i - 9:i + 1].max()
            fill = c[i]
            sl = ext - sg * b * atr[i]
            rg = sg * (fill - sl)
            if rg <= 0:
                continue
            if tp_modo.endswith("R"):
                tp = fill + sg * float(tp_modo[:-1]) * rg
            elif tp_modo == "vwap":
                tp = niv[i, 0]
            elif tp_modo == "banda":
                tp = niv[i, 1] if sg > 0 else niv[i, 2]
            else:  # nivel: el más cercano a favor que deje R ≥ 2
                d = sg * (niv[i] - fill)
                ok = d >= 2 * rg
                if not ok.any():
                    continue
                tp = fill + sg * d[ok].min()
            if not np.isfinite(tp) or sg * (tp - fill) < 2 * rg - 1e-9:
                continue                               # filtro 1:2
            fin = min(i + 1440, t.size - 1)
            stop, r, j_sal = sl, None, fin
            for j in range(i + 1, fin + 1):
                if (l[j] <= stop) if sg > 0 else (h[j] >= stop):
                    r, j_sal = sg * (stop - fill) / rg, j
                    break
                if (h[j] >= tp) if sg > 0 else (l[j] <= tp):
                    r, j_sal = sg * (tp - fill) / rg, j
                    break
                if be is not None and sg * ((h[j] if sg > 0 else l[j]) - fill) >= be * rg:
                    stop = fill if sg * (fill - stop) > 0 else stop      # breakeven desde la vela siguiente
            if r is None:
                r = sg * (c[fin] - fill) / rg
            res.append(r)
            libre = j_sal
    return np.array(res)


def resumen(r: np.ndarray) -> str:
    if r.size == 0:
        return "0 | – | –"
    return f"{r.size} | {(r > 0).mean():.0%} | {r.mean():+.3f}"


def main() -> None:
    cal = bb.minutos().sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    s_cal = bt.senales(cal, "hondo_ag")
    tests = {}
    for a in (2023, 2024, 2025):
        m = minutos_test(a).sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
        tests[a] = (m, bt.senales(m, "hondo_ag"))
        print("listo", a, flush=True)
    filas = []
    for b, tp, be in itertools.product((0.25, 0.5, 1.0), ("2R", "2.5R", "3R", "vwap", "banda", "nivel"), (None, 1.0)):
        rc = simular(cal, s_cal, b, tp, be)
        rt = np.concatenate([simular(m, s, b, tp, be) for m, s in tests.values()])
        filas.append((b, tp, be, rc, rt))
    mejor = max(filas, key=lambda f: f[3].mean() if f[3].size >= 100 else -9)
    l = ["B2 con filtro R ≥ 2, una pata, sin comisiones. Calibración jul–sep 2026 → test 2023–2025 (todas las variantes).", "",
         "| SL detrás del extremo | TP | Breakeven | Calib.: trades · gana · R medio | Test: trades · gana · R medio |",
         "|---|---|---|---|---|"]
    for b, tp, be, rc, rt in filas:
        marca = " **← elegida en calibración**" if (b, tp, be) == mejor[:3] else ""
        l.append(f"| {b:g} ATR | {tp} | {'+1R' if be else 'no'} | {resumen(rc)} | {resumen(rt)}{marca} |")
    rt = mejor[4]
    rng = np.random.default_rng(0)
    bs = [rt[rng.integers(0, rt.size, rt.size)].mean() for _ in range(2000)]
    l += ["", f"Elegida en calibración: SL {mejor[0]:g} ATR · TP {mejor[1]} · BE {'+1R' if mejor[2] else 'no'} → test "
          f"{rt.size} trades, gana {(rt > 0).mean():.0%}, R medio {rt.mean():+.3f} [IC 95 % {np.percentile(bs, 2.5):+.3f}, "
          f"{np.percentile(bs, 97.5):+.3f}]"]
    txt = "\n".join(l)
    (OUT / "tp_r2.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
