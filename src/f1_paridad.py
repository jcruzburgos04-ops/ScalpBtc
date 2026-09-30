"""F1 · Compara los valores que Juan anota de TradingView (tests/paridad_tv.csv) contra la réplica.

Cada fila: hora_art = apertura de la vela de 1m en hora argentina (AAAA-MM-DD HH:MM), leída en vivo cerca del
cierre de esa vela. Las columnas vacías se ignoran. Las etiquetas que dependen de un TF mayor se comparan con la
versión vivo (lo que se ve en tiempo real).
Salida: reports/f1/paridad.md
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

import indicadores as ind

RAIZ = Path(__file__).resolve().parent.parent
TOL = {"ash_bulls": 0.01, "ash_bears": 0.01, "rvol": 0.001}  # el resto: ±0,1 USD (confirmado por Juan)
VIVO = {"r7D", "r30D", "MNDAY_H", "MNDAY_L"}


def main() -> None:
    tv = pl.read_csv(RAIZ / "tests" / "paridad_tv.csv", infer_schema_length=0)
    df = ind.cargar("2026-10")
    l = ["# F1 · Paridad con TradingView", "", "| Hora ART | Valor | TV | Réplica | Dif. | Tol. | ¿OK? |",
         "|---|---|---|---|---|---|---|"]
    malos = 0
    for r in tv.iter_rows(named=True):
        t = dt.datetime.strptime(r["hora_art"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        ms = int(t.timestamp() * 1000)
        fila = df.filter(pl.col("open_time") == ms)
        if fila.is_empty():
            l.append(f"| {r['hora_art']} | (sin datos todavía: Binance publica el día siguiente) | | | | | |")
            continue
        f = fila.row(0, named=True)
        for col, val in r.items():
            if col in ("hora_art", "comentario") or val in (None, ""):
                continue
            nuestro = f[col + "_vivo"] if col in VIVO else f[col]
            d = float(val.replace(",", ".")) - nuestro
            tol = TOL.get(col, 0.1)
            ok = abs(d) <= tol
            malos += not ok
            l.append(f"| {r['hora_art']} | {col} | {val} | {nuestro:.4f} | {d:+.4f} | {tol} | {'sí' if ok else '**NO**'} |")
    l += ["", f"Fuera de tolerancia: {malos}"]
    (RAIZ / "reports" / "f1" / "paridad.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
