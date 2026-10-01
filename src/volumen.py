"""Indicadores de volumen por minuto, medidos al CIERRE de cada vela de 1m (sin mirar hacia adelante), para estudiar
qué veía el trader en su volume suite, el CVD y las velas de segundos ("ampliaciones" de TradingView: 10s/15s/30s).

Todo en convención "comprador +" (se le cambia el signo para los shorts al compararlo con un trade):
  delta1        (compras − ventas taker) / volumen de la vela de 1m
  cvd5, cvd15   ídem acumulado 5 / 15 min (de f6_variables)
  vol15_rel     volumen de los últimos 15 min / mediana de los bloques de 15 min de las 24 h previas
  absorcion5    esfuerzo / resultado de las últimas 5 velas: (volumen relativo) / (rango / ATR)
  pico10s       máximo volumen de una vela de 10 s en el último minuto / mediana de las velas de 10 s de la hora previa
  delta60s      delta de los últimos 60 s; delta10s: de los últimos 10 s
  n_burbujas_*  órdenes grandes a mercado (percentil 90 de las ≥ 100k USD del día previo) en 5 / 15 min, compras y ventas
  oi15, oi60    variación del open interest (último dato publicado)
"""
from __future__ import annotations

import polars as pl

import f6_variables as f6
from datos import leer_1s


def segundos(meses: list[str]) -> pl.DataFrame:
    """Rasgos de velas de 10 s agregados al minuto."""
    b = pl.concat([leer_1s(m) for m in meses]).sort("ts")
    d = (b.group_by((pl.col("ts") // 10_000 * 10_000).alias("t10"))
         .agg(v=pl.col("v").sum(), vb=pl.col("vb").sum()).sort("t10"))
    d = d.with_columns(med=pl.col("v").rolling_median(360).shift(1)).with_columns(
        open_time=pl.col("t10") // 60_000 * 60_000)
    return (d.group_by("open_time").agg(
        pico10s=(pl.col("v") / pl.col("med")).max(),
        delta60s=(2 * pl.col("vb").sum() - pl.col("v").sum()) / pl.col("v").sum(),
        delta10s=((2 * pl.col("vb") - pl.col("v")) / pl.col("v")).last()).sort("open_time"))


def agregar(df: pl.DataFrame, desde: str, hasta: str, con_segundos: bool = True) -> pl.DataFrame:
    """Suma los rasgos de volumen a un DataFrame por minuto que ya viene de f6_variables.por_minuto."""
    meses = pl.date_range(pl.date(int(desde[:4]), int(desde[5:]), 1), pl.date(int(hasta[:4]), int(hasta[5:]), 1),
                          "1mo", eager=True).dt.strftime("%Y-%m").to_list()
    df = df.sort("open_time")
    if con_segundos:
        df = df.join(segundos(meses), on="open_time", how="left")
    v15 = pl.col("volume").rolling_sum(15)
    v5 = pl.col("volume").rolling_sum(5)
    df = df.with_columns(
        delta1=(2 * pl.col("taker_buy_volume") - pl.col("volume")) / pl.col("volume"),
        vol15_rel=v15 / v15.rolling_median(1440).shift(15),
        rango5=(pl.col("high").rolling_max(5) - pl.col("low").rolling_min(5)) / pl.col("atr14"),
        vol5_rel=v5 / v5.rolling_median(1440).shift(5),
        nb15=pl.col("nb").rolling_sum(15), ns15=pl.col("ns").rolling_sum(15),
    ).with_columns(absorcion5=pl.col("vol5_rel") / pl.max_horizontal(pl.col("rango5"), pl.lit(0.25)))
    return df


def por_minuto(desde: str, hasta: str) -> pl.DataFrame:
    return agregar(f6.por_minuto(desde, hasta), desde, hasta)
