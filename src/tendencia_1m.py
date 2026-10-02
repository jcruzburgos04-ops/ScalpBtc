"""Indicadores de tendencia en 1m de UNA línea/valor (Juan 2026-10-02: nada que dibuje cientos de líneas), como filtro de
la A congelada (TP 3R con 50 % en +1R, SL ext10 ± 0,25 ATR, hasta 4 patas, motor 1 s, sin comisiones).

Cada indicador da un estado alcista/bajista por minuto (vela cerrada); la señal long pasa si el estado es alcista:
  ema200        precio sobre la EMA 200 de 1m
  ema50_pend    EMA 50 de 1m subiendo respecto de 10 velas antes
  hma55_pend    Hull MA 55 subiendo respecto de la vela anterior
  supertrend    Supertrend (ATR 10, multiplicador 3) en modo alcista
  psar          Parabolic SAR (0,02 / 0,2) debajo del precio
  adx_di        ADX(14) ≥ 20 y +DI > −DI (long) / −DI > +DI (short)
  regresion60   pendiente de la regresión lineal de 60 cierres > 0
  vwap_pend     VWAP de sesión subiendo en los últimos 30 min
  kama          precio sobre la KAMA (10, 2, 30)
Variantes: A + indicador · A + EMA 200 de 45m + indicador. Calibración 2023–2024 → test 2025-01..2026-06.
Salida: reports/f3/tendencia_1m.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from numba import njit

import indicadores as ind
import motor
from datos import leer_velas_1m
from f3_correr import filtro_ema45, preparar
from indicadores import ema
from nuevas_mr import COLS, met

RAIZ = Path(__file__).resolve().parent.parent
F3 = RAIZ / "reports" / "f3"
NOMBRES = {"ema200": "precio sobre la EMA 200 (1m)", "ema50_pend": "EMA 50 subiendo (1m)", "hma55_pend": "Hull MA 55 subiendo",
           "supertrend": "Supertrend (10, 3)", "psar": "Parabolic SAR", "adx_di": "ADX ≥ 20 con DI a favor",
           "regresion60": "regresión lineal 60 subiendo", "vwap_pend": "VWAP de sesión subiendo 30 min", "kama": "precio sobre la KAMA"}


def wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    out = np.full(x.size, np.nan)
    c = np.convolve(x, w[::-1], mode="valid") / w.sum()
    out[n - 1:] = c
    return out


@njit(cache=True)
def supertrend(h, l, c, atr, mult):
    n = c.size
    up = np.zeros(n); dn = np.zeros(n); est = np.ones(n)
    for i in range(n):
        m = (h[i] + l[i]) / 2
        bu, bd = m - mult * atr[i], m + mult * atr[i]
        if i == 0 or not np.isfinite(atr[i]):
            up[i], dn[i] = bu, bd
            continue
        up[i] = max(bu, up[i - 1]) if c[i - 1] > up[i - 1] else bu
        dn[i] = min(bd, dn[i - 1]) if c[i - 1] < dn[i - 1] else bd
        est[i] = est[i - 1]
        if est[i - 1] < 0 and c[i] > dn[i - 1]:
            est[i] = 1
        elif est[i - 1] > 0 and c[i] < up[i - 1]:
            est[i] = -1
    return est


@njit(cache=True)
def psar(h, l, a0, amax):
    n = h.size
    est = np.ones(n); sar = l[0]; ep = h[0]; af = a0; largo = True
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if largo:
            sar = min(sar, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < sar:
                largo, sar, ep, af = False, ep, l[i], a0
            elif h[i] > ep:
                ep, af = h[i], min(af + a0, amax)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > sar:
                largo, sar, ep, af = True, ep, h[i], a0
            elif l[i] < ep:
                ep, af = l[i], min(af + a0, amax)
        est[i] = 1 if largo else -1
    return est


@njit(cache=True)
def kama(c, n, f, s):
    out = np.full(c.size, np.nan)
    fa, sa = 2 / (f + 1), 2 / (s + 1)
    out[n] = c[n]
    for i in range(n + 1, c.size):
        ch = abs(c[i] - c[i - n])
        vol = 0.0
        for k in range(i - n + 1, i + 1):
            vol += abs(c[k] - c[k - 1])
        er = ch / vol if vol > 0 else 0.0
        sc = (er * (fa - sa) + sa) ** 2
        out[i] = out[i - 1] + sc * (c[i] - out[i - 1])
    return out


def estados() -> pl.DataFrame:
    k = leer_velas_1m("2022-01", "2026-06").sort("open_time")
    t, h, l, c = (k[x].to_numpy() for x in ("open_time", "high", "low", "close"))
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])))
    atr10 = ind.rma(tr, 10)
    e200, e50 = ema(c, 200), ema(c, 50)
    hma = wma(2 * wma(c, 27) - wma(c, 55), 7)
    up, dn = h - np.r_[h[0], h[:-1]], np.r_[l[0], l[:-1]] - l
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr14 = ind.rma(tr, 14)
    pdi, mdi = 100 * ind.rma(pdm, 14) / atr14, 100 * ind.rma(mdm, 14) / atr14
    adx = ind.rma(100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9), 14)
    x = np.arange(60) - 29.5
    pend = np.full(c.size, np.nan)
    pend[59:] = np.convolve(c, x[::-1], mode="valid") / (x ** 2).sum()
    sgn = lambda b: np.where(b, 1, -1)  # noqa: E731
    vw = ind.cargar("2022-01", "2026-06").select("open_time", "vwap_d")
    d = pl.DataFrame({
        "open_time": t,
        "ema200": sgn(c > e200), "ema50_pend": sgn(e50 > np.r_[np.full(10, np.nan), e50[:-10]]),
        "hma55_pend": sgn(hma > np.r_[np.nan, hma[:-1]]), "supertrend": supertrend(h, l, c, atr10, 3.0).astype(int),
        "psar": psar(h, l, 0.02, 0.2).astype(int),
        "adx_di": np.where(adx >= 20, sgn(pdi > mdi), 0), "regresion60": sgn(pend > 0),
        "kama": sgn(c > kama(c, 10, 2, 30)),
    }).join(vw, on="open_time", how="left").sort("open_time")
    return d.with_columns(vwap_pend=pl.when(pl.col("vwap_d") > pl.col("vwap_d").shift(30)).then(1).otherwise(-1)).drop("vwap_d")


def filtrar(s: pl.DataFrame, est: pl.DataFrame, col: str) -> pl.DataFrame:
    x = s.join(est.select("open_time", col), on="open_time", how="left")
    sg = pl.when(pl.col("lado") == "long").then(1).otherwise(-1)
    return x.filter(pl.col(col) == sg).drop(col)


def main() -> None:
    est = estados()
    P = motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)
    res = {}
    for k, (d, h) in {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}.items():
        s, todas = preparar(d, h, 3.0)
        s45 = filtro_ema45(s, d)
        D = motor.Datos(d, h)
        variantes = {"A sin filtro de tendencia": s, "A + EMA 200 de 45m (congelada)": s45}
        for col, nom in NOMBRES.items():
            variantes[f"A + {nom}"] = filtrar(s, est, col)
            variantes[f"A + EMA 45m + {nom}"] = filtrar(s45, est, col)
        for nom, x in variantes.items():
            patas, _ = motor.simular(D, x.select(COLS), P, todas.sort().to_numpy())
            res[(nom, k)] = met(motor.a_tabla(patas))
            print(k, nom, res[(nom, k)][0], flush=True)
    noms = list(dict.fromkeys(n for n, _ in res))
    l = ["A con TP 3R y 50 % en +1R · patas · gana · R medio [IC 95 % por posición] · motor 1 s, sin comisiones.", "",
         "| Filtro de tendencia | Calibración 2023–2024 | Test 2025-01..2026-06 |", "|---|---|---|"]
    for n in noms:
        l.append(f"| {n} | {res[(n, 'cal')][0]} | {res[(n, 'test')][0]} |")
    el = max(noms, key=lambda n: res[(n, "cal")][2] if res[(n, "cal")][1] >= 0.5 else -9)
    l += ["", f"Mejor en calibración (gana ≥ 50 %): {el} → test {res[(el, 'test')][0]}"]
    txt = "\n".join(l)
    (F3 / "tendencia_1m.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
