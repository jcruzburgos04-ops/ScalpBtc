"""Backtest 2020-01 → 2026-09 de las dos estrategias con gana ≥ 50 % (pedido de Juan 2026-10-28).

  A congelada   señal ASH + XO de Juan, SL ext10 ± 0,25 ATR, filtro EMA 200 de 45m, TP 3R con 50 % en +1R
                (breakeven del resto). = `f3_correr.py D H --ema45 --parcial 1 --parcial_f 0.5 --tp_r 3`
  Trendlines    ruptura de trendline v2 (pivots 10, línea limpia, vence a 2×) con agresión a favor (delta de la vela
                ≥ 0,2), filtro EMA 200 de 45m, TP en el nivel opuesto (primero a ≥ 2R), 50 % en +1R.
                = la elegida en `trendlines_volumen.py`.
Motor de 1 s, entrada al primer tick después del cierre, SL por last, hasta 4 patas de 1 % cada una, sin comisiones,
solo entradas en la ventana 00:00 UTC → 12:00 NY. Se corre por año calendario; el motor de cada año ve también el mes
siguiente para cerrar las posiciones abiertas el 31-dic. La reserva (oct–dic 2026) no se toca.
Salida: reports/backtest_2020/trades_{A,TL}.parquet
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import polars as pl

import a_tp_nivel as atn
import motor
from f3_correr import filtro_ema45, preparar
from nuevas_mr import COLS, met
from trendlines import senales_tl

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "backtest_2020"
ULTIMO = "2026-09"
P = motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)


def anios():
    for a in range(2020, 2027):
        d, h = f"{a}-01", (f"{a}-12" if a < 2026 else ULTIMO)
        yield a, d, h, (f"{a + 1}-01" if a < 2026 else ULTIMO)


def senales_a(d, h):
    s, todas = preparar(d, h, 3.0)
    return filtro_ema45(s, d), todas.sort().to_numpy()


def senales_tl_vol(d, h):
    s = senales_tl(d, h, 10, v2=True)
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    s = s.filter(sg * pl.col("delta1") >= 0.2)
    s = atn.con_tp(filtro_ema45(s, d).drop("tp"), d, h)
    return s, s["open_time"].sort().to_numpy()


def main(cuales=("A", "TL")) -> None:
    atn.NIV = atn.NIV + ["mVAH_vivo", "mVAL_vivo", "rVAH", "rVAL"]
    OUT.mkdir(parents=True, exist_ok=True)
    fun = {"A": senales_a, "TL": senales_tl_vol}
    tablas = {k: [] for k in cuales}
    pos0 = {k: 0 for k in cuales}
    for a, d, h, h_motor in anios():
        D = motor.Datos(d, h_motor)
        for k in cuales:
            t0 = time.time()
            s, todas = fun[k](d, h)
            patas, _ = motor.simular(D, s.select(COLS), P, todas)
            t = motor.a_tabla(patas)
            if t.height:
                t = t.with_columns(pos_id=pl.col("pos_id") + pos0[k], anio=pl.lit(a))
                pos0[k] = int(t["pos_id"].max()) + 1
                tablas[k].append(t)
            print(a, k, met(t)[0], f"{time.time() - t0:.0f} s", flush=True)
        del D
    for k in cuales:
        x = pl.concat(tablas[k], how="diagonal_relaxed")
        x.write_parquet(OUT / f"trades_{k}.parquet")
        print(k, "total", met(x)[0], flush=True)


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("A", "TL"))
