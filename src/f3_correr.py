"""F3 · Corre el motor sobre las señales base de F2 con el SL elegido (ext_10 + 0,25 ATR) y un TP provisorio en R fijo.
Uso: python src/f3_correr.py 2023-01 2024-12 [--invalidacion] [--tp_r 2] [--slip 0]"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import polars as pl

import motor
import senales

RAIZ = Path(__file__).resolve().parent.parent
SL_K, SL_MARGEN_ATR = 10, 0.25  # elegido por coincidencia con los SL de Juan (reports/f3_sl_candidatos.csv)


def preparar(desde: str, hasta: str, tp_r: float) -> tuple[pl.DataFrame, pl.Series]:
    s = senales.calcular(desde, hasta, filtrar=False, solo_ventana=False)
    s = s.with_columns(
        sl=pl.when(pl.col("lado") == "long").then(pl.col("min_low10") - SL_MARGEN_ATR * pl.col("atr14"))
        .otherwise(pl.col("max_high10") + SL_MARGEN_ATR * pl.col("atr14")),
        tp=pl.lit(None, dtype=pl.Float64), tp_r=pl.lit(tp_r)).filter(pl.col("sl").is_not_null())
    return s, s["open_time"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("desde"); ap.add_argument("hasta")
    ap.add_argument("--invalidacion", action="store_true")
    ap.add_argument("--tp_r", type=float, default=2.0)
    ap.add_argument("--slip", type=float, default=0.0)
    ap.add_argument("--sl_por", default="last", choices=["mark", "last"])
    ap.add_argument("--be", type=float, default=None)   # breakeven al llegar a +be R
    a = ap.parse_args()
    t0 = time.time()
    s, todas = preparar(a.desde, a.hasta, a.tp_r)
    D = motor.Datos(a.desde, a.hasta)
    P = motor.Params(slip_sl_ticks=a.slip, invalidacion=a.invalidacion, sl_por=a.sl_por, be_r=a.be)
    cols = ["open_time", "lado", "en_ventana", "sl", "tp", "tp_r", "tipo", "atr14", "z_favor", "cruces_ash30", "rvol", "dist5m_atr"]
    patas, ign = motor.simular(D, s.select(cols), P, todas.sort().to_numpy())
    tabla = motor.a_tabla(patas)
    out = RAIZ / "reports" / "f3"
    out.mkdir(parents=True, exist_ok=True)
    nom = f"trades_{a.desde}_{a.hasta}_tp{a.tp_r:g}{'_inv' if a.invalidacion else ''}_slip{a.slip:g}_sl{a.sl_por}{f'_be{a.be:g}' if a.be else ''}"
    tabla.write_parquet(out / f"{nom}.parquet")
    pl.DataFrame(ign).write_parquet(out / f"{nom}_ignoradas.parquet") if ign else None
    print(f"{tabla.height} patas en {tabla['pos_id'].n_unique() if tabla.height else 0} posiciones, {len(ign)} señales ignoradas, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
