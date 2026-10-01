"""Estrategia B · selección de configuración y filtros SIN mirar el período de test.

Espacio de candidatos (fijado antes de ver resultados):
  configuración: nivel (dVAL/dVAH, ±2σ) × R mínimo (1, 2) × manejo (ninguno, breakeven 0,5 R, breakeven 1 R,
                 corte a 10 min, corte a 20 min) = 20 corridas del motor
  filtro de absorción: ninguno · absorción ≥ p40 · ≥ p60 (percentiles del entrenamiento)
  filtro de meta del día: ninguno · cruces del VWAP en el día ≥ p40 · ≥ p60
Criterio: mayor expectativa por trade en entrenamiento con ≥ 30 % de los trades de la configuración y ≥ 800 trades.
Esquemas: estático (entrena 2023–2024, testea 2025-01→2026-06) y walk-forward trimestral 2025Q1→2026Q2 con ventana
creciente desde 2023Q1. Feb–may 2026 se usó para calibrar las definiciones de B1: el OOS se reporta con y sin esos meses.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import polars as pl

import b_variables

RAIZ = Path(__file__).resolve().parent.parent
B = RAIZ / "reports" / "b"
CONFIGS = [(v, r, m) for v in ("va", "2sd") for r in ("1", "2") for m in ("", "_be0.5", "_be1", "_corte10", "_corte20")]
NOM_M = {"": "sin manejo", "_be0.5": "breakeven 0,5R", "_be1": "breakeven 1R", "_corte10": "corte 10 min", "_corte20": "corte 20 min"}
NOM_V = {"va": "dVAL/dVAH", "2sd": "±2σ"}


def cargar() -> dict:
    out = {}
    for v, r, m in CONFIGS:
        t = pl.read_parquet(B / f"trades_b1_{v}_2023-01_2026-06_rmin{r}_patas1{m}.parquet")
        t = b_variables.agregar(t, "2023-01", "2026-06")
        u = pl.from_epoch("t_senal", time_unit="ms")
        t = t.with_columns(trim=u.dt.strftime("%Y") + "Q" + ((u.dt.month() - 1) // 3 + 1).cast(pl.Utf8), mes=u.dt.strftime("%Y-%m"))
        out[(v, r, m)] = t
    return out


def candidatos(train: dict) -> list[tuple]:
    cands = []
    for k, t in train.items():
        a, c = t["absorcion"].to_numpy(), t["cruces_vwap_dia"].to_numpy().astype(float)
        fa = [None] + [("absorcion", float(np.nanquantile(a, q))) for q in (0.4, 0.6)]
        fc = [None] + [("cruces_vwap_dia", float(np.nanquantile(c, q))) for q in (0.4, 0.6)]
        for x, y in itertools.product(fa, fc):
            cands.append((k, tuple(f for f in (x, y) if f)))
    return cands


def aplicar(t: pl.DataFrame, filtros: tuple) -> pl.DataFrame:
    for var, umbral in filtros:
        t = t.filter(pl.col(var) >= umbral)
    return t


def elegir(train: dict) -> tuple:
    mejor = None
    for k, f in candidatos(train):
        x = aplicar(train[k], f)
        if x.height < 800 or x.height < 0.3 * train[k].height:
            continue
        e = x["r"].mean()
        if mejor is None or e > mejor[0]:
            mejor = (e, k, f)
    return mejor


def desc(k, f) -> str:
    v, r, m = k
    fs = ", ".join(f"{var} ≥ {u:.2f}" for var, u in f) or "sin filtros"
    return f"{NOM_V[v]} · R ≥ {r} · {NOM_M[m]} · {fs}"


def met(t: pl.DataFrame) -> dict:
    r = t["r"].to_numpy()
    rng = np.random.default_rng(0)
    bs = [r[rng.integers(0, r.size, r.size)].mean() for _ in range(2000)] if r.size else [np.nan]
    return {"n": int(r.size), "wr": float((r > 0).mean()) if r.size else np.nan, "exp": float(r.mean()) if r.size else np.nan,
            "ic": (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))}


def main() -> None:
    datos = cargar()
    sub = lambda cond: {k: t.filter(cond) for k, t in datos.items()}  # noqa: E731
    l = []
    # estático
    tr, te = sub(pl.col("trim") < "2025Q1"), sub(pl.col("trim") >= "2025Q1")
    e, k, f = elegir(tr)
    base_te = met(te[("va", "2", "")])
    l.append(f"ESTÁTICO · elegido con 2023–2024: {desc(k, f)} (entrenamiento {e:+.3f} R)")
    for nom, d in (("test 2025–2026", te), ("test sin feb–may 2026", sub((pl.col("trim") >= "2025Q1") & ~pl.col("mes").is_between(pl.lit("2026-02"), pl.lit("2026-05"))))):
        x = met(aplicar(d[k], f))
        l.append(f"   {nom}: {x['n']} trades · WR {x['wr']:.1%} · exp {x['exp']:+.3f} [{x['ic'][0]:+.3f}, {x['ic'][1]:+.3f}]")
    l.append(f"   (referencia: dVAL/dVAH R≥2 sin manejo ni filtros en 2025–2026: exp {base_te['exp']:+.3f})")
    # walk-forward
    l.append("WALK-FORWARD trimestral (cada trimestre elegido con todo lo anterior):")
    oos = []
    for q in ("2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"):
        e, k, f = elegir(sub(pl.col("trim") < q))
        x = aplicar(datos[k].filter(pl.col("trim") == q), f)
        oos.append(x)
        m = met(x)
        l.append(f"   {q}: {desc(k, f)} → {m['n']} trades · WR {m['wr']:.1%} · exp {m['exp']:+.3f}")
    o = pl.concat(oos, how="diagonal_relaxed")
    for nom, x in (("OOS concatenado", o), ("OOS sin feb–may 2026", o.filter(~pl.col("mes").is_between(pl.lit("2026-02"), pl.lit("2026-05"))))):
        m = met(x)
        l.append(f"   {nom}: {m['n']} trades · WR {m['wr']:.1%} · exp {m['exp']:+.3f} [{m['ic'][0]:+.3f}, {m['ic'][1]:+.3f}]")
    # descriptivo por componente (entrenamiento vs test) para entender qué aporta cada cosa
    l.append("DESCRIPTIVO (dVAL/dVAH, R ≥ 1): expectativa por manejo, entrenamiento 2023–2024 / test 2025–2026")
    for m in ("", "_be0.5", "_be1", "_corte10", "_corte20"):
        a, b = met(tr[("va", "1", m)]), met(te[("va", "1", m)])
        l.append(f"   {NOM_M[m]:16s}: {a['exp']:+.3f} (WR {a['wr']:.0%}) / {b['exp']:+.3f} (WR {b['wr']:.0%})")
    for var in ("absorcion", "cruces_vwap_dia", "delta_empujon"):
        t0, t1 = tr[("va", "1", "")], te[("va", "1", "")]
        cortes = np.nanquantile(t0[var].cast(pl.Float64).to_numpy(), [0.2, 0.4, 0.6, 0.8])
        def q(t):
            x = np.digitize(t[var].cast(pl.Float64).to_numpy(), cortes); r = t["r"].to_numpy()
            return " ".join(f"{r[x == j].mean():+.3f}" for j in range(5))
        l.append(f"   {var:16s} quintiles  entrenamiento: {q(t0)}  |  test: {q(t1)}")
    txt = "\n".join(l)
    print(txt)
    (B / "seleccion.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
