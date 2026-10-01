"""Estrategia B · validación pre-registrada en 2022 (ver DECISIONES.md, 2026-10-01).
Configuración congelada: B1 dVAL/dVAH, R ≥ 2, 1 pata, breakeven 0,5 R.
H0: expectativa > 0 · H1: cruces del VWAP ≤ 16 rinde más que > 16 (global y por tramo de 4 h) ·
H2: 00:30–04:00 UTC rinde más que el resto."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import b_variables

RAIZ = Path(__file__).resolve().parent.parent
CORTE_CRUCES = 16  # p40 de 2023–2024, fijado antes de ver 2022


def ic(r: np.ndarray, n: int = 4000) -> tuple[float, float]:
    rng = np.random.default_rng(0)
    bs = [r[rng.integers(0, r.size, r.size)].mean() for _ in range(n)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def ic_dif(a: np.ndarray, b: np.ndarray, n: int = 4000) -> tuple[float, float]:
    rng = np.random.default_rng(1)
    d = [a[rng.integers(0, a.size, a.size)].mean() - b[rng.integers(0, b.size, b.size)].mean() for _ in range(n)]
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def linea(nom: str, r: np.ndarray) -> str:
    lo, hi = ic(r)
    return f"{nom}: {r.size} trades · WR {(r > 0).mean():.1%} · exp {r.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]"


def comparar(nom: str, a: np.ndarray, b: np.ndarray) -> str:
    lo, hi = ic_dif(a, b)
    return f"{nom}: {a.mean():+.3f} (n {a.size}) vs {b.mean():+.3f} (n {b.size}) · dif {a.mean() - b.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]"


def main() -> None:
    t = pl.read_parquet(RAIZ / "reports" / "b" / "trades_b1_va_2022-01_2022-12_rmin2_patas1_be0.5.parquet")
    t = b_variables.agregar(t, "2022-01", "2022-12")
    t = t.with_columns(minu=(pl.col("t_senal") // 60_000) % 1440)
    t = t.with_columns(tramo=(pl.col("minu") // 240).clip(0, 3), pocos=pl.col("cruces_vwap_dia") <= CORTE_CRUCES)
    r = lambda x: x["r"].to_numpy()  # noqa: E731
    l = ["VALIDACIÓN 2022 · B1 dVAL/dVAH · R ≥ 2 · breakeven 0,5 R (pre-registrada)", linea("H0 total 2022", r(t))]
    l.append("motivos: " + ", ".join(f"{m} {n}" for m, n in t.group_by("motivo").len().sort("len", descending=True).rows()))
    l.append(comparar("H1 cruces ≤ 16 vs > 16", r(t.filter(pl.col("pocos"))), r(t.filter(~pl.col("pocos")))))
    nom_t = {0: "0–4 h", 1: "4–8 h", 2: "8–12 h", 3: "12 h+"}
    for k in range(4):
        x = t.filter(pl.col("tramo") == k)
        a, b = r(x.filter(pl.col("pocos"))), r(x.filter(~pl.col("pocos")))
        if a.size >= 30 and b.size >= 30:
            l.append("   " + comparar(f"tramo {nom_t[k]}", a, b))
        else:
            l.append(f"   tramo {nom_t[k]}: muestra chica (pocos {a.size}, muchos {b.size})")
    asia = pl.col("minu") < 240
    l.append(comparar("H2 00:30–04:00 UTC vs resto", r(t.filter(asia)), r(t.filter(~asia))))
    l.append("por trimestre (H0 y H2):")
    t = t.with_columns(q=pl.from_epoch("t_senal", time_unit="ms").dt.quarter())
    for q in range(1, 5):
        x = t.filter(pl.col("q") == q)
        l.append(f"   2022Q{q}: total {x['r'].mean():+.3f} (n {x.height}) · 0–4 h {x.filter(asia)['r'].mean():+.3f} · resto {x.filter(~asia)['r'].mean():+.3f}")
    txt = "\n".join(l)
    print(txt)
    (RAIZ / "reports" / "b" / "validacion_2022.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
