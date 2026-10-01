"""Estrategia B · variables de orderflow y contexto de cada señal, medidas al cierre de la vela de señal.

  esfuerzo        volumen agresivo EN la dirección del empujón (para un short: compras taker) desde el inicio del
                  empujón hasta la vela anterior a la señal, en "minutos de volumen normal" (÷ volumen medio por minuto
                  de los 60 min previos al empujón)
  resultado       avance del empujón: |extremo − open de la primera vela del empujón| / ATR(14)
  absorcion       esfuerzo / max(resultado, 0,1): mucho volumen agresivo y poco avance = "high effort, unrewarded"
  delta_empujon   (agresivo a favor del empujón − agresivo en contra) / volumen, durante el empujón
  cruces_vwap_dia cantidad de veces que los cierres de 1m cruzaron el VWAP de sesión desde 00:00 UTC (meta rotacional)
  rango_dia_atr   (máximo − mínimo de la sesión hasta la señal) / ATR(14)
  r_tp            distancia del fill al TP (la media), en R
"""
from __future__ import annotations

import numpy as np
import polars as pl

import indicadores as ind
from datos import leer_velas_1m


def agregar(tr: pl.DataFrame, desde: str, hasta: str) -> pl.DataFrame:
    df = ind.cargar(desde, hasta).select("open_time", "open", "high", "low", "close", "volume", "vwap_d", "atr14")
    k = leer_velas_1m(desde, hasta).select("open_time", "taker_buy_volume")
    df = df.join(k, on="open_time", how="left").sort("open_time")
    t = df["open_time"].to_numpy()
    o, h, l, c, v, tb = (df[x].to_numpy() for x in ("open", "high", "low", "close", "volume", "taker_buy_volume"))
    vw, atr = df["vwap_d"].to_numpy(), df["atr14"].to_numpy()
    dia = t // 86_400_000
    lado_vw = np.sign(c - vw)
    # cruces del VWAP acumulados por día
    cambio = np.r_[0, (lado_vw[1:] != lado_vw[:-1]) & (lado_vw[1:] != 0) & (lado_vw[:-1] != 0) & (dia[1:] == dia[:-1])]
    cru = np.zeros(t.size, dtype=np.int64)
    acc = 0
    for i in range(t.size):
        if i == 0 or dia[i] != dia[i - 1]:
            acc = 0
        acc += int(cambio[i])
        cru[i] = acc
    hi_d = df.with_columns(d=pl.col("open_time") // 86_400_000).select(
        hi=pl.col("high").cum_max().over("d"), lo=pl.col("low").cum_min().over("d"))
    hi_d, lo_d = hi_d["hi"].to_numpy(), hi_d["lo"].to_numpy()
    filas = []
    for r in tr.select("t_senal", "lado", "inicio_empujon", "extremo", "fill", "tp", "riesgo").iter_rows(named=True):
        i = int(np.searchsorted(t, r["t_senal"]))
        a = int(np.searchsorted(t, r["inicio_empujon"]))
        largo = r["lado"] == "long"  # el empujón fue en contra del trade
        tramo = slice(a, max(a + 1, i))
        agr_emp = (v[tramo] - tb[tramo]).sum() if largo else tb[tramo].sum()   # long: el empujón fue vendedor
        agr_con = tb[tramo].sum() if largo else (v[tramo] - tb[tramo]).sum()
        vol_ref = np.nanmean(v[max(0, a - 60):a]) if a > 0 else np.nan
        esfuerzo = agr_emp / vol_ref if vol_ref and vol_ref > 0 else np.nan
        resultado = abs(r["extremo"] - o[a]) / atr[i] if atr[i] > 0 else np.nan
        filas.append({
            "esfuerzo": float(esfuerzo), "resultado": float(resultado),
            "absorcion": float(esfuerzo / max(resultado, 0.1)) if not np.isnan(esfuerzo) else np.nan,
            "delta_empujon": float((agr_emp - agr_con) / v[tramo].sum()) if v[tramo].sum() > 0 else np.nan,
            "cruces_vwap_dia": int(cru[i]), "rango_dia_atr": float((hi_d[i] - lo_d[i]) / atr[i]) if atr[i] > 0 else np.nan,
            "r_tp": abs(r["tp"] - r["fill"]) / r["riesgo"],
        })
    return pl.concat([tr, pl.DataFrame(filas)], how="horizontal")
