"""Estrategia B · corre el motor con las señales de reversión del trader de referencia.
Uso: python src/b_correr.py <desde> <hasta> --variante 2sd|1sd|va --r_min 1 [--patas 1]"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import motor
import estrategia_b as b

RAIZ = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("desde"); ap.add_argument("hasta")
    ap.add_argument("--variante", default="va", choices=list(b.NIVELES))
    ap.add_argument("--r_min", type=float, default=1.0)
    ap.add_argument("--patas", type=int, default=1)
    ap.add_argument("--be", type=float, default=0.5)  # breakeven a +0,5 R adoptado (2026-10-01); --be 0 lo apaga
    ap.add_argument("--corte", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    s = b.calcular(a.desde, a.hasta, a.variante)
    D = motor.Datos(a.desde, a.hasta)
    P = motor.Params(r_min=a.r_min, max_patas=a.patas, sl_por="last", be_r=a.be or None, corte_min=a.corte)
    cols = ["open_time", "lado", "en_ventana", "sl", "tp", "tipo", "atr14", "variante", "extremo", "nivel", "inicio_empujon"]
    patas, ign = motor.simular(D, s.select(cols), P)
    tabla = motor.a_tabla(patas)
    out = RAIZ / "reports" / "b"
    out.mkdir(parents=True, exist_ok=True)
    nom = f"trades_b1_{a.variante}_{a.desde}_{a.hasta}_rmin{a.r_min:g}_patas{a.patas}{f'_be{a.be:g}' if a.be else ''}{f'_corte{a.corte}' if a.corte else ''}"
    tabla.write_parquet(out / f"{nom}.parquet")
    print(f"{nom}: {tabla.height} trades, {len(ign)} ignoradas, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
