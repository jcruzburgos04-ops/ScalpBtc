"""Estrategia B · 12 trades de la ventana de calibración (feb–may 2026) dibujados con las bandas del VWAP de sesión y
dVAH/dVAL, para que Juan confirme que el código opera el setup del trader. Incluye las dos entradas documentadas del
trader del 2026-02-20. Salida: reports/b/revision/casos.json"""
from __future__ import annotations

import json
import random
from pathlib import Path

import polars as pl

import f3_auditoria as fa
import indicadores as ind

RAIZ = Path(__file__).resolve().parent.parent
B = RAIZ / "reports" / "b"
SERIES = {"VWAP": "vwap_d", "+1σ": "vwap_d_p1", "−1σ": "vwap_d_m1", "+2σ": "vwap_d_p2", "−2σ": "vwap_d_m2", "dVAH": "dVAH", "dVAL": "dVAL"}


def overlays(c: dict, df: pl.DataFrame) -> dict:
    ts = [v["t"] * 1000 for v in c["velas"]]
    x = df.filter(pl.col("open_time").is_in(ts)).sort("open_time")
    return {nom: [{"t": int(r["open_time"]) // 1000, "v": round(float(r[col]), 1)} for r in x.select("open_time", col).iter_rows(named=True)
                  if r[col] is not None] for nom, col in SERIES.items()}


def main(semilla: int = 5) -> None:
    rnd = random.Random(semilla)
    df = ind.cargar("2026-02", "2026-05")
    casos = []
    va = pl.read_parquet(B / "trades_b1_va_2026-02_2026-05_rmin1_patas1.parquet")
    dos = pl.read_parquet(B / "trades_b1_2sd_2026-02_2026-05_rmin1_patas1.parquet")
    # las dos entradas documentadas del trader (2026-02-20, ~01:27 y ~02:26 UTC)
    for t in (1771550820000, 1771554360000):
        r = va.filter(pl.col("t_senal") == t)
        if r.height:
            casos.append(fa.caso(r.row(0, named=True), "Trade documentado del trader (TW1, 20-feb-2026)", "sin", len(casos) + 1, "last"))
    for tabla, et, n in [(va, "B1 · rechazo en dVAL/dVAH", 5), (dos, "B1 · rechazo en la banda ±2σ", 5)]:
        filas = [r for r in tabla.to_dicts() if r["t_senal"] not in (1771550820000, 1771554360000)]
        rnd.shuffle(filas)
        # mitad ganadores, mitad perdedores para ver los dos lados
        g = [r for r in filas if r["r"] > 0][: (n + 1) // 2] + [r for r in filas if r["r"] <= 0][: n // 2]
        for r in g:
            casos.append(fa.caso(r, et, "sin", len(casos) + 1, "last"))
    for c in casos:
        c["ov"] = overlays(c, df)
    out = B / "revision"
    out.mkdir(parents=True, exist_ok=True)
    (out / "casos.json").write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
    print(len(casos), "casos:", [c["etiqueta"][:30] for c in casos])


if __name__ == "__main__":
    main()
