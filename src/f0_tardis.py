"""F0 · Liquidaciones reales de BTCUSDT USD-M desde Tardis.dev (gratis: solo el 1.er día de cada mes).

Fuente: https://datasets.tardis.dev/v1/binance-futures/liquidations/AAAA/MM/01/BTCUSDT.csv.gz (sin API key).
Origen de los datos: stream forceOrder de Binance, que publica como mucho una liquidación por símbolo cada
1000 ms: es una MUESTRA real, no el total.

Salida: data/proc/liq_tardis/AAAA-MM-01.parquet  (timestamp y local_timestamp en ms UTC, side, price, amount)
Uso:    python src/f0_tardis.py 2022-01 2026-09
"""
from __future__ import annotations

import argparse
import gzip
import io
import time
from pathlib import Path

import polars as pl
import requests

from f0_descarga import meses

URL = "https://datasets.tardis.dev/v1/binance-futures/liquidations/{a}/{m}/01/BTCUSDT.csv.gz"
PROC = Path(__file__).resolve().parent.parent / "data" / "proc" / "liq_tardis"


def bajar(mes: str) -> pl.DataFrame | None:
    a, m = mes.split("-")
    for i in range(5):
        try:
            r = requests.get(URL.format(a=a, m=m), timeout=120)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if i == 4:
                raise
            print(f"  reintento {i + 1} {mes}: {e}")
            time.sleep(2 ** (i + 1))
    df = pl.read_csv(io.BytesIO(gzip.decompress(r.content)))
    # Tardis da timestamps en microsegundos; internamente todo va en ms
    return df.select(
        timestamp=(pl.col("timestamp") // 1000).cast(pl.Int64),
        local_timestamp=(pl.col("local_timestamp") // 1000).cast(pl.Int64),
        id=pl.col("id").cast(pl.Utf8), side=pl.col("side"),
        price=pl.col("price").cast(pl.Float64), amount=pl.col("amount").cast(pl.Float64),
    ).sort("timestamp")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("desde")
    ap.add_argument("hasta")
    args = ap.parse_args()
    PROC.mkdir(parents=True, exist_ok=True)
    for mes in meses(args.desde, args.hasta):
        df = bajar(mes)
        if df is None:
            print(f"{mes}-01: sin datos")
            continue
        df.write_parquet(PROC / f"{mes}-01.parquet", compression="zstd", compression_level=19)
        print(f"{mes}-01: {df.height} liquidaciones, {df['amount'].sum():.1f} BTC")


if __name__ == "__main__":
    main()
