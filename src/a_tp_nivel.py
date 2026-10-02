"""A + EMA 200 de 45m con TP en el "nivel opuesto" del trader (Juan 2026-10-02).

Niveles donde terminaron los recorridos ganadores del trader (reports/trader_sep/salidas.md): MNDAY-H/L, VWAP ±2σ de
sesión, dVAH/dVAL, VWAP ±2σ semanal. TP = el primero de esos niveles en la dirección del trade que quede a ≥ 2R del
precio de la señal (long: el más bajo por encima; short: el más alto por debajo). Sin nivel a ≥ 2R → no se entra.
Salidas: con 50 % cobrado en +1R (breakeven del resto) y sin parcial. Motor de 1 s, hasta 4 patas, sin comisiones.
Calibración 2023–2024 → test 2025-01..2026-06. Referencia: A congelada (TP 3R + 50 % en +1R).
Salida: reports/f3/a_tp_nivel.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import indicadores as ind
import motor
from f3_correr import filtro_ema45, preparar
from nuevas_mr import COLS, met

RAIZ = Path(__file__).resolve().parent.parent
F3 = RAIZ / "reports" / "f3"
NIV = ["MNDAY_H_vivo", "MNDAY_L_vivo", "vwap_d_p2", "vwap_d_m2", "dVAH", "dVAL", "vwap_w_p2", "vwap_w_m2"]


def con_tp(s: pl.DataFrame, desde: str, hasta: str) -> pl.DataFrame:
    lv = ind.cargar(desde, hasta).select("open_time", "close", *NIV)
    x = s.join(lv, on="open_time", how="left")
    c, sl = x["close"].to_numpy(), x["sl"].to_numpy()
    largo = (x["lado"] == "long").to_numpy()
    L = np.column_stack([x[n].cast(pl.Float64).to_numpy() for n in NIV])
    rg = np.abs(c - sl)
    d = np.where(largo[:, None], L - c[:, None], c[:, None] - L)        # distancia a favor
    d = np.where(np.isfinite(d) & (d >= 2 * rg[:, None]), d, np.inf)
    dmin = d.min(axis=1)
    tp = np.where(np.isfinite(dmin), np.where(largo, c + dmin, c - dmin), np.nan)
    return x.with_columns(tp=pl.Series(tp), tp_r=pl.lit(None, dtype=pl.Float64)).filter(pl.col("tp").is_not_nan())


def medir(desde: str, hasta: str) -> None:
    """Variante para la reserva: TP en el nivel opuesto SIN parcial, sobre [desde, hasta] (python src/a_tp_nivel.py AAAA-MM AAAA-MM)."""
    s, todas = preparar(desde, hasta, 2.0)
    s = con_tp(filtro_ema45(s, desde), desde, hasta)
    patas, _ = motor.simular(motor.Datos(desde, hasta), s.select(COLS), motor.Params(sl_por="last"), todas.sort().to_numpy())
    print(f"A + EMA 45m + TP nivel opuesto sin parcial, {desde}..{hasta}: {met(motor.a_tabla(patas))[0]}")


def main() -> None:
    l = ["A + EMA 200 de 45m · patas · gana · R medio [IC 95 % por posición] · motor 1 s, sin comisiones.", "",
         "| Salida | Calibración 2023–2024 | Test 2025-01..2026-06 |", "|---|---|---|"]
    res = {}
    for k, (d, h) in {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}.items():
        s, todas = preparar(d, h, 2.0)
        s = con_tp(filtro_ema45(s, d), d, h)
        D = motor.Datos(d, h)
        for nom, P in (("TP nivel opuesto + 50 % en +1R", motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)),
                       ("TP nivel opuesto, sin parcial", motor.Params(sl_por="last"))):
            patas, _ = motor.simular(D, s.select(COLS), P, todas.sort().to_numpy())
            t = motor.a_tabla(patas)
            res[(nom, k)] = met(t)
            print(nom, k, res[(nom, k)][0], flush=True)
    for nom in ("TP nivel opuesto + 50 % en +1R", "TP nivel opuesto, sin parcial"):
        l.append(f"| {nom} | {res[(nom, 'cal')][0]} | {res[(nom, 'test')][0]} |")
    l.append("| A congelada (TP 3R + 50 % en +1R), referencia | 12546 · 51% · +0.056 | 8870 · 52% · +0.080 [+0.052, +0.113] |")
    txt = "\n".join(l)
    (F3 / "a_tp_nivel.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    import sys
    medir(sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else main()
