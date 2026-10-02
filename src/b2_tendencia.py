"""B2 + filtro de tendencia de 4h (hipótesis sacada de las entradas del trader, 2026-10-02: 78 % de sus entradas van a
favor de la EMA 200 de 4h contra 36 % de las señales B2 que no tomó; él opera 80 % longs en un septiembre alcista).

Regla fijada ANTES de mirar 2023–2025: se toma la señal B2 (V10_hondo_ag) solo si el precio está del lado de la
tendencia: long sobre la EMA 200 de 4h, short debajo (EMA "en vivo", con la vela de 4h en formación).
Mismas 36 salidas de b2_tp.py (filtro R ≥ 2, una pata, sin comisiones). Calibración jul–sep 2026 → test 2023–2025.
Salida: reports/b2/tendencia_4h.md
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import polars as pl

import b2_timing as bt
import b2_tp
import trader_sep as ts
import volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
COLS = b2_tp.COLS + ["h4_200"]


def minutos(desde: str, hasta: str, filtro_anio: int | None, nombre: str) -> pl.DataFrame:
    f = OUT / f"minutos_tend_{nombre}.parquet"
    if f.exists():
        return pl.read_parquet(f)
    df = volumen.agregar(ts.base(desde, hasta), desde, hasta, con_segundos=False).select(COLS)
    if filtro_anio:
        df = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.year() == filtro_anio)
    else:
        df = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m") >= "2026-07")
    df.write_parquet(f)
    return df


def con_tendencia(m: pl.DataFrame, s: pl.DataFrame) -> pl.DataFrame:
    x = s.join(m.select("open_time", "close", "h4_200"), left_on="t_senal", right_on="open_time", how="left")
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    return x.filter((sg * (pl.col("close") - pl.col("h4_200"))) > 0).select(s.columns)


def preparar(m: pl.DataFrame):
    m = m.sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    s = bt.senales(m, "hondo_ag")
    return m, s, con_tendencia(m, s)


def main() -> None:
    cal = preparar(minutos("2026-01", "2026-09", None, "cal"))
    tests = [preparar(minutos(f"{a - 1}-01", f"{a}-12", a, str(a))) for a in (2023, 2024, 2025)]
    print("datos listos", flush=True)
    l = ["B2 con filtro de tendencia 4h (EMA 200) vs sin filtro. R ≥ 2, una pata, sin comisiones.",
         "Calibración jul–sep 2026 → test 2023–2025.", "",
         "| SL | TP | BE | Sin filtro: calib. · test (trades · gana · R) | Con tendencia 4h: calib. · test (trades · gana · R) |",
         "|---|---|---|---|---|"]
    filas = []
    for b, tp, be in itertools.product((0.25, 0.5, 1.0), ("2R", "2.5R", "3R", "vwap", "banda", "nivel"), (None, 1.0)):
        res = {}
        for k, j in (("sin", 1), ("con", 2)):
            rc = b2_tp.simular(cal[0], cal[j], b, tp, be)
            rt = np.concatenate([b2_tp.simular(t[0], t[j], b, tp, be) for t in tests])
            res[k] = (rc, rt)
        filas.append((b, tp, be, res))
        f = lambda r: f"{r.size} · {(r > 0).mean():.0%} · {r.mean():+.3f}" if r.size else "0"  # noqa: E731
        l.append(f"| {b:g} ATR | {tp} | {'+1R' if be else 'no'} | {f(res['sin'][0])} → {f(res['sin'][1])} | {f(res['con'][0])} → {f(res['con'][1])} |")
    # resumen: promedio sobre las 36 salidas y la elegida en calibración con filtro
    for k in ("sin", "con"):
        m_t = np.mean([f[3][k][1].mean() for f in filas])
        pos = sum(f[3][k][1].mean() > 0 for f in filas)
        l.append(f"\n{'Sin' if k == 'sin' else 'Con'} filtro: R medio en test promediado sobre las 36 salidas {m_t:+.3f}; positivas {pos}/36.")
    mejor = max(filas, key=lambda f: f[3]["con"][0].mean() if f[3]["con"][0].size >= 100 else -9)
    rt = mejor[3]["con"][1]
    rng = np.random.default_rng(0)
    bs = [rt[rng.integers(0, rt.size, rt.size)].mean() for _ in range(2000)]
    l.append(f"Elegida en calibración (con filtro): SL {mejor[0]:g} ATR · TP {mejor[1]} · BE {'+1R' if mejor[2] else 'no'} → "
             f"test {rt.size} trades, gana {(rt > 0).mean():.0%}, R medio {rt.mean():+.3f} [IC 95 % {np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}]")
    txt = "\n".join(l)
    (OUT / "tendencia_4h.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
