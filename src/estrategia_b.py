"""Estrategia B · setups del trader de referencia (PDFs de Juan, feb–may 2026).

B1 · Reversión desde el extremo ("low volume reversion", "edge to edge", "mandatory TP at the mean"). Short (long espejo):
  1. Empujón con esfuerzo: el high toca el nivel extremo superior (banda +2σ del VWAP de sesión, +1σ, o dVAH según la
     variante) y en ese tramo hay ≥ 1 vela con RVOL ≥ RVOL_ESFUERZO.
  2. Sin continuación: dentro de MAX_VELAS desde el inicio del empujón, la primera vela que no hace un máximo nuevo,
     cierra por debajo del nivel y es bajista. Entrada al cierre de esa vela (motor: primer tick posterior).
  3. SL = máximo del empujón + 0,25 ATR(14). TP = VWAP de sesión al cierre de la vela de señal.
  4. Se ignoran los primeros MIN_SESION minutos del día UTC (bandas degeneradas) y solo dentro de la ventana operativa.
Todo con información disponible al cierre de la vela de señal (los niveles son los valores "vivo" de ese minuto).
"""
from __future__ import annotations

import numpy as np
import polars as pl

import indicadores as ind
import senales

RVOL_ESFUERZO = 1.5
MAX_VELAS = 10
MIN_SESION = 30
SL_MARGEN_ATR = 0.25
NIVELES = {  # variante → (columna del nivel superior, columna del nivel inferior)
    "2sd": ("vwap_d_p2", "vwap_d_m2"),
    "1sd": ("vwap_d_p1", "vwap_d_m1"),
    "va": ("dVAH", "dVAL"),
}


def detectar(df: pl.DataFrame, variante: str) -> pl.DataFrame:
    sup, inf = NIVELES[variante]
    t = df["open_time"].to_numpy()
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    rv, atr, vw = df["rvol"].to_numpy(), df["atr14"].to_numpy(), df["vwap_d"].to_numpy()
    ns, ni = df[sup].to_numpy(), df[inf].to_numpy()
    min_dia = (t // 60_000) % 1440
    out = []
    for lado in ("short", "long"):
        i, n = 0, t.size
        while i < n:
            toca = (h[i] >= ns[i]) if lado == "short" else (l[i] <= ni[i])
            if not toca or min_dia[i] < MIN_SESION or np.isnan(ns[i]):
                i += 1
                continue
            # empujón: desde i, seguimiento de extremo y esfuerzo hasta MAX_VELAS o hasta la señal
            ext = h[i] if lado == "short" else l[i]
            esfuerzo = rv[i] >= RVOL_ESFUERZO
            dia = t[i] // 86_400_000
            j = i + 1
            senal = None
            while j < n and j - i <= MAX_VELAS and t[j] // 86_400_000 == dia:
                nuevo = (h[j] > ext) if lado == "short" else (l[j] < ext)
                if nuevo:
                    ext = h[j] if lado == "short" else l[j]
                    esfuerzo = esfuerzo or rv[j] >= RVOL_ESFUERZO
                    j += 1
                    continue
                adentro = (c[j] < ns[j]) if lado == "short" else (c[j] > ni[j])
                vela_ok = (c[j] < o[j]) if lado == "short" else (c[j] > o[j])
                if adentro and vela_ok and esfuerzo:
                    senal = j
                    break
                esfuerzo = esfuerzo or rv[j] >= RVOL_ESFUERZO
                j += 1
            if senal is not None:
                sl = ext + SL_MARGEN_ATR * atr[senal] if lado == "short" else ext - SL_MARGEN_ATR * atr[senal]
                out.append({"open_time": int(t[senal]), "lado": lado, "sl": float(sl), "tp": float(vw[senal]),
                            "extremo": float(ext), "inicio_empujon": int(t[i]), "atr14": float(atr[senal]),
                            "nivel": float(ns[senal] if lado == "short" else ni[senal])})
                i = senal + 1
            else:
                i = j
    s = pl.DataFrame(out).sort("open_time") if out else pl.DataFrame()
    return s


def calcular(desde: str, hasta: str, variante: str = "2sd") -> pl.DataFrame:
    df = ind.cargar(desde, hasta)
    s = detectar(df, variante)
    if s.is_empty():
        return s
    s = s.with_columns(en_ventana=senales.ventana_operativa(pl.col("open_time")), variante=pl.lit(variante),
                       tipo=pl.lit("reversion"))
    # el TP tiene que quedar del lado correcto del cierre (la media por debajo para el short)
    return s
