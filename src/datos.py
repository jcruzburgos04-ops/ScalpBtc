"""Lectura de los parquet de data/proc/ (ver f0_descarga.py para el origen de cada uno)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl

PROC = Path(__file__).resolve().parent.parent / "data" / "proc"
ESCALA_P = 10
ESCALA_Q = 1000


def _ini_mes_s(mes: str) -> int:
    return int(dt.datetime.fromisoformat(mes + "-01").replace(tzinfo=dt.timezone.utc).timestamp())


def leer_1s(mes: str) -> pl.DataFrame:
    """Decodifica bars_1s/AAAA-MM.parquet → ts (ms UTC), o/h/l/c (USDT), v/vb (BTC), n_agg, n_trades, ms_first, ms_last."""
    e = pl.read_parquet(PROC / "bars_1s" / f"{mes}.parquet")
    s = e["dt"].cast(pl.Int64).cum_sum() + _ini_mes_s(mes)
    # o_i = do_i + c_{i-1} y c_i = o_i + dc_i  →  o_i = cumsum(do) + cumsum(dc) desplazado una fila
    o = e["do"].cast(pl.Int64).cum_sum() + e["dc"].cast(pl.Int64).cum_sum().shift(1, fill_value=0)
    return pl.DataFrame({
        "ts": s * 1000,
        "o": o / ESCALA_P,
        "h": (o + e["dh"]) / ESCALA_P,
        "l": (o - e["dl"]) / ESCALA_P,
        "c": (o + e["dc"]) / ESCALA_P,
        "v": e["v"] / ESCALA_Q,
        "vb": e["vb"] / ESCALA_Q,
        "n_agg": e["n_agg"],
        "n_trades": e["n_agg"] + e["ntx"],
        "ms_first": e["ms_first"],
        "ms_last": e["ms_last"],
    })


def leer(carpeta: str, desde: str | None = None, hasta: str | None = None) -> pl.DataFrame:
    """Concatena los meses [desde, hasta] (AAAA-MM) de una carpeta de data/proc/ (no bars_1s)."""
    archivos = sorted((PROC / carpeta).glob("*.parquet"))
    archivos = [a for a in archivos if (desde is None or a.stem >= desde) and (hasta is None or a.stem <= hasta)]
    return pl.concat([pl.read_parquet(a) for a in archivos])
