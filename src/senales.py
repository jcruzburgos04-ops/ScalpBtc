"""F2 · Señales de Juan (CLAUDE.md §7), versión para calibrar.

Long (short = espejo), evaluado al cierre de cada vela de 1m, sin mirar hacia adelante:
  1. ASH 1m "próximo a ponerse verde": todavía rojo (Bulls < Bears), la brecha normalizada
     gn = (Bulls − Bears) / (Bulls + Bears) está entre −A y 0, y se viene cerrando (gn sube respecto de la vela previa).
  2. Precio por encima de las dos XO, y XO "por cruzarse al alza": EMA11 < EMA25 con
     xg = (EMA11 − EMA25) / ATR14 entre −B y 0, y cerrándose.
  3. 5m (vela en formación, §3.3): se etiqueta continuación / rebote por la distancia del precio a las EMAs de 5m
     en ATR de 5m y el estado del ASH de 5m. Solo etiqueta: no filtra.
La señal es la PRIMERA vela en que 1 y 2 se cumplen juntas (no se repite mientras sigan cumpliéndose).
Solo dentro de la ventana operativa (00:00 UTC → 12:00 America/New_York).

A y B arrancan amplios (A_MAX, B_MAX) para la revisión de Juan; con sus respuestas se eligen los definitivos.
"""
from __future__ import annotations

import numpy as np
import polars as pl

import indicadores as ind

A_MAX = 0.5   # |gn| máximo del ASH para la revisión
B_MAX = 1.0   # |xg| máximo de las XO (en ATR) para la revisión
C_CONT = 1.0  # continuación si el precio está a ≤ C ATR de 5m de las dos EMAs de 5m


def ventana_operativa(t_ms: pl.Expr) -> pl.Expr:
    """00:00 UTC → 12:00 America/New_York del mismo día UTC (convierte con la zona, nunca con offset fijo)."""
    u = pl.from_epoch(t_ms, time_unit="ms").dt.replace_time_zone("UTC")
    fin = (u.dt.date().cast(pl.Datetime("us")).dt.replace_time_zone("America/New_York")
           + pl.duration(hours=12)).dt.convert_time_zone("UTC")
    return u < fin


def atr_5m(df: pl.DataFrame) -> np.ndarray:
    """ATR(14) de velas de 5m cerradas, llevado a cada vela de 1m (última de 5m cerrada)."""
    t = df["open_time"].to_numpy()
    b = t // (5 * ind.MS_MIN)
    v5 = (df.with_columns(b=pl.Series(b)).group_by("b", maintain_order=True)
          .agg(h=pl.col("high").max(), l=pl.col("low").min(), c=pl.col("close").last()))
    a5 = ind.atr(v5["h"].to_numpy(), v5["l"].to_numpy(), v5["c"].to_numpy())
    idx = np.searchsorted(v5["b"].to_numpy(), b) - 1  # vela de 5m anterior a la que está en formación
    return np.where(idx >= 0, a5[np.maximum(idx, 0)], np.nan)


def calcular(desde: str = "2023-01", hasta: str = "2024-12", a: float = A_MAX, b: float = B_MAX) -> pl.DataFrame:
    df = ind.cargar(desde, hasta)
    df = df.with_columns(atr5m=pl.Series(atr_5m(df)))
    gn = (pl.col("ash_bulls") - pl.col("ash_bears")) / (pl.col("ash_bulls") + pl.col("ash_bears"))
    xg = (pl.col("ema11") - pl.col("ema25")) / pl.col("atr14")
    df = df.with_columns(gn=gn, xg=xg).with_columns(dgn=pl.col("gn").diff(), dxg=pl.col("xg").diff())
    hi_xo = pl.max_horizontal("ema11", "ema25")
    lo_xo = pl.min_horizontal("ema11", "ema25")
    c_long = ((pl.col("gn") < 0) & (pl.col("gn") >= -a) & (pl.col("dgn") > 0)
              & (pl.col("close") > hi_xo) & (pl.col("xg") < 0) & (pl.col("xg") >= -b) & (pl.col("dxg") > 0))
    c_short = ((pl.col("gn") > 0) & (pl.col("gn") <= a) & (pl.col("dgn") < 0)
               & (pl.col("close") < lo_xo) & (pl.col("xg") > 0) & (pl.col("xg") <= b) & (pl.col("dxg") < 0))
    df = df.with_columns(c_long=c_long.fill_null(False), c_short=c_short.fill_null(False))
    df = df.with_columns(
        sig_long=pl.col("c_long") & ~pl.col("c_long").shift(1, fill_value=False),
        sig_short=pl.col("c_short") & ~pl.col("c_short").shift(1, fill_value=False),
        en_ventana=ventana_operativa(pl.col("open_time")),
    )
    s = df.filter((pl.col("sig_long") | pl.col("sig_short")) & pl.col("en_ventana"))
    # 5m: distancia del precio a las EMAs de 5m (vela en formación) en ATR de 5m, y brecha del ASH de 5m
    d5 = pl.max_horizontal((pl.col("close") - pl.col("ema11_5m_vivo")).abs(),
                           (pl.col("close") - pl.col("ema25_5m_vivo")).abs()) / pl.col("atr5m")
    gn5 = (pl.col("ash_bulls_5m_vivo") - pl.col("ash_bears_5m_vivo")) / (pl.col("ash_bulls_5m_vivo") + pl.col("ash_bears_5m_vivo"))
    s = s.with_columns(lado=pl.when(pl.col("sig_long")).then(pl.lit("long")).otherwise(pl.lit("short")),
                       dist5m_atr=d5, gn5=gn5)
    s = s.with_columns(tipo=pl.when(pl.col("dist5m_atr") <= C_CONT).then(pl.lit("continuacion")).otherwise(pl.lit("rebote")))
    return s


if __name__ == "__main__":
    s = calcular()
    print(s.height, "señales 2023–2024 con umbrales amplios")
    print(s.group_by("lado", "tipo").len().sort("lado", "tipo"))
    print(s.select(pl.col("gn").abs().quantile(q).alias(f"|gn| q{q}") for q in (0.25, 0.5, 0.75)))
    print(s.select(pl.col("xg").abs().quantile(q).alias(f"|xg| q{q}") for q in (0.25, 0.5, 0.75)))
