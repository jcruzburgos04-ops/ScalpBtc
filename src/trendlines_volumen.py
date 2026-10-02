"""Ruptura de trendline v2 confirmada por volumen (Juan 2026-10-02: "con volumen"; "probá con ventas/longs a favor, o
liquidación de los contrarios a lo que abro").

Base: rupturas v2 (línea limpia, vence a 2× la distancia entre pivots), pivots de 10, EMA 200 de 45m a favor, TP en
el nivel opuesto (primero a ≥ 2R), SL ext10 ± 0,25 ATR. Confirmaciones de la vela que rompe (fijadas antes):
  sin confirmación · RVOL ≥ 1,5 · delta a favor ≥ 0,2 (compras − ventas taker / volumen; ≤ −0,2 en un short) ·
  liquidación contraria (proxy de `liq_proxy.py` en la vela de ruptura o las 2 anteriores: shorts liquidados para un
  long, longs liquidados para un short) · delta o liquidación · RVOL ≥ 1,5 y (delta o liquidación).
Salidas: TP nivel + 50 % en +1R, TP nivel sin parcial. Motor 1 s, hasta 4 patas, sin comisiones.
Calibración 2023–2024 → test 2025-01..2026-06. Elección: máximo R con gana ≥ 50 % en calibración.
Salida: reports/trendlines/trendlines_volumen.md
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

import a_tp_nivel as atn
import motor
from f3_correr import filtro_ema45
from liq_proxy import por_minuto as liq_por_minuto
from nuevas_mr import COLS, met
from trendlines import senales_tl

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trendlines"


def con_liq(s: pl.DataFrame, desde: str, hasta: str) -> pl.DataFrame:
    q = liq_por_minuto(desde, hasta).sort("open_time").with_columns(
        ls3=pl.col("liq_s").cast(pl.Int8).rolling_max(3), ll3=pl.col("liq_l").cast(pl.Int8).rolling_max(3))
    x = s.join(q.select("open_time", "ls3", "ll3"), on="open_time", how="left")
    return x.with_columns(liq_contra=pl.when(pl.col("lado") == "long").then(pl.col("ls3")).otherwise(pl.col("ll3"))
                          .fill_null(0) > 0).drop("ls3", "ll3")


def main() -> None:
    atn.NIV = atn.NIV + ["mVAH_vivo", "mVAL_vivo", "rVAH", "rVAL"]
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    delta = (sg * pl.col("delta1")) >= 0.2
    rv = pl.col("rvol") >= 1.5
    liq = pl.col("liq_contra")
    confs = {"sin confirmación de volumen": pl.lit(True), "RVOL ≥ 1,5": rv, "delta a favor ≥ 0,2": delta,
             "liquidación contraria (proxy)": liq, "delta o liquidación": delta | liq, "RVOL ≥ 1,5 y (delta o liquidación)": rv & (delta | liq)}
    res = {}
    for k, (d, h) in {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}.items():
        D = motor.Datos(d, h)
        s0 = con_liq(senales_tl(d, h, 10, v2=True), d, h)
        s0 = atn.con_tp(filtro_ema45(s0, d).drop("tp"), d, h)
        for cn, cond in confs.items():
            s = s0.filter(cond)
            for sal, P in (("TP nivel + 50 % en +1R", motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)),
                           ("TP nivel sin parcial", motor.Params(sl_por="last"))):
                patas, _ = motor.simular(D, s.select(COLS), P, s["open_time"].sort().to_numpy())
                nom = f"{cn} · {sal}"
                res[(nom, k)] = met(motor.a_tabla(patas))
                print(k, nom, s.height, res[(nom, k)][0], flush=True)
    noms = list(dict.fromkeys(n for n, _ in res))
    l = ["Ruptura de trendline v2 · pivots 10 · EMA 200 45m a favor · TP nivel opuesto ≥ 2R · patas · gana · R medio "
         "[IC 95 % por posición] · motor 1 s, sin comisiones.", "",
         "| Confirmación de la vela que rompe · salida | Calibración 2023–2024 | Test 2025-01..2026-06 |", "|---|---|---|"]
    for n in noms:
        l.append(f"| {n} | {res[(n, 'cal')][0]} | {res[(n, 'test')][0]} |")
    ok = [n for n in noms if res[(n, "cal")][1] >= 0.5]
    if ok:
        el = max(ok, key=lambda n: res[(n, "cal")][2])
        l += ["", f"Elegida en calibración (máximo R con gana ≥ 50 %): {el} → test {res[(el, 'test')][0]}"]
    txt = "\n".join(l)
    (OUT / "trendlines_volumen.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
