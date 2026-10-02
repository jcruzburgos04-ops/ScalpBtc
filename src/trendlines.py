"""Ruptura de líneas de tendencia automáticas (Juan 2026-10-02: "indicadores que generen trendlines, y se tradee cuando
rompen"; sin cientos de líneas → UNA línea por lado, la más reciente).

Línea bajista (para longs): une los dos últimos pivots altos confirmados con el segundo más bajo que el primero
(máximos decrecientes). Pivot alto de largo n = máximo de las n velas a cada lado; se confirma n velas después
(sin mirar hacia adelante). La línea se extiende hacia la derecha hasta que se rompe o aparece un pivot nuevo.
Señal long: el cierre de 1m queda por encima de la línea (antes estaba debajo) → entrada al cierre. Short = espejo
con la línea alcista que une mínimos crecientes.
Variantes (fijadas antes): n = 5 / 10 / 20 · con y sin filtro EMA 200 de 45m.
SL: extremo de 10 velas ± 0,25 ATR (como A). Salidas: TP 3R con 50 % en +1R (la operable de Juan) y TP 2R.
Motor de 1 s, hasta 4 patas, sin comisiones. Calibración 2023–2024 → test 2025-01..2026-06.
Elección (fijada antes): máximo R con gana ≥ 50 % en calibración. Salida: reports/trendlines/trendlines.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from numba import njit

import indicadores as ind
import motor
import senales
from f3_correr import SL_MARGEN_ATR, filtro_ema45
from nuevas_mr import COLS, met

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trendlines"


@njit(cache=True)
def rupturas(h, l, c, n):
    """Devuelve (+1 ruptura alcista de la línea bajista, −1 ruptura bajista de la línea alcista, 0 nada) por vela,
    y el precio de la línea en esa vela."""
    m = c.size
    out = np.zeros(m, np.int64)
    linea = np.full(m, np.nan)
    # últimos dos pivots altos / bajos confirmados: (índice, precio)
    ph1i, ph1, ph2i, ph2 = -1, 0.0, -1, 0.0
    pl1i, pl1, pl2i, pl2 = -1, 0.0, -1, 0.0
    usada_h, usada_l = True, True
    for i in range(2 * n, m):
        p = i - n                                   # candidato a pivot, confirmado en i
        es_h, es_l = True, True
        for k in range(p - n, p + n + 1):
            if k != p:
                if h[k] >= h[p]:
                    es_h = False
                if l[k] <= l[p]:
                    es_l = False
        if es_h:
            ph1i, ph1, ph2i, ph2 = ph2i, ph2, p, h[p]
            usada_h = False
        if es_l:
            pl1i, pl1, pl2i, pl2 = pl2i, pl2, p, l[p]
            usada_l = False
        # línea bajista: máximos decrecientes
        if ph1i >= 0 and ph2 < ph1 and not usada_h:
            v = ph2 + (ph2 - ph1) / (ph2i - ph1i) * (i - ph2i)
            vprev = ph2 + (ph2 - ph1) / (ph2i - ph1i) * (i - 1 - ph2i)
            if c[i] > v and c[i - 1] <= vprev:
                out[i] = 1
                linea[i] = v
                usada_h = True
        if pl1i >= 0 and pl2 > pl1 and not usada_l:
            v = pl2 + (pl2 - pl1) / (pl2i - pl1i) * (i - pl2i)
            vprev = pl2 + (pl2 - pl1) / (pl2i - pl1i) * (i - 1 - pl2i)
            if c[i] < v and c[i - 1] >= vprev:
                out[i] = -1
                linea[i] = v
                usada_l = True
    return out, linea


@njit(cache=True)
def _valor(i1, p1, i2, p2, k):
    return p2 + (p2 - p1) / (i2 - i1) * (k - i2)


@njit(cache=True)
def _toques(x, atr, i1, p1, i2, p2, fin, tol, sg):
    """Episodios (velas consecutivas cuentan como uno) en que la mecha llega a ≤ tol × ATR de la línea."""
    t, antes = 0, False
    for k in range(i1, fin):
        toca = sg * (x[k] - _valor(i1, p1, i2, p2, k)) >= -tol * atr[k]
        if toca and not antes:
            t += 1
        antes = toca
    return t


@njit(cache=True)
def rupturas_v2(h, l, c, atr, n, vida, tol):
    """Versión aceitada (2026-10-02). Misma línea (dos últimos pivots confirmados, una por lado) más tres reglas:
    1. Línea limpia: si algún cierre entre el pivot 1 y la confirmación del pivot 2 ya quedó del otro lado, la línea
       nació rota y no da señal.
    2. Vencimiento: la ruptura tiene que llegar dentro de `vida` × (distancia entre pivots) velas después del pivot 2.
    3. Toques: velas entre el pivot 1 y la ruptura cuya mecha llega a ≤ tol × ATR de la línea sin cerrar del otro lado
       (incluye los dos pivots). Se informa; filtro opcional.
    Devuelve por vela: señal (+1/−1/0), precio de la línea, índice del pivot 1, índice del pivot 2, toques."""
    m = c.size
    out = np.zeros(m, np.int64)
    linea = np.full(m, np.nan)
    a1 = np.full(m, -1, np.int64)
    a2 = np.full(m, -1, np.int64)
    toq = np.zeros(m, np.int64)
    ph1i, ph1, ph2i, ph2 = -1, 0.0, -1, 0.0
    pl1i, pl1, pl2i, pl2 = -1, 0.0, -1, 0.0
    viva_h, viva_l = False, False
    for i in range(2 * n, m):
        p = i - n
        es_h, es_l = True, True
        for k in range(p - n, p + n + 1):
            if k != p:
                if h[k] >= h[p]:
                    es_h = False
                if l[k] <= l[p]:
                    es_l = False
        if es_h:
            ph1i, ph1, ph2i, ph2 = ph2i, ph2, p, h[p]
            viva_h = ph1i >= 0 and ph2 < ph1
            if viva_h:
                for k in range(ph1i + 1, i):
                    if c[k] > _valor(ph1i, ph1, ph2i, ph2, k):
                        viva_h = False
                        break
        if es_l:
            pl1i, pl1, pl2i, pl2 = pl2i, pl2, p, l[p]
            viva_l = pl1i >= 0 and pl2 > pl1
            if viva_l:
                for k in range(pl1i + 1, i):
                    if c[k] < _valor(pl1i, pl1, pl2i, pl2, k):
                        viva_l = False
                        break
        if viva_h and i - ph2i > vida * (ph2i - ph1i):
            viva_h = False
        if viva_l and i - pl2i > vida * (pl2i - pl1i):
            viva_l = False
        if viva_h and c[i] > _valor(ph1i, ph1, ph2i, ph2, i):
            out[i] = 1
            linea[i] = _valor(ph1i, ph1, ph2i, ph2, i)
            a1[i], a2[i] = ph1i, ph2i
            toq[i] = _toques(h, atr, ph1i, ph1, ph2i, ph2, i, tol, 1.0)
            viva_h = False
        if viva_l and c[i] < _valor(pl1i, pl1, pl2i, pl2, i):
            out[i] = -1
            linea[i] = _valor(pl1i, pl1, pl2i, pl2, i)
            a1[i], a2[i] = pl1i, pl2i
            toq[i] = _toques(l, atr, pl1i, pl1, pl2i, pl2, i, tol, -1.0)
            viva_l = False
    return out, linea, a1, a2, toq


VIDA, TOL = 2.0, 0.15   # v2: vence a 2× la distancia entre pivots · toque = mecha a ≤ 0,15 ATR de la línea


def senales_tl(desde: str, hasta: str, n: int, v2: bool = False) -> pl.DataFrame:
    df = ind.cargar(desde, hasta).select("open_time", "high", "low", "close", "atr14").sort("open_time")
    hlc = [df[x].to_numpy() for x in ("high", "low", "close")]
    if v2:
        r, lin, i1, i2, tq = rupturas_v2(*hlc, df["atr14"].to_numpy(), n, VIDA, TOL)
        t = df["open_time"].to_numpy()
        df = df.with_columns(linea=pl.Series(lin), t_piv1=pl.Series(np.where(i1 >= 0, t[np.maximum(i1, 0)], -1)),
                             t_piv2=pl.Series(np.where(i2 >= 0, t[np.maximum(i2, 0)], -1)), toques=pl.Series(tq))
    else:
        r, _ = rupturas(*hlc, n)
    df = df.with_columns(rup=pl.Series(r), min10=pl.col("low").rolling_min(10), max10=pl.col("high").rolling_max(10),
                         en_ventana=senales.ventana_operativa(pl.col("open_time")))
    s = df.filter((pl.col("rup") != 0) & pl.col("en_ventana")).with_columns(
        lado=pl.when(pl.col("rup") > 0).then(pl.lit("long")).otherwise(pl.lit("short")))
    return s.with_columns(
        sl=pl.when(pl.col("lado") == "long").then(pl.col("min10") - SL_MARGEN_ATR * pl.col("atr14"))
        .otherwise(pl.col("max10") + SL_MARGEN_ATR * pl.col("atr14")),
        tp=pl.lit(None, dtype=pl.Float64), tipo=pl.lit(f"TL{n}"), z_favor=pl.lit(0.0), cruces_ash30=pl.lit(0),
        rvol=pl.lit(0.0), dist5m_atr=pl.lit(0.0))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for k, (d, h) in {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}.items():
        D = motor.Datos(d, h)
        for n in (5, 10, 20):
            s0 = senales_tl(d, h, n)
            for filtro in ("", " + EMA 45m"):
                s = filtro_ema45(s0, d) if filtro else s0
                for salida, tp_r, P in (("TP 3R + 50 % en +1R", 3.0, motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)),
                                        ("TP 2R", 2.0, motor.Params(sl_por="last"))):
                    x = s.with_columns(tp_r=pl.lit(tp_r))
                    patas, _ = motor.simular(D, x.select(COLS), P, x["open_time"].sort().to_numpy())
                    nom = f"pivots de {n} velas{filtro} · {salida}"
                    res[(nom, k)] = met(motor.a_tabla(patas))
                    print(k, nom, res[(nom, k)][0], flush=True)
    noms = list(dict.fromkeys(n for n, _ in res))
    l = ["Ruptura de la línea de tendencia más reciente · patas · gana · R medio [IC 95 % por posición] · motor 1 s, sin comisiones.", "",
         "| Variante | Calibración 2023–2024 | Test 2025-01..2026-06 |", "|---|---|---|"]
    for n in noms:
        l.append(f"| {n} | {res[(n, 'cal')][0]} | {res[(n, 'test')][0]} |")
    ok = [n for n in noms if res[(n, "cal")][1] >= 0.5]
    if ok:
        el = max(ok, key=lambda n: res[(n, "cal")][2])
        l += ["", f"Elegida en calibración (máximo R con gana ≥ 50 %): {el} → test {res[(el, 'test')][0]}"]
    txt = "\n".join(l)
    (OUT / "trendlines.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
