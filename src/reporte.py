"""Reporte estándar de cada test (CLAUDE.md §9). Unidades: R por pata; IC por bootstrap POR BLOQUES DE POSICIÓN (§4.3).

Uso: python src/reporte.py <archivo de trades sin .parquet> [<otro> ...]  → imprime y guarda reports/f3/reporte_*.md
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parent.parent
NY = "America/New_York"


def subsesion(df: pl.DataFrame) -> pl.DataFrame:
    """Asia 00:00–07:00 UTC · Londres 07:00 UTC → 09:30 NY · NY 09:30 → 12:00 NY (hora de la señal)."""
    u = pl.from_epoch("t_senal", time_unit="ms").dt.replace_time_zone("UTC")
    ny = u.dt.convert_time_zone(NY)
    mins_ny = ny.dt.hour().cast(pl.Int32) * 60 + ny.dt.minute().cast(pl.Int32)  # hour() es Int8: sin cast desborda
    return df.with_columns(
        subsesion=pl.when(u.dt.hour() < 7).then(pl.lit("Asia"))
        .when(mins_ny < 9 * 60 + 30).then(pl.lit("Londres")).otherwise(pl.lit("NY")),
        dia_sem=u.dt.weekday(), mes=u.dt.strftime("%Y-%m"), anio=u.dt.year(), fecha=u.dt.date())


def boot_ic(t: pl.DataFrame, col: str = "r", n: int = 2000, semilla: int = 0) -> tuple[float, float]:
    """IC 95 % de la expectativa por pata, remuestreando POSICIONES enteras (las patas de una posición no son independientes)."""
    g = t.group_by("pos_id").agg(s=pl.col(col).sum(), k=pl.len())
    s, k = g["s"].to_numpy(), g["k"].to_numpy()
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, s.size, size=(n, s.size))
    est = s[idx].sum(1) / k[idx].sum(1)
    return float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def metricas(t: pl.DataFrame, col: str = "r") -> dict:
    r = t.sort("salida_ts")[col].to_numpy()
    if r.size == 0:
        return {}
    gan, per = r[r > 0], r[r <= 0]
    curva = np.cumsum(r)
    dd = float((np.maximum.accumulate(np.concatenate([[0], curva]))[1:] - curva).max())
    racha = mx = 0
    for x in r:
        racha = racha + 1 if x <= 0 else 0
        mx = max(mx, racha)
    lo, hi = boot_ic(t, col)
    dias = t["fecha"].n_unique() if "fecha" in t.columns else np.nan
    return {"n": r.size, "posiciones": t["pos_id"].n_unique(), "win_rate": float((r > 0).mean()),
            "expectativa_R": float(r.mean()), "ic95": (lo, hi),
            "profit_factor": float(gan.sum() / -per.sum()) if per.sum() < 0 else np.inf,
            "R_medio_ganador": float(gan.mean()) if gan.size else np.nan, "R_medio_perdedor": float(per.mean()) if per.size else np.nan,
            "total_R": float(r.sum()), "max_dd_R": dd, "racha_perdedora": mx, "patas_por_dia": r.size / dias,
            "ambiguos": int(t["ambiguo"].sum())}


def fila(nombre: str, m: dict) -> str:
    return (f"| {nombre} | {m['n']} | {m['posiciones']} | {m['win_rate']:.1%} | {m['expectativa_R']:+.3f} | "
            f"[{m['ic95'][0]:+.3f}, {m['ic95'][1]:+.3f}] | {m['profit_factor']:.2f} | {m['R_medio_ganador']:+.2f} / "
            f"{m['R_medio_perdedor']:+.2f} | {m['total_R']:+.0f} | {m['max_dd_R']:.0f} | {m['racha_perdedora']} | "
            f"{m['patas_por_dia']:.1f} |")


CAB = ("| Grupo | Patas | Posiciones | Win rate | Expectativa (R) | IC 95 % | PF | R gan. / perd. | Total R | Máx. DD (R) | "
       "Racha perd. | Patas/día |\n|---|---|---|---|---|---|---|---|---|---|---|---|")


def reporte(nombre: str) -> str:
    t = subsesion(pl.read_parquet(RAIZ / "reports" / "f3" / f"{nombre}.parquet"))
    l = [f"### {nombre}", "", CAB, fila("Total", metricas(t))]
    for g in ("anio", "subsesion", "tipo", "lado"):
        for v in sorted(t[g].unique().to_list()):
            l.append(fila(f"{g} = {v}", metricas(t.filter(pl.col(g) == v))))
    p1 = t.filter(pl.col("pata") == 1)
    l.append(fila("solo patas 1 (sin ampliaciones)", metricas(p1)))
    l.append(fila("fin de semana", metricas(t.filter(pl.col("dia_sem") >= 6))))
    l.append(fila("lunes a viernes", metricas(t.filter(pl.col("dia_sem") <= 5))))
    l.append("")
    l.append("Motivos de salida: " + ", ".join(f"{d['motivo']} {d['len']}" for d in t.group_by("motivo").len().sort("motivo").to_dicts()))
    return "\n".join(l)


if __name__ == "__main__":
    salida = [reporte(n) for n in sys.argv[1:]]
    txt = "\n\n".join(salida)
    print(txt)
    (RAIZ / "reports" / "f3" / "reporte_base_tp2.md").write_text(
        "# Estrategia A · señal base, SL ext10 ± 0,25 ATR, TP provisorio 2R, SL por last, sin comisiones\n\n" + txt + "\n")
