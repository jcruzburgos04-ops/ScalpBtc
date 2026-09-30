"""F2 · Muestra de 40 señales de 2023–2024 para que Juan las revise ("la tomaría / no la tomaría" + SL).

Muestreo estratificado sobre las señales de umbrales amplios (senales.py): 3 tramos de la brecha del ASH (|gn|)
× 3 tramos de la brecha de las XO (|xg|), con long/short y continuación/rebote repartidos, días distintos y
algunos fines de semana. Así las respuestas de Juan muestran dónde cortar cada umbral.

Cada caso lleva los datos para dibujarlo SOLO hasta la vela de la señal (lo que se vería en vivo): 120 velas de 1m
con EMAs, VWAP de sesión ±1σ/±2σ, ASH y RVOL; las velas de 5m de las últimas 3 h con la de 5m en formación; y las
etiquetas vigentes en ese minuto. Sale a reports/f2/casos.json (se inserta en la página de revisión).
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

import polars as pl

import indicadores as ind
import senales

RAIZ = Path(__file__).resolve().parent.parent
N_CASOS = 40
VELAS_1M = 120
VELAS_5M = 36
TRAMOS_GN = [0.0, 0.03, 0.08, senales.A_MAX + 1e-9]
TRAMOS_XG = [0.0, 0.25, 0.6, senales.B_MAX + 1e-9]
ETIQUETAS = {  # columna → nombre en el gráfico (las de la visión baja del indicador de Juan)
    "dVAH": "dVAH", "dVAL": "dVAL", "rVAH": "rVAH", "rVAL": "rVAL", "DO": "DO", "WO": "WO",
    "PWH": "PWH", "PWL": "PWL", "MNDAY_H_vivo": "MNDAY-H", "MNDAY_L_vivo": "MNDAY-L",
    "pwVWAP_vivo": "pwVWAP", "mVWAP_vivo": "mVWAP", "mVAH_vivo": "mVAH", "mVAL_vivo": "mVAL",
    "r7D_vivo": "7D", "r30D_vivo": "30D",
}


def elegir(s: pl.DataFrame, semilla: int = 7) -> pl.DataFrame:
    rnd = random.Random(semilla)
    s = s.with_columns(
        bgn=pl.col("gn").abs().cut(TRAMOS_GN[1:-1], labels=["chica", "media", "grande"]),
        bxg=pl.col("xg").abs().cut(TRAMOS_XG[1:-1], labels=["chica", "media", "grande"]),
        dia=pl.from_epoch("open_time", time_unit="ms").dt.date(),
        finde=pl.from_epoch("open_time", time_unit="ms").dt.weekday() >= 6,
    )
    celdas = [(g, x) for g in ("chica", "media", "grande") for x in ("chica", "media", "grande")]
    combos = [(l, t) for l in ("long", "short") for t in ("continuacion", "rebote")]
    elegidos, dias, k = [], set(), 0
    filas = s.to_dicts()
    rnd.shuffle(filas)
    por_clave: dict = {}
    for f in filas:
        por_clave.setdefault((f["bgn"], f["bxg"], f["lado"], f["tipo"]), []).append(f)
    # recorrer celdas × combinaciones en ronda hasta juntar N_CASOS, con 4 de fin de semana como mínimo
    while len(elegidos) < N_CASOS and k < 10_000:
        celda, combo = celdas[k % len(celdas)], combos[(k // len(celdas)) % len(combos)]
        k += 1
        quiero_finde = sum(f["finde"] for f in elegidos) < 4 and k % 5 == 0
        for f in por_clave.get((*celda, *combo), []):
            if f["dia"] in dias or (quiero_finde and not f["finde"]):
                continue
            elegidos.append(f)
            dias.add(f["dia"])
            break
    return pl.DataFrame(elegidos).sort("open_time")


def a_json(caso: dict, df: pl.DataFrame, i: int) -> dict:
    t = caso["open_time"]
    v1 = df.filter(pl.col("open_time").is_between(t - (VELAS_1M - 1) * ind.MS_MIN, t))
    r = lambda x: None if x is None else round(float(x), 2)  # noqa: E731
    velas = [{"t": x["open_time"] // 1000, "o": x["open"], "h": x["high"], "l": x["low"], "c": x["close"],
              "e11": r(x["ema11"]), "e25": r(x["ema25"]), "vw": r(x["vwap_d"]),
              "p1": r(x["vwap_d_p1"]), "m1": r(x["vwap_d_m1"]), "p2": r(x["vwap_d_p2"]), "m2": r(x["vwap_d_m2"]),
              "bu": r(x["ash_bulls"]), "be": r(x["ash_bears"]), "rv": round(x["rvol"], 3) if x["rvol"] is not None else None}
             for x in v1.iter_rows(named=True)]
    # 5m: velas armadas con las 1m hasta t; la última en formación. EMAs/ASH de 5m: valor al cierre de cada vela de
    # 5m y, en la que está en formación, el valor vivo al minuto t.
    v5src = df.filter(pl.col("open_time").is_between(t - VELAS_5M * 5 * ind.MS_MIN, t)).with_columns(
        b=pl.col("open_time") // (5 * ind.MS_MIN) * (5 * ind.MS_MIN))
    v5 = v5src.group_by("b", maintain_order=True).agg(
        o=pl.col("open").first(), h=pl.col("high").max(), l=pl.col("low").min(), c=pl.col("close").last(),
        e11=pl.col("ema11_5m_vivo").last(), e25=pl.col("ema25_5m_vivo").last(),
        bu=pl.col("ash_bulls_5m_vivo").last(), be=pl.col("ash_bears_5m_vivo").last())
    velas5 = [{"t": x["b"] // 1000, "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"], "e11": r(x["e11"]),
               "e25": r(x["e25"]), "bu": r(x["bu"]), "be": r(x["be"])} for x in v5.iter_rows(named=True)]
    ult = df.filter(pl.col("open_time") == t).row(0, named=True)
    niveles = [{"n": nom, "p": r(ult[c])} for c, nom in ETIQUETAS.items() if ult[c] is not None]
    u = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc)
    return {"id": f"c{i:02d}", "t": t // 1000, "utc": u.strftime("%Y-%m-%d %H:%M"),
            "art": (u - dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "dow": u.strftime("%a"),
            "lado": caso["lado"], "tipo": caso["tipo"], "velas": velas, "velas5": velas5, "niveles": niveles,
            # para el análisis posterior (no se muestran en la página)
            "_gn": round(caso["gn"], 4), "_xg": round(caso["xg"], 4), "_dist5m_atr": round(caso["dist5m_atr"], 3)}


def main() -> None:
    s = senales.calcular()
    m = elegir(s)
    df = ind.cargar("2022-12", "2024-12")
    casos = [a_json(c, df, i + 1) for i, c in enumerate(m.iter_rows(named=True))]
    out = RAIZ / "reports" / "f2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "casos.json").write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
    print(len(casos), "casos")
    print(m.group_by("lado", "tipo").len().sort("lado", "tipo"))
    print(m.group_by("bgn", "bxg").len().sort("bgn", "bxg"))
    print("fin de semana:", int(m["finde"].sum()))


if __name__ == "__main__":
    main()
