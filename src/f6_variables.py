"""F6 · Variables de contexto de cada pata, medidas al CIERRE de la vela de señal (sin mirar hacia adelante), y el
recorrido a favor antes del SL (MFE) para estudiar el TP y el win rate.

Variables (todas "a favor del trade": positivo = favorece la dirección del trade):
  ubicación   z_vwap_d / z_vwap_w (en σ del VWAP de sesión / semana; + = el precio ya está del lado al que apunta)
  rango       cruces_ash30 (cruces Bulls/Bears del ASH 1m en 30 min), cruces_xo60
  volumen     rvol (vela de señal), rvol_max3, cvd5 / cvd15 (desequilibrio taker: (compras − ventas)/volumen, a favor)
  órdenes     grandes5 (nocional neto de órdenes grandes a mercado en 5 min, a favor / total), n_grandes5_favor
              "grande" = ≥ percentil 90 de las órdenes ≥ 100k USD del día anterior (≈ top 0,5 % de todas)
  posiciones  oi15 / oi60 (variación % del open interest; último dato con ≥ 5 min de antigüedad), pxoi15 (cuadrante
              precio/OI: +1 precio a favor y OI sube, etc.), taker_ratio (long/short taker del último 5m, a favor)
  estructura  barrida (el extremo de las últimas 3 velas superó el de las 27 anteriores en contra y el cierre volvió)
  5m          dist5m_atr, ash5_favor (brecha normalizada del ASH 5m a favor)
  régimen     atr_rel (ATR14 / mediana del ATR14 de las 24 h previas)
  niveles     obst_2r (niveles entre el fill y 2R a favor), nivel_cerca_r (distancia al nivel más cercano a favor, en R)
Resultado: r (TP 2R), mfe_r (máximo a favor antes de tocar el SL, en R, por last; tope 24 h), alcanzo_1r/1_5r/3r.
Salida: reports/f6/variables_<periodo>.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

import indicadores as ind
from datos import leer, leer_velas_1m

RAIZ = Path(__file__).resolve().parent.parent
NIVELES = ["vwap_d", "vwap_d_p1", "vwap_d_m1", "vwap_d_p2", "vwap_d_m2", "dVAH", "dVAL", "dPOC", "rVAH", "rVAL",
           "DO", "WO", "PWH", "PWL", "MNDAY_H_vivo", "MNDAY_L_vivo", "pwVWAP_vivo", "mVWAP_vivo", "r7D_vivo", "r30D_vivo"]


def por_minuto(desde: str, hasta: str) -> pl.DataFrame:
    df = ind.cargar(desde, hasta)
    k = leer_velas_1m(desde, hasta).select("open_time", "taker_buy_volume")
    df = df.join(k, on="open_time", how="left")
    d = (2 * pl.col("taker_buy_volume") - pl.col("volume"))
    df = df.with_columns(
        cvd5=d.rolling_sum(5) / pl.col("volume").rolling_sum(5),
        cvd15=d.rolling_sum(15) / pl.col("volume").rolling_sum(15),
        rvol_max3=pl.col("rvol").rolling_max(3),
        atr_rel=pl.col("atr14") / pl.col("atr14").rolling_median(1440),
        z_vwap_d=(pl.col("close") - pl.col("vwap_d")) / (pl.col("vwap_d_p1") - pl.col("vwap_d")),
        z_vwap_w=(pl.col("close") - pl.col("vwap_w")) / (pl.col("vwap_w_p1") - pl.col("vwap_w")),
        g=pl.col("ash_bulls") - pl.col("ash_bears"), x=pl.col("ema11") - pl.col("ema25"),
        gn5=(pl.col("ash_bulls_5m_vivo") - pl.col("ash_bears_5m_vivo")) / (pl.col("ash_bulls_5m_vivo") + pl.col("ash_bears_5m_vivo")),
        min3=pl.col("low").rolling_min(3), max3=pl.col("high").rolling_max(3),
        min_prev=pl.col("low").shift(3).rolling_min(27), max_prev=pl.col("high").shift(3).rolling_max(27),
    )
    cr = lambda c: ((pl.col(c) > 0) != (pl.col(c) > 0).shift(1)).cast(pl.Int32).fill_null(0)  # noqa: E731
    df = df.with_columns(cruces_ash30=cr("g").rolling_sum(30), cruces_xo60=cr("x").rolling_sum(60))
    # órdenes grandes: umbral = p90 de las órdenes ≥ 100k del día anterior
    o = leer("ordenes_grandes", desde, hasta).with_columns(
        usd=pl.col("q").cast(pl.Float64) / 1000 * pl.col("pmin").cast(pl.Float64) / 100,
        dia=pl.col("ts") // 86_400_000, open_time=pl.col("ts") // 60_000 * 60_000)
    umbral = o.group_by("dia").agg(u=pl.col("usd").quantile(0.9)).with_columns(pl.col("dia") + 1)
    o = o.join(umbral, on="dia", how="left").filter(pl.col("usd") >= pl.col("u"))
    om = o.group_by("open_time").agg(gb=pl.col("usd").filter(pl.col("buy")).sum(), gs=pl.col("usd").filter(~pl.col("buy")).sum(),
                                     nb=pl.col("buy").sum(), ns=(~pl.col("buy")).sum())
    df = df.join(om, on="open_time", how="left").with_columns(pl.col("gb", "gs", "nb", "ns").fill_null(0))
    df = df.with_columns(gb5=pl.col("gb").rolling_sum(5), gs5=pl.col("gs").rolling_sum(5),
                         nb5=pl.col("nb").rolling_sum(5), ns5=pl.col("ns").rolling_sum(5))
    # open interest: último snapshot con ≥ 5 min de antigüedad respecto del cierre de la vela
    m = leer("metrics_5m", desde, hasta).select("create_time", "sum_open_interest", "sum_taker_long_short_vol_ratio").sort("create_time")
    m = m.with_columns(oi15=pl.col("sum_open_interest") / pl.col("sum_open_interest").shift(3) - 1,
                       oi60=pl.col("sum_open_interest") / pl.col("sum_open_interest").shift(12) - 1,
                       t_disp=pl.col("create_time") + 300_000)
    df = df.with_columns(t_cierre=pl.col("open_time") + 60_000).sort("t_cierre")
    df = df.join_asof(m.select("t_disp", "oi15", "oi60", "sum_taker_long_short_vol_ratio"), left_on="t_cierre",
                      right_on="t_disp", strategy="backward")
    df = df.with_columns(px15=pl.col("close") / pl.col("close").shift(15) - 1)
    return df


def recorrido(trades: pl.DataFrame, desde: str, hasta: str) -> pl.DataFrame:
    """MFE en R antes de tocar el SL (por last, velas de 1m; dentro del minuto del SL no se cuenta lo favorable:
    criterio conservador). Tope 24 h."""
    k = leer_velas_1m(desde, hasta).sort("open_time")
    t, h, l = k["open_time"].to_numpy(), k["high"].to_numpy(), k["low"].to_numpy()
    mfe = np.full(trades.height, np.nan)
    for j, r in enumerate(trades.select("fill_ts", "fill", "sl", "lado").iter_rows()):
        fts, fill, sl, lado = r
        i0 = np.searchsorted(t, fts // 60_000 * 60_000)
        i1 = min(i0 + 1440, t.size)
        lg = lado == "long"
        toca = (l[i0:i1] <= sl) if lg else (h[i0:i1] >= sl)
        k_sl = int(np.argmax(toca)) if toca.any() else i1 - i0
        fav = (h[i0:i0 + k_sl] - fill) if lg else (fill - l[i0:i0 + k_sl])
        mfe[j] = max(0.0, float(fav.max())) / abs(fill - sl) if fav.size else 0.0
    return trades.with_columns(mfe_r=pl.Series(mfe))


def armar(archivo: str, desde: str, hasta: str) -> pl.DataFrame:
    tr = pl.read_parquet(RAIZ / "reports" / "f3" / f"{archivo}.parquet")
    pm = por_minuto(desde, hasta)
    cols = ["open_time", "close", "z_vwap_d", "z_vwap_w", "cruces_ash30", "cruces_xo60", "rvol", "rvol_max3", "cvd5", "cvd15",
            "gb5", "gs5", "nb5", "ns5", "oi15", "oi60", "px15", "sum_taker_long_short_vol_ratio", "gn5", "atr_rel",
            "min3", "max3", "min_prev", "max_prev", "low", "high"] + NIVELES
    x = tr.join(pm.select(cols).rename({"open_time": "t_senal", "close": "c_senal"}), on="t_senal", how="left")
    s = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    x = x.with_columns(
        z_vwap_d=s * pl.col("z_vwap_d"), z_vwap_w=s * pl.col("z_vwap_w"),
        cvd5=s * pl.col("cvd5"), cvd15=s * pl.col("cvd15"),
        grandes5=s * (pl.col("gb5") - pl.col("gs5")) / (pl.col("gb5") + pl.col("gs5")),
        n_grandes5_favor=pl.when(pl.col("lado") == "long").then(pl.col("nb5")).otherwise(pl.col("ns5")),
        n_grandes5_contra=pl.when(pl.col("lado") == "long").then(pl.col("ns5")).otherwise(pl.col("nb5")),
        oi15=pl.col("oi15") * 100, oi60=pl.col("oi60") * 100,
        pxoi15=(s * pl.col("px15")).sign() * pl.col("oi15").sign(),
        taker_ratio=pl.when(pl.col("lado") == "long").then(pl.col("sum_taker_long_short_vol_ratio"))
        .otherwise(1 / pl.col("sum_taker_long_short_vol_ratio")),
        ash5_favor=s * pl.col("gn5"),
        barrida=pl.when(pl.col("lado") == "long").then((pl.col("min3") < pl.col("min_prev")) & (pl.col("c_senal") > pl.col("min_prev")))
        .otherwise((pl.col("max3") > pl.col("max_prev")) & (pl.col("c_senal") < pl.col("max_prev"))),
    )
    # niveles a favor entre el fill y 2R, y distancia al más cercano a favor
    lv = np.stack([x[c].to_numpy() for c in NIVELES], axis=1)
    fill, risk = x["fill"].to_numpy(), x["riesgo"].to_numpy()
    sg = np.where(x["lado"].to_numpy() == "long", 1.0, -1.0)
    d = (lv - fill[:, None]) * sg[:, None] / risk[:, None]  # distancia en R, + = a favor
    d = np.where(np.isnan(d), np.inf, d)
    x = x.with_columns(obst_2r=pl.Series(((d > 0.05) & (d < 2)).sum(1)),
                       nivel_cerca_r=pl.Series(np.where(np.isinf(np.min(np.where(d > 0.05, d, np.inf), 1)), np.nan,
                                                        np.min(np.where(d > 0.05, d, np.inf), 1))))
    x = recorrido(x, desde, hasta)
    x = x.with_columns(alcanzo_1r=pl.col("mfe_r") >= 1, alcanzo_1_5r=pl.col("mfe_r") >= 1.5, alcanzo_3r=pl.col("mfe_r") >= 3)
    return x.drop(["gb5", "gs5", "nb5", "ns5", "min3", "max3", "min_prev", "max_prev", "low", "high", "gn5", "px15",
                   "sum_taker_long_short_vol_ratio"] + NIVELES)


if __name__ == "__main__":
    out = RAIZ / "reports" / "f6"
    out.mkdir(parents=True, exist_ok=True)
    for arch, d, h, nom in [("trades_2023-01_2024-12_tp2_slip0_sllast", "2023-01", "2024-12", "2023_2024"),
                            ("trades_2025-01_2026-06_tp2_slip0_sllast", "2025-01", "2026-06", "2025_2026")]:
        v = armar(arch, d, h)
        v.write_parquet(out / f"variables_{nom}.parquet")
        print(nom, v.height, "patas;", "nulos por columna:", {c: v[c].null_count() for c in ("cvd5", "oi15", "grandes5", "atr_rel") })
