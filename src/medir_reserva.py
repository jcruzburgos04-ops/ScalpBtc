"""Medición mensual de las estrategias CONGELADAS en la reserva (oct–dic 2026), sin cambiar ninguna regla.

Uso: python src/medir_reserva.py AAAA-MM      (antes: python src/actualizar.py AAAA-MM)

Solo para esta medición se abre el mes pedido de la reserva: datos.RESERVA pasa a empezar el mes siguiente, así
indicadores.cargar devuelve ese mes y nada posterior.
  1. B2 final (b2_final.py): señal, filtro EMA 200 de 45m y salida congelados (SL ext10 ± 0,25 ATR, TP VWAP,
     breakeven +1R), una pata, velas de 1m. Calentamiento con los 2 meses previos; solo señales del mes.
  2. A congelada: = f3_correr.py MES MES --ema45 --parcial 1 --parcial_f 0.5 --tp_r 3 (motor 1 s, hasta 4 patas).
  3. A + EMA 45m + TP en el nivel opuesto, sin parcial: = a_tp_nivel.medir(MES, MES).
Se compara contra el test (2023–2025 para B2; 2025-01..2026-06 para A). Salida: reports/reserva/AAAA-MM.md
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import polars as pl

import datos

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "reserva"
TEST = {"B2": ("2 619", "13 %", "+0,064 [−0,011; +0,148]"), "A": ("8 870", "52 %", "+0,080 [+0,052; +0,113]"),
        "A_nivel": ("–", "23 %", "+0,136")}
HUECOS = {"2026-10": [("2026-10-28", "Binance no publicó el 28-oct (ni mensual ni diario): sin velas ni ticks")]}


def mes_siguiente(mes: str) -> str:
    a, m = map(int, mes.split("-"))
    return f"{a + (m == 12)}-{m % 12 + 1:02d}"


def mes_menos(mes: str, k: int) -> str:
    a, m = map(int, mes.split("-"))
    m -= k
    while m < 1:
        a, m = a - 1, m + 12
    return f"{a}-{m:02d}"


def ic_pos(t: pl.DataFrame) -> tuple[float, float]:
    pos = t.group_by("pos_id").agg(pl.col("r").sum(), pl.len())
    rp, n = pos["r"].to_numpy(), pos["len"].to_numpy()
    rng = np.random.default_rng(0)
    bs = [rp[i].sum() / n[i].sum() for i in (rng.integers(0, rp.size, rp.size) for _ in range(2000))]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def ic_simple(r: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(0)
    bs = [r[rng.integers(0, r.size, r.size)].mean() for _ in range(2000)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def fila(nombre: str, r: np.ndarray, ic: tuple[float, float], test: tuple[str, str, str], extra: str = "") -> str:
    if r.size == 0:
        return f"| {nombre} | 0 | – | – | {test[0]} · {test[1]} · {test[2]} |{extra}"
    return (f"| {nombre} | {r.size} | {(r > 0).mean():.0%} | {r.mean():+.3f} [{ic[0]:+.3f}; {ic[1]:+.3f}] | "
            f"{test[0]} · {test[1]} · {test[2]} |{extra}")


def main(mes: str) -> None:
    datos.RESERVA = (mes_siguiente(mes), "2026-12")        # abre solo `mes` de la reserva
    import a_tp_nivel as atn
    import b2_final
    import b2_tendencia as bten
    import b2_tp
    import motor
    import trader_sep as ts
    import volumen
    from f3_correr import filtro_ema45, preparar
    from nuevas_mr import COLS

    ini = int(dt.datetime.fromisoformat(mes + "-01").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    fin = int(dt.datetime.fromisoformat(mes_siguiente(mes) + "-01").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    huecos = [(int(dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp() * 1000), nota)
              for d, nota in HUECOS.get(mes, [])]

    def cruza_hueco(t: pl.DataFrame) -> pl.Series:
        m = pl.lit(False)
        for h0, _ in huecos:
            m = m | ((pl.col("fill_ts") < h0 + 86_400_000) & (pl.col("salida_ts") > h0))
        return t.select(m.alias("x"))["x"] if t.height else pl.Series([], dtype=pl.Boolean)

    # 1. B2 final
    d0 = mes_menos(mes, 2)
    m = volumen.agregar(ts.base(d0, mes), d0, mes, con_segundos=False).select(bten.COLS)
    m2, s = b2_final.preparar(m)
    s_mes = s.filter(pl.col("t_senal").is_between(ini, fin - 1))
    r_b2 = b2_tp.simular(m2, s_mes, *b2_final.SALIDA)
    r_b2_sin = np.array([])
    if huecos:      # sensibilidad: sin las señales del día anterior al hueco (pueden cruzarlo)
        h0 = huecos[0][0]
        r_b2_sin = b2_tp.simular(m2, s_mes.filter(~pl.col("t_senal").is_between(h0 - 86_400_000, h0 - 1)), *b2_final.SALIDA)

    # 2. A congelada y 3. A + TP nivel opuesto sin parcial
    D = motor.Datos(mes, mes)
    s_a, todas = preparar(mes, mes, 3.0)
    s_a = filtro_ema45(s_a, mes)
    t_a = motor.a_tabla(motor.simular(D, s_a.select(COLS), motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5),
                                      todas.sort().to_numpy())[0])
    s_n, todas_n = preparar(mes, mes, 2.0)
    s_n = atn.con_tp(filtro_ema45(s_n, mes), mes, mes)
    t_n = motor.a_tabla(motor.simular(D, s_n.select(COLS), motor.Params(sl_por="last"), todas_n.sort().to_numpy())[0])

    OUT.mkdir(parents=True, exist_ok=True)
    for nom, t in (("A", t_a), ("A_nivel", t_n)):
        if t.height:
            t.write_parquet(OUT / f"{mes}_{nom}.parquet")
    l = [f"# Reserva · {mes} · estrategias congeladas", "",
         f"Medido el {dt.date.today():%Y-%m-%d}. Ninguna regla se cambió. Sin comisiones. R por pata (A) o por trade (B2), "
         "IC 95 % por bootstrap (A: por posición).", ""]
    for _, nota in huecos:
        l += [f"**Datos:** {nota}. Ese día no hay señales; las posiciones abiertas que lo cruzan se muestran aparte.", ""]
    l += ["| Estrategia | Trades | Gana | R medio [IC 95 %] | Test (trades · gana · R) |", "|---|---|---|---|---|"]
    l.append(fila("B2 final (B2 + EMA 200 45m, TP VWAP, BE +1R)", r_b2, ic_simple(r_b2) if r_b2.size else (0, 0), TEST["B2"]))
    if huecos:
        l.append(fila("  · sin las señales del día anterior al hueco", r_b2_sin, ic_simple(r_b2_sin) if r_b2_sin.size else (0, 0), TEST["B2"]))
    for nom, t, k in (("A congelada (EMA 45m + TP 3R + 50 % en +1R)", t_a, "A"), ("A + TP nivel opuesto, sin parcial", t_n, "A_nivel")):
        r = t["r"].to_numpy() if t.height else np.array([])
        l.append(fila(nom, r, ic_pos(t) if t.height else (0, 0), TEST[k]))
        if huecos and t.height:
            x = cruza_hueco(t)
            if x.sum():
                tt = t.filter(~x)
                l.append(fila(f"  · sin las {int(x.sum())} patas que cruzan el hueco", tt["r"].to_numpy(), ic_pos(tt), TEST[k]))
    if t_a.height:
        mot = t_a["motivo"].value_counts().sort("count", descending=True)
        l += ["", "A congelada, salidas: " + ", ".join(f"{a} {c}" for a, c in mot.iter_rows()) +
              f" · patas por día {t_a.height / ((fin - ini) / 86_400_000 - len(huecos)):.1f}"]
    txt = "\n".join(l)
    (OUT / f"{mes}.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main(sys.argv[1])
