"""F3 · 20 trades para que Juan audite el motor (CLAUDE.md §4.4).

Muestra estratificada de 2023–2024 (período de calibración) con todos los tipos de salida y de ambigüedad:
TP, SL, tope 24 h, cierre por invalidación, SL y TP en el mismo minuto, SL dudoso en el minuto de entrada,
mark reconstruido y patas de ampliación. Cada trade lleva: velas de 1m desde 30 min antes de la señal hasta 15 min
después de la salida, el mark 1m, las barras de 1 s alrededor de la salida (y el mark sintético cuando se usó), la
entrada, el SL, el TP y el motivo. Salida: reports/f3/auditoria/casos.json
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

import numpy as np
import polars as pl

import motor

RAIZ = Path(__file__).resolve().parent.parent
F = RAIZ / "reports" / "f3"
CUPOS = [  # (archivo, filtro, cantidad, etiqueta)
    ("sin", pl.col("motivo") == "TP", 4, "TP"),
    ("sin", (pl.col("motivo") == "SL") & (pl.col("ambiguo_tipo") == "") & (pl.col("pata") == 1), 4, "SL"),
    ("sin", pl.col("motivo") == "tope_24h", 2, "tope 24 h"),
    ("inv", pl.col("motivo") == "invalidacion", 3, "cierre por invalidación"),
    ("sin", pl.col("ambiguo_tipo") == "sl_y_tp_mismo_minuto", 2, "ambiguo: SL y TP en el mismo minuto"),
    ("sin", pl.col("ambiguo_tipo") == "sl_minuto_entrada", 2, "ambiguo: SL en el minuto de la entrada"),
    ("sin", pl.col("mark_reconstruido"), 1, "mark reconstruido"),
    ("sin", pl.col("pata") >= 2, 2, "pata de ampliación"),
]
ARCH = {"sin": "trades_2023-01_2024-12_tp2_slip0", "inv": "trades_2023-01_2024-12_tp2_inv_slip0"}
# Mini-auditoría tras los cambios de Juan (SL por last, invalidación por pata con 30 min reales y ≥ 7 cruces)
ARCH2 = {"sin": "trades_2023-01_2024-12_tp2_slip0_sllast", "inv": "trades_2023-01_2024-12_tp2_inv_slip0_sllast"}
CUPOS2 = [
    ("sin", pl.col("motivo") == "TP", 2, "TP (por last)"),
    ("sin", (pl.col("motivo") == "SL") & (pl.col("pata") == 1), 3, "SL (por last)"),
    ("inv", (pl.col("motivo") == "invalidacion") & (pl.col("pata") == 1), 3, "cierre por invalidación"),
    ("inv", (pl.col("motivo") == "invalidacion") & (pl.col("pata") >= 2), 1, "cierre por invalidación (pata de ampliación)"),
    ("sin", pl.col("pata") >= 2, 1, "pata de ampliación"),
]
ART = dt.timedelta(hours=-3)


def hora(ms: int) -> str:
    return (dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc) + ART).strftime("%Y-%m-%d %H:%M:%S")


def caso(r: dict, etiqueta: str, version: str, i: int, modo: str = "mark") -> dict:
    mes0 = dt.datetime.fromtimestamp(r["t_senal"] / 1000, dt.timezone.utc).strftime("%Y-%m")
    mes1 = dt.datetime.fromtimestamp(r["salida_ts"] / 1000, dt.timezone.utc).strftime("%Y-%m")
    D = motor.Datos(mes0, mes1)
    a = D.idx(r["t_senal"] - 30 * motor.MS_MIN)
    z = min(D.idx(r["salida_ts"] // motor.MS_MIN * motor.MS_MIN + 15 * motor.MS_MIN), D.t.size - 1)
    if z - a > 400:  # trades largos: se muestran la entrada y la salida con un corte en el medio
        idx = list(range(a, a + 120)) + list(range(z - 200, z + 1))
    else:
        idx = list(range(a, z + 1))
    from datos import leer_velas_1m
    k = leer_velas_1m(mes0, mes1).sort("open_time")
    o, h, l, c = (k[x].to_numpy() for x in ("open", "high", "low", "close"))
    velas = [{"t": int(D.t[j]) // 1000, "o": float(o[j]), "h": float(h[j]), "l": float(l[j]), "c": float(c[j]),
              "mh": None if np.isnan(D.mh[j]) else float(D.mh[j]), "ml": None if np.isnan(D.ml[j]) else float(D.ml[j]),
              "mc": None if np.isnan(D.mc[j]) else float(D.mc[j])} for j in idx]
    # 1 s alrededor de la salida (±90 s) y mark sintético del minuto de la salida
    s0 = r["salida_ts"] // motor.MS_MIN * motor.MS_MIN
    b = D.barras_1s(s0 - 90_000, s0 + 150_000)
    seg = [{"t": int(b["ts"][j]) // 1000, "o": float(b["o"][j]), "h": float(b["h"][j]), "l": float(b["l"][j]),
            "c": float(b["c"][j])} for j in range(b["ts"].size)]
    if modo == "last":  # sin mark ni trayectoria sintética
        for v in velas:
            v["mh"] = v["ml"] = v["mc"] = None
        sint, rep = {}, False
    else:
        sint, rep = motor._sintetico(D, D.idx(s0), r["fill_ts"])
    sint_l = [{"t": int(sint["ts"][j]) // 1000, "sh": float(sint["sh"][j]), "sl": float(sint["sl"][j])}
              for j in range(sint["ts"].size)] if "sh" in sint else []
    lg = r["lado"] == "long"
    return {
        "id": f"t{i:02d}", "etiqueta": etiqueta, "version": "con invalidación" if version == "inv" else "sin invalidación",
        "lado": r["lado"], "pos_id": r["pos_id"], "pata": r["pata"], "tipo": r["tipo"],
        "senal": hora(r["t_senal"]), "senal_t": r["t_senal"] // 1000, "fill_hora": hora(r["fill_ts"]), "fill_t": r["fill_ts"] // 1000,
        "salida_hora": hora(r["salida_ts"]), "salida_t": r["salida_ts"] // 1000,
        "close_senal": r["close_senal"], "fill": r["fill"], "sl": r["sl"], "tp": r["tp"], "salida": r["salida"],
        "motivo": r["motivo"], "motivo_opt": r["motivo_opt"], "r": round(r["r"], 2), "r_opt": round(r["r_opt"], 2),
        "ambiguo_tipo": r["ambiguo_tipo"], "sintetico_reproduce": bool(rep), "mark_reconstruido": r["mark_reconstruido"],
        "riesgo_usd": round(r["riesgo"], 1), "riesgo_atr": round(r["riesgo"] / r["atr14"], 2),
        "nocional_x": round(r["nocional_x_equity"], 1), "minutos": round(r["minutos"], 1),
        "velas": velas, "seg": seg, "sint": sint_l, "modo": modo,
    }


def mini(semilla: int = 11) -> None:
    rnd = random.Random(semilla)
    tablas = {k: pl.read_parquet(F / f"{v}.parquet") for k, v in ARCH2.items()}
    previos = {c["id"]: c for c in json.loads((F / "auditoria" / "casos.json").read_text())}
    casos = []
    # los mismos trades t06 y t08 de la auditoría anterior, resueltos con la regla nueva
    for tid in ("t06", "t08"):
        c0 = previos[tid]
        r = tablas["sin"].filter((pl.col("t_senal") == c0["senal_t"] * 1000) & (pl.col("lado") == c0["lado"]))
        if r.height:
            casos.append(caso(r.row(0, named=True), f"{tid} de la auditoría anterior, ahora con SL por last", "sin", len(casos) + 1, "last"))
    for ver, filtro, n, et in CUPOS2:
        filas = tablas[ver].filter(filtro).to_dicts()
        rnd.shuffle(filas)
        for r in filas[:n]:
            casos.append(caso(r, et, ver, len(casos) + 1, "last"))
    out = F / "auditoria2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "casos.json").write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
    print(len(casos), "trades;", [c["etiqueta"] for c in casos])


def main(semilla: int = 3) -> None:
    rnd = random.Random(semilla)
    tablas = {k: pl.read_parquet(F / f"{v}.parquet") for k, v in ARCH.items()}
    casos, usados = [], set()
    for ver, filtro, n, et in CUPOS:
        t = tablas[ver].filter(filtro)
        filas = t.to_dicts()
        rnd.shuffle(filas)
        for r in filas[:n * 3]:
            if len([c for c in casos if c["etiqueta"] == et]) >= n:
                break
            if (ver, r["pos_id"], r["pata"]) in usados:
                continue
            usados.add((ver, r["pos_id"], r["pata"]))
            casos.append(caso(r, et, ver, len(casos) + 1))
    out = F / "auditoria"
    out.mkdir(parents=True, exist_ok=True)
    (out / "casos.json").write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
    print(len(casos), "trades;", {c["etiqueta"]: sum(1 for x in casos if x["etiqueta"] == c["etiqueta"]) for c in casos})


if __name__ == "__main__":
    import sys
    mini() if "--mini" in sys.argv else main()
