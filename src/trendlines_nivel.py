"""Ruptura de línea de tendencia + TP en el nivel opuesto (lo que mostró Juan en su gráfico del 2-oct-2026: long al romper
la línea bajista con TP en MNDAY-H; short al romper la alcista con TP en mVAH/rVAH).
TP = primer nivel a ≥ 2R entre MNDAY-H/L, VWAP ±2σ sesión, dVAH/dVAL, VWAP ±2σ semanal (a_tp_nivel.NIV) + mVAH/mVAL y
rVAH/rVAL. Pivots 10 y 20, con y sin EMA 45m, con y sin 50 % en +1R. Motor 1 s, sin comisiones.
Calibración 2023–2024 → test 2025-01..2026-06. Salida: reports/trendlines/trendlines_nivel.md"""
from pathlib import Path
import polars as pl
import a_tp_nivel as atn
import motor
from f3_correr import filtro_ema45
from nuevas_mr import COLS, met
from trendlines import senales_tl

atn.NIV = atn.NIV + ["mVAH_vivo", "mVAL_vivo", "rVAH", "rVAL"]
OUT = Path(__file__).resolve().parent.parent / "reports" / "trendlines"
res = {}
for k, (d, h) in {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}.items():
    D = motor.Datos(d, h)
    for n in (10, 20):
        s0 = senales_tl(d, h, n)
        for filtro in ("", " + EMA 45m"):
            s = filtro_ema45(s0, d) if filtro else s0
            s = atn.con_tp(s.drop("tp"), d, h)
            for sal, P in (("TP nivel + 50 % en +1R", motor.Params(sl_por="last", parcial_r=1.0, parcial_f=0.5)),
                           ("TP nivel sin parcial", motor.Params(sl_por="last"))):
                patas, _ = motor.simular(D, s.select(COLS), P, s["open_time"].sort().to_numpy())
                nom = f"pivots {n}{filtro} · {sal}"
                res[(nom, k)] = met(motor.a_tabla(patas))
                print(k, nom, res[(nom, k)][0], flush=True)
noms = list(dict.fromkeys(x for x, _ in res))
l = ["Ruptura de trendline + TP en el nivel opuesto · patas · gana · R [IC 95 %] · motor 1 s, sin comisiones.", "",
     "| Variante | Calibración 2023–2024 | Test 2025-01..2026-06 |", "|---|---|---|"]
l += [f"| {x} | {res[(x, 'cal')][0]} | {res[(x, 'test')][0]} |" for x in noms]
ok = [x for x in noms if res[(x, "cal")][1] >= 0.5]
if ok:
    el = max(ok, key=lambda x: res[(x, "cal")][2])
    l += ["", f"Elegida en calibración (gana ≥ 50 %): {el} → test {res[(el, 'test')][0]}"]
(OUT / "trendlines_nivel.md").write_text("\n".join(l) + "\n")
print("\n".join(l))
