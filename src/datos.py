"""Lectura de los parquet de data/proc/ (ver f0_descarga.py para el origen de cada uno)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.compute as pc

PROC = Path(__file__).resolve().parent.parent / "data" / "proc"
ESCALA_P = 100
ESCALA_Q = 1000


def _div(s: pl.Series, k: int) -> pl.Series:
    """Entero / k con redondeo IEEE correcto (polars multiplica por el recíproco y deja errores de 1 ulp,
    así 4628920/100 no da el mismo double que el close 46289.2 de las klines)."""
    return pl.from_arrow(pc.divide(s.cast(pl.Float64).to_arrow(), pa.scalar(float(k))))


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
        "o": _div(o, ESCALA_P),
        "h": _div(o + e["dh"], ESCALA_P),
        "l": _div(o - e["dl"], ESCALA_P),
        "c": _div(o + e["dc"], ESCALA_P),
        "v": _div(e["v"], ESCALA_Q),
        "vb": _div(e["vb"], ESCALA_Q),
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
