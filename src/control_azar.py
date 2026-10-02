"""Control con lado al azar (misma hora de señal de A, lado sorteado, SL en el extremo de 10 velas del lado sorteado,
TP 2R, 1 pata) con y sin el filtro EMA 200 de 45m, en calibración (2023–2024) y test (2025-01..2026-06), 3 sorteos.
Compara contra la señal real de A con 1 pata. Salida: reports/f3/control_azar.md"""
from pathlib import Path
import numpy as np, polars as pl
import motor
from f3_correr import SL_MARGEN_ATR, preparar, filtro_ema45

RAIZ = Path(__file__).resolve().parent.parent
COLS = ["open_time", "lado", "en_ventana", "sl", "tp", "tp_r", "tipo", "atr14", "z_favor", "cruces_ash30", "rvol", "dist5m_atr"]


def correr(D, s, todas):
    patas, _ = motor.simular(D, s.select(COLS), motor.Params(sl_por="last", max_patas=1), todas.sort().to_numpy())
    r = motor.a_tabla(patas)["r"].to_numpy()
    return f"{r.size} · {(r > 0).mean():.1%} · {r.mean():+.3f}"


def con_sl(s):
    return s.with_columns(sl=pl.when(pl.col("lado") == "long").then(pl.col("min_low10") - SL_MARGEN_ATR * pl.col("atr14"))
                          .otherwise(pl.col("max_high10") + SL_MARGEN_ATR * pl.col("atr14")))


l = ["| Período | Variante | trades · gana · R medio |", "|---|---|---|"]
for d, h in (("2023-01", "2024-12"), ("2025-01", "2026-06")):
    s, todas = preparar(d, h, 2.0)
    D = motor.Datos(d, h)
    l.append(f"| {d[:4]}–{h[:4]} | Señal A real | {correr(D, s, todas)} |")
    l.append(f"| {d[:4]}–{h[:4]} | Señal A real + EMA 200 45m | {correr(D, filtro_ema45(s, d), todas)} |")
    for semilla in (1, 2, 3):
        rng = np.random.default_rng(semilla)
        z = con_sl(s.with_columns(lado=pl.Series(np.where(rng.random(s.height) < 0.5, "long", "short"))))
        l.append(f"| {d[:4]}–{h[:4]} | Lado al azar (sorteo {semilla}) | {correr(D, z, todas)} |")
        l.append(f"| {d[:4]}–{h[:4]} | Lado al azar + EMA 200 45m (sorteo {semilla}) | {correr(D, filtro_ema45(z, d), todas)} |")
    print("\n".join(l), flush=True)
(RAIZ / "reports/f3/control_azar.md").write_text("\n".join(l) + "\n")
