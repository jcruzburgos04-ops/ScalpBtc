"""Página de revisión de las entradas del trader (septiembre 2026): cada entrada dibujada en Binance 1m con las líneas
de su gráfico (VWAP de sesión blanco ±1σ ±2σ, VWAP semanal rojo, rolling VWAP amarillo, dVAH/dVAL, EMAs XO) y la
lectura de los indicadores al entrar. Juan confirma si la ubicación coincide con su captura.
Uso: python src/trader_sep_pagina.py  → reports/trader_sep/pagina/entradas_trader.html (+ capturas/*.jpg)"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import polars as pl

import trader_sep as ts

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trader_sep" / "pagina"
ANTES, DESPUES = 60, 30
SERIES = {"vwap": "vwap_d", "p1": "vwap_d_p1", "m1": "vwap_d_m1", "p2": "vwap_d_p2", "m2": "vwap_d_m2",
          "vw": "vwap_w", "rv": "rVWAP", "vah": "dVAH", "val": "dVAL", "e11": "ema11", "e25": "ema25"}


def r1(x):
    return None if x is None or x != x else round(float(x), 1)


def r2(x):
    return None if x is None or x != x else round(float(x), 2)


def main() -> None:
    tr = pl.read_parquet(RAIZ / "reports" / "trader_sep" / "entradas.parquet")
    df = ts.base("2026-08", "2026-09").sort("open_time")
    t = df["open_time"].to_list()
    idx = {v: i for i, v in enumerate(t)}
    casos = []
    for r in tr.sort("t_entrada", nulls_last=True).iter_rows(named=True):
        c = {k: r[k] for k in ("id", "captura", "plataforma", "lado", "entrada", "exacta", "nota", "confianza", "episodios", "dif_min",
                               "nivel1", "nivel2", "precio_vs_xo")}
        c["t"] = r["t_entrada"]
        if r["t_entrada"] is not None:
            i = idx[r["t_entrada"]]
            x = df.slice(max(0, i - ANTES), ANTES + DESPUES + 1)
            c["velas"] = [[int(a) // 1000, r1(o), r1(h), r1(l), r1(cl)] for a, o, h, l, cl in
                          x.select("open_time", "open", "high", "low", "close").iter_rows()]
            c["lineas"] = {k: [r1(v) for v in x[col].to_list()] for k, col in SERIES.items()}
            for k in ("z_vwap_d", "z_vwap_w", "dist1_atr", "dist2_atr", "ash1_gn", "ash5_gn", "rvol", "rvol_max5", "ret15_atr",
                      "ret60_atr", "cvd5", "pos_rango_dia", "atr14", "hora_utc", "oi15"):
                c[k] = r2(r[k])
            for k in ("sobre_vwap_w", "sobre_rvwap", "ash1_a_favor", "xo_a_favor", "ash5_a_favor", "barrida60"):
                c[k] = bool(r[k])
            for k in ("ash1_velas_desde_cruce", "xo_velas_desde_cruce", "niveles_05atr", "grandes5_favor", "grandes5_contra"):
                c[k] = None if r[k] is None else int(r[k])
        casos.append(c)
    resumen = json.loads((RAIZ / "reports" / "trader_sep" / "similitudes.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "capturas").mkdir(exist_ok=True)
    for f in sorted((RAIZ / "marcas" / "trader_sep2026").glob("*.jpg")):
        shutil.copy(f, OUT / "capturas" / f.name)
    html = (RAIZ / "src" / "plantillas" / "entradas_trader.html").read_text()
    html = html.replace("__CASOS__", json.dumps(casos, separators=(",", ":"), ensure_ascii=False))
    html = html.replace("__RESUMEN__", json.dumps(resumen, separators=(",", ":"), ensure_ascii=False))
    (OUT / "entradas_trader.html").write_text(html)
    print(OUT / "entradas_trader.html", len(html) // 1024, "KB,", len(casos), "casos")


if __name__ == "__main__":
    main()
