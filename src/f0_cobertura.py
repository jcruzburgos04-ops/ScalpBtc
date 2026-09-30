"""F0 · Cobertura del bucket público data.binance.vision (futuros USD-M, BTCUSDT).

Solo LISTA el bucket (no descarga nada). Para cada dataset y frecuencia (monthly/daily)
informa el primer y último período disponible, los meses/días faltantes dentro del rango
2022-01-01 → hoy y el tamaño total de los zips.

Uso:  python src/f0_cobertura.py [--salida reports/f0/cobertura.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import xml.etree.ElementTree as ET

import requests

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BASE = "data/futures/um/{freq}/{dataset}/BTCUSDT/{sub}"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
INICIO = dt.date(2022, 1, 1)

# (dataset, subcarpeta de intervalo, frecuencias a revisar)
DATASETS = [
    ("klines", "1m/", ("monthly", "daily")),
    ("aggTrades", "", ("monthly", "daily")),
    ("markPriceKlines", "1m/", ("monthly", "daily")),
    ("indexPriceKlines", "1m/", ("monthly", "daily")),
    ("premiumIndexKlines", "1m/", ("monthly", "daily")),
    ("metrics", "", ("monthly", "daily")),
    ("liquidationSnapshot", "", ("monthly", "daily")),
]

RE_PERIODO = re.compile(r"-(\d{4}-\d{2}(?:-\d{2})?)\.zip$")


def listar(prefijo: str) -> list[tuple[str, int]]:
    """Devuelve [(key, bytes)] de todos los objetos bajo el prefijo (paginando)."""
    out: list[tuple[str, int]] = []
    marker = ""
    while True:
        r = requests.get(BUCKET, params={"prefix": prefijo, "marker": marker}, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for c in root.findall("s3:Contents", NS):
            out.append((c.find("s3:Key", NS).text, int(c.find("s3:Size", NS).text)))
        if root.find("s3:IsTruncated", NS).text != "true" or not out:
            return out
        marker = out[-1][0]


def esperados(freq: str, hasta: dt.date) -> list[str]:
    if freq == "monthly":
        res, d = [], INICIO
        while d < hasta.replace(day=1):  # el mes en curso todavía no se publica en monthly
            res.append(d.strftime("%Y-%m"))
            d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        return res
    return [(INICIO + dt.timedelta(days=i)).isoformat() for i in range((hasta - INICIO).days)]


def compactar(faltantes: list[str], freq: str) -> str:
    """Agrupa períodos faltantes consecutivos en rangos para que el informe sea legible."""
    if not faltantes:
        return "—"
    fmt = "%Y-%m" if freq == "monthly" else "%Y-%m-%d"
    ds = [dt.datetime.strptime(x, fmt).date() for x in faltantes]
    rangos, ini, prev = [], ds[0], ds[0]
    for d in ds[1:]:
        paso = (d.year - prev.year) * 12 + d.month - prev.month if freq == "monthly" else (d - prev).days
        if paso == 1:
            prev = d
            continue
        rangos.append((ini, prev))
        ini = prev = d
    rangos.append((ini, prev))
    txt = [a.strftime(fmt) if a == b else f"{a.strftime(fmt)}→{b.strftime(fmt)}" for a, b in rangos]
    return ", ".join(txt[:8]) + (f" … (+{len(txt) - 8} rangos)" if len(txt) > 8 else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="reports/f0/cobertura.md")
    args = ap.parse_args()
    hoy = dt.datetime.now(dt.timezone.utc).date()

    filas = []
    for dataset, sub, freqs in DATASETS:
        for freq in freqs:
            objs = listar(BASE.format(freq=freq, dataset=dataset, sub=sub))
            zips = {}
            checks = set()
            for key, size in objs:
                m = RE_PERIODO.search(key.removesuffix(".CHECKSUM"))
                if not m:
                    continue
                if key.endswith(".CHECKSUM"):
                    checks.add(m.group(1))
                else:
                    zips[m.group(1)] = size
            per = sorted(zips)
            exp = esperados(freq, hoy)
            falt = [p for p in exp if p not in zips]
            sin_check = [p for p in per if p not in checks]
            gb = sum(zips[p] for p in per if p >= exp[0]) / 1e9 if per else 0.0
            filas.append({
                "dataset": dataset + (f" {sub.rstrip('/')}" if sub else ""),
                "freq": freq,
                "primero": per[0] if per else "—",
                "ultimo": per[-1] if per else "—",
                "n": sum(1 for p in per if p >= exp[0]),
                "esperados": len(exp),
                "faltantes": compactar(falt, freq),
                "sin_checksum": len(sin_check),
                "gb": gb,
            })
            print(f"{filas[-1]['dataset']:<26} {freq:<8} {filas[-1]['primero']} → {filas[-1]['ultimo']}  "
                  f"{filas[-1]['n']}/{len(exp)}  {gb:.2f} GB")

    lineas = [
        f"# F0 · Cobertura de data.binance.vision (BTCUSDT USD-M) — listado del {hoy.isoformat()}",
        "",
        f"Rango pedido: {INICIO.isoformat()} → {hoy.isoformat()} (monthly: hasta el último mes cerrado; "
        "daily: hasta ayer). Tamaño = zips comprimidos desde 2022-01.",
        "",
        "| Dataset | Frec. | Primero | Último | Disponibles/esperados (desde 2022-01) | Faltantes | Sin .CHECKSUM | GB zip |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        lineas.append(f"| {f['dataset']} | {f['freq']} | {f['primero']} | {f['ultimo']} | "
                      f"{f['n']}/{f['esperados']} | {f['faltantes']} | {f['sin_checksum']} | {f['gb']:.2f} |")
    with open(args.salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    print(f"\nInforme: {args.salida}")


if __name__ == "__main__":
    main()
