"""Métricas del backtest 2020-01 → 2026-09 (A congelada y Trendlines + agresión) y página HTML.

Convenciones:
- Cada pata arriesga 1 % del capital; R de la pata = resultado / riesgo (la toma parcial ya está dentro del R).
- "Riesgo fijo": 1 % del capital INICIAL por pata, sin interés compuesto → retorno % = R × 1.
- "Compuesto": 1 % del capital vigente al cerrar cada pata (aproximación: las patas abiertas a la vez se dimensionan
  con el capital de su cierre, no el de su entrada).
- Retornos diarios = suma de los R cerrados ese día UTC (días sin trades = 0, 365 días por año: cripto opera 24/7).
  Sharpe = media / desvío × √365 (tasa libre de riesgo 0). Sortino = media / desvío a la baja × √365.
- Drawdown sobre la curva de patas cerradas (no incluye la pérdida flotante de las patas abiertas).
Salida: reports/backtest_2020/metricas.json, reports/backtest_2020/backtest_2020.html
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import polars as pl

from datos import leer_velas_1m

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "backtest_2020"
PLANTILLA = RAIZ / "src" / "plantillas" / "backtest_2020.html"
NOMBRES = {"A": "A congelada", "TL": "Trendlines + agresión"}
LIMPIO = 2022   # 2020–2022 no se usó para elegir nada; 2023+ sí (calibración, test, ideas del trader)
DIA = 86_400_000


def ic_pos(t: pl.DataFrame, n=2000):
    pos = t.group_by("pos_id").agg(pl.col("r").sum(), pl.len())
    rp, k = pos["r"].to_numpy(), pos["len"].to_numpy()
    rng = np.random.default_rng(0)
    bs = [rp[i].sum() / k[i].sum() for i in (rng.integers(0, rp.size, rp.size) for _ in range(n))]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def dd(curva: np.ndarray):
    pico = np.maximum.accumulate(np.r_[0.0, curva])[1:]
    return curva - pico


def racha(r: np.ndarray) -> int:
    m = c = 0
    for x in r:
        c = c + 1 if x < 0 else 0
        m = max(m, c)
    return m


def metricas(t: pl.DataFrame, d0: int, d1: int) -> dict:
    t = t.sort("salida_ts")
    r = t["r"].to_numpy()
    dias = np.arange(d0, d1 + 1)
    por_dia = t.group_by(dia=pl.col("salida_ts") // DIA).agg(pl.col("r").sum())
    diario = np.zeros(dias.size)
    idx = np.searchsorted(dias, por_dia["dia"].to_numpy())
    ok = (idx >= 0) & (idx < dias.size)
    np.add.at(diario, idx[ok], por_dia["r"].to_numpy()[ok])
    cum = np.cumsum(r)
    ddr = dd(cum)
    # compuesto por pata
    eq = np.cumprod(1 + 0.01 * r)
    dd_c = eq / np.maximum.accumulate(np.r_[1.0, eq])[1:] - 1
    anios = dias.size / 365.0
    # duración del peor drawdown (días entre el pico y la recuperación, sobre la curva diaria)
    cd = np.cumsum(diario)
    pico_d = np.maximum.accumulate(np.r_[0.0, cd])[1:]
    bajo = cd < pico_d - 1e-9
    larga = cur = 0
    for b in bajo:
        cur = cur + 1 if b else 0
        larga = max(larga, cur)
    abajo = np.minimum(diario, 0)
    lo, hi = ic_pos(t)
    gan, per = r[r > 0], r[r < 0]
    sharpe = float(diario.mean() / diario.std() * np.sqrt(365)) if diario.std() > 0 else 0.0
    sortino = float(diario.mean() / np.sqrt((abajo ** 2).mean()) * np.sqrt(365)) if (abajo < 0).any() else 0.0
    ret_anual = float(cum[-1] / anios) if r.size else 0.0
    mot = t["motivo"].value_counts()
    motivos = {m: int(c) for m, c in mot.iter_rows()}
    return {
        "patas": int(r.size), "posiciones": int(t["pos_id"].n_unique()), "dias": int(dias.size),
        "patas_por_dia": r.size / dias.size, "gana": float((r > 0).mean()),
        "tp": motivos.get("TP", 0) / r.size, "be": motivos.get("breakeven", 0) / r.size, "sl": motivos.get("SL", 0) / r.size,
        "r_medio": float(r.mean()), "ic": [lo, hi], "pf": float(gan.sum() / -per.sum()) if per.size else None,
        "r_gana": float(gan.mean()) if gan.size else 0.0, "r_pierde": float(per.mean()) if per.size else 0.0,
        "r_total": float(cum[-1]), "ret_fijo_pct": float(cum[-1]), "ret_anual_pct": ret_anual,
        "dd_r": float(ddr.min()), "dd_dias": int(larga), "calmar": ret_anual / -float(ddr.min()) if ddr.min() < 0 else None,
        "sharpe": sharpe, "sortino": sortino, "racha": racha(r),
        "peor_dia_pct": float(diario.min()), "mejor_dia_pct": float(diario.max()),
        "cagr_comp": float(eq[-1] ** (1 / anios) - 1) if r.size else 0.0, "mult_comp": float(eq[-1]),
        "dd_comp_pct": float(dd_c.min() * 100),
        "pos_4_sl": int(t.filter(pl.col("motivo") == "SL").group_by("pos_id").len().filter(pl.col("len") >= 4).height),
    }


def main() -> None:
    k = leer_velas_1m("2020-01", "2026-09").select("open_time", "close").sort("open_time")
    d0, d1 = int(k["open_time"][0] // DIA), int(k["open_time"][-1] // DIA)
    btc = k.with_columns(anio=pl.from_epoch("open_time", time_unit="ms").dt.year()).group_by("anio").agg(
        a=pl.col("close").first(), b=pl.col("close").last()).sort("anio")
    btc_anio = {int(a): float(b / a0 - 1) for a, a0, b in btc.select("anio", "a", "b").iter_rows()}

    out = {"generado": f"{dt.date.today():%Y-%m-%d}", "desde": "2020-01-01", "hasta": "2026-09-30",
           "btc_anio": btc_anio, "estrategias": {}}
    for cod, nom in NOMBRES.items():
        f = OUT / f"trades_{cod}.parquet"
        if not f.exists():
            continue
        t = pl.read_parquet(f).with_columns(anio=pl.from_epoch("fill_ts", time_unit="ms").dt.year())
        e = {"nombre": nom, "total": metricas(t, d0, d1)}
        lim = int(dt.datetime(LIMPIO + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000) // DIA
        e["limpio"] = metricas(t.filter(pl.col("anio") <= LIMPIO), d0, lim - 1)
        e["usado"] = metricas(t.filter(pl.col("anio") > LIMPIO), lim, d1)
        e["anios"] = {}
        for a in sorted(t["anio"].unique().to_list()):
            a0 = max(d0, int(dt.datetime(a, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000) // DIA)
            a1 = min(d1, int(dt.datetime(a + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000) // DIA - 1)
            e["anios"][str(a)] = metricas(t.filter(pl.col("anio") == a), a0, a1)
        # serie diaria acumulada (riesgo fijo, % del capital inicial) y drawdown
        por_dia = t.group_by(dia=pl.col("salida_ts") // DIA).agg(pl.col("r").sum())
        diario = np.zeros(d1 - d0 + 1)
        idx = por_dia["dia"].to_numpy() - d0
        ok = (idx >= 0) & (idx < diario.size)
        np.add.at(diario, idx[ok], por_dia["r"].to_numpy()[ok])
        cum = np.cumsum(diario)
        e["curva"] = [round(float(x), 2) for x in cum]
        e["dd"] = [round(float(x), 2) for x in dd(cum)]
        # mensual (%, riesgo fijo)
        m = t.with_columns(mes=pl.from_epoch("salida_ts", time_unit="ms").dt.strftime("%Y-%m")).group_by("mes").agg(
            pl.col("r").sum(), pl.len()).sort("mes")
        e["mensual"] = {a: [round(float(b), 2), int(n)] for a, b, n in m.select("mes", "r", "len").iter_rows()}
        # distribución de R por pata
        e["dist_r"] = {str(round(v, 2)): int(c) for v, c in t.group_by(pl.col("r").round(2)).len().sort("r").iter_rows()}
        out["estrategias"][cod] = e
    out["dia0"] = d0
    (OUT / "metricas.json").write_text(json.dumps(out, ensure_ascii=False))
    html = PLANTILLA.read_text().replace("/*__DATOS__*/null", json.dumps(out, ensure_ascii=False))
    (OUT / "backtest_2020.html").write_text(html)
    for cod, e in out["estrategias"].items():
        x = e["total"]
        print(cod, f"patas {x['patas']} gana {x['gana']:.0%} R {x['r_medio']:+.3f} {x['ic']} total {x['r_total']:.0f}R "
              f"anual {x['ret_anual_pct']:.0f}% sharpe {x['sharpe']:.2f} sortino {x['sortino']:.2f} dd {x['dd_r']:.1f}R "
              f"({x['dd_dias']} d) calmar {x['calmar']} pf {x['pf']:.2f} racha {x['racha']} comp x{x['mult_comp']:.3g} dd_comp {x['dd_comp_pct']:.1f}%")
        for a, y in e["anios"].items():
            print("  ", a, f"{y['patas']} {y['gana']:.0%} {y['r_medio']:+.3f} total {y['r_total']:.0f}R dd {y['dd_r']:.1f} sharpe {y['sharpe']:.2f}")


if __name__ == "__main__":
    main()
