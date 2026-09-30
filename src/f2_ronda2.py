"""F2 · Ronda 2: 30 señales NUEVAS de 2023–2024 para validar los filtros elegidos en la ronda 1.

20 pasan los filtros (ubicación ≤ +1σ y ≤ 3 cruces del ASH en 30 min) y 10 no (5 fallan solo por ubicación y
5 solo por rango). Días distintos entre sí y distintos de los de la ronda 1. El orden se mezcla: Juan no sabe cuáles
pasan. Se mide la coincidencia con casos que no se usaron para elegir las reglas.
Salida: reports/f2/ronda2/casos.json
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

import polars as pl

import indicadores as ind
import senales
from f2_muestra import a_json

RAIZ = Path(__file__).resolve().parent.parent
CUPOS = {"pasa": 20, "falla_ubicacion": 5, "falla_rango": 5}


def main(semilla: int = 20261001) -> None:
    rnd = random.Random(semilla)
    s = senales.calcular(filtrar=False).with_columns(dia=pl.from_epoch("open_time", time_unit="ms").dt.date())
    s = s.with_columns(grupo=pl.when(pl.col("pasa_filtros")).then(pl.lit("pasa"))
                       .when(~pl.col("ok_ubicacion") & pl.col("ok_rango")).then(pl.lit("falla_ubicacion"))
                       .when(pl.col("ok_ubicacion") & ~pl.col("ok_rango")).then(pl.lit("falla_rango"))
                       .otherwise(pl.lit("falla_ambos")))
    r1 = json.loads((RAIZ / "reports" / "f2" / "casos.json").read_text())
    dias = {dt.datetime.fromtimestamp(c["t"], dt.timezone.utc).date() for c in r1}
    filas = s.to_dicts()
    rnd.shuffle(filas)
    combos = [(l, t) for l in ("long", "short") for t in ("continuacion", "rebote")]
    elegidos = []
    for grupo, n in CUPOS.items():
        k = 0
        for f in filas:
            if len([e for e in elegidos if e["grupo"] == grupo]) >= n:
                break
            lado, tipo = combos[k % 4]
            if f["grupo"] != grupo or f["dia"] in dias or f["lado"] != lado or f["tipo"] != tipo:
                continue
            elegidos.append(f)
            dias.add(f["dia"])
            k += 1
    rnd.shuffle(elegidos)
    df = ind.cargar("2022-12", "2024-12")
    casos = []
    for i, c in enumerate(elegidos):
        j = a_json(c, df, i + 1)
        j.update({"_grupo": c["grupo"], "_z_favor": round(c["z_favor"], 3), "_cruces_ash30": c["cruces_ash30"]})
        casos.append(j)
    out = RAIZ / "reports" / "f2" / "ronda2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "casos.json").write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
    m = pl.DataFrame([{"grupo": c["_grupo"], "lado": c["lado"], "tipo": c["tipo"]} for c in casos])
    print(len(casos), "casos")
    print(m.group_by("grupo", "lado", "tipo").len().sort("grupo", "lado", "tipo"))


if __name__ == "__main__":
    main()
