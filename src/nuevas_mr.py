"""Estrategias nuevas (Juan 2026-10-02): retroceso simple a favor de la tendencia (opción 2) y reversión a la media con
las Liquidation Bands de Leviathan.

Liquidation Bands (Leviathan, código protegido; descripción pública: bandas a la distancia aproximada del precio de
liquidación de 100x/75x/50x/25x alrededor de una EMA o del VWAP). SUPUESTO: banda = base × (1 ± 1/L) → 1 %, 1,33 %,
2 %, 4 % (sin margen de mantenimiento). Bases: VWAP de sesión y EMA 200 de 1m. PENDIENTE: confirmar con la config de Juan.

Señales (long; short espejo), al cierre de la vela de 1m, dentro de la ventana operativa:
  RET   retroceso a favor de la tendencia: precio sobre la EMA 200 de 45m; en las últimas 10 velas el precio retrocedió
        ≥ 1 ATR desde el máximo de 60 min; la vela actual cierra sobre el máximo de la anterior (gira a favor).
  LB_x  rechazo de la banda de 100x: el mínimo de la vela tocó la banda inferior (base × 0,99) y la vela cerró de vuelta
        por encima, verde. x = vwap / ema. Variante +t: además a favor de la EMA 200 de 45m.
SL: extremo de 10 velas ± 0,25 ATR (igual que A). Motor de 1 s, hasta 4 patas, sin comisiones.
Salidas: (a) TP 3R con 50 % en +1R; (b) TP 2R sin parcial; (c) solo LB: TP en la base (la media) con R ≥ 2.
Calibración 2023–2024 → test 2025-01..2026-06. Elección (fijada antes): máximo R con gana ≥ 50 % en calibración.
Salida: reports/mr/nuevas.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

import indicadores as ind
import motor
import senales
from f3_correr import SL_MARGEN_ATR, filtro_ema45
from indicadores import ema

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "mr"
COLS = ["open_time", "lado", "en_ventana", "sl", "tp", "tp_r", "tipo", "atr14", "z_favor", "cruces_ash30", "rvol", "dist5m_atr"]


def base(desde: str, hasta: str) -> pl.DataFrame:
    df = ind.cargar(desde, hasta).select("open_time", "open", "high", "low", "close", "atr14", "vwap_d", "rvol").sort("open_time")
    return df.with_columns(
        ema200=pl.Series(ema(df["close"].to_numpy(), 200)),
        min10=pl.col("low").rolling_min(10), max10=pl.col("high").rolling_max(10),
        max60=pl.col("high").rolling_max(60), min60=pl.col("low").rolling_min(60),
        en_ventana=senales.ventana_operativa(pl.col("open_time")))


def senales_de(df: pl.DataFrame, tipo: str) -> pl.DataFrame:
    out = []
    for lado, sg in (("long", 1.0), ("short", -1.0)):
        if tipo == "RET":
            if sg > 0:
                cond = ((pl.col("max60") - pl.col("min10")) >= pl.col("atr14")) & (pl.col("close") > pl.col("high").shift(1))
            else:
                cond = ((pl.col("max10") - pl.col("min60")) >= pl.col("atr14")) & (pl.col("close") < pl.col("low").shift(1))
        else:
            b = pl.col("vwap_d") if tipo.startswith("LB_vwap") else pl.col("ema200")
            if sg > 0:
                banda = b * (1 - 0.01)
                cond = (pl.col("low") <= banda) & (pl.col("close") > banda) & (pl.col("close") > pl.col("open"))
            else:
                banda = b * (1 + 0.01)
                cond = (pl.col("high") >= banda) & (pl.col("close") < banda) & (pl.col("close") < pl.col("open"))
        x = df.filter(cond.fill_null(False) & pl.col("en_ventana")).with_columns(
            lado=pl.lit(lado),
            sl=(pl.col("min10") - SL_MARGEN_ATR * pl.col("atr14")) if sg > 0 else (pl.col("max10") + SL_MARGEN_ATR * pl.col("atr14")),
            media=pl.col("vwap_d") if tipo.startswith("LB_vwap") else pl.col("ema200"))
        out.append(x)
    s = pl.concat(out).sort("open_time")
    if tipo == "RET" or tipo.endswith("+t"):
        s = filtro_ema45(s, "2022-01")
    return s.with_columns(tipo=pl.lit(tipo), z_favor=pl.lit(0.0), cruces_ash30=pl.lit(0), dist5m_atr=pl.lit(0.0))


def correr(D, s, salida: str, todas) -> pl.DataFrame:
    if salida == "media":
        s = s.with_columns(tp=pl.col("media"), tp_r=pl.lit(None, dtype=pl.Float64))
        P = motor.Params(sl_por="last", r_min=2.0)
    else:
        tp_r = 3.0 if salida == "3R+parcial" else 2.0
        s = s.with_columns(tp=pl.lit(None, dtype=pl.Float64), tp_r=pl.lit(tp_r))
        P = motor.Params(sl_por="last", parcial_r=1.0 if salida == "3R+parcial" else None, parcial_f=0.5)
    patas, _ = motor.simular(D, s.select(COLS), P, todas)
    return motor.a_tabla(patas)


def met(t: pl.DataFrame) -> tuple[str, float, float]:
    if t.height == 0:
        return "0", 0.0, 0.0
    r = t["r"].to_numpy()
    pos = t.group_by("pos_id").agg(pl.col("r").sum(), pl.len())
    rp, n = pos["r"].to_numpy(), pos["len"].to_numpy()
    rng = np.random.default_rng(0)
    bs = [rp[i].sum() / n[i].sum() for i in (rng.integers(0, rp.size, rp.size) for _ in range(1000))]
    return (f"{r.size} · {(r > 0).mean():.0%} · {r.mean():+.3f} [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}]",
            float((r > 0).mean()), float(r.mean()))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tipos = ["RET", "LB_vwap", "LB_vwap+t", "LB_ema", "LB_ema+t"]
    per = {"cal": ("2023-01", "2024-12"), "test": ("2025-01", "2026-06")}
    res = {}
    for k, (d, h) in per.items():
        df = base(d, h)
        D = motor.Datos(d, h)
        for tipo in tipos:
            s = senales_de(df, tipo)
            todas = s["open_time"].sort().to_numpy()
            for salida in (["3R+parcial", "2R"] + (["media"] if tipo.startswith("LB") else [])):
                t = correr(D, s, salida, todas)
                t.write_parquet(OUT / f"{tipo}_{salida}_{k}.parquet")
                res[(tipo, salida, k)] = met(t)
                print(tipo, salida, k, res[(tipo, salida, k)][0], flush=True)
    l = ["Calibración 2023–2024 → test 2025-01..2026-06 · patas · gana · R medio [IC 95 % por posición] · motor 1 s, sin comisiones.", "",
         "| Señal | Salida | Calibración | Test |", "|---|---|---|---|"]
    for tipo in tipos:
        for salida in (["3R+parcial", "2R"] + (["media"] if tipo.startswith("LB") else [])):
            l.append(f"| {tipo} | {salida} | {res[(tipo, salida, 'cal')][0]} | {res[(tipo, salida, 'test')][0]} |")
    ok = [(k[0], k[1]) for k, v in res.items() if k[2] == "cal" and v[1] >= 0.5]
    if ok:
        el = max(ok, key=lambda x: res[(x[0], x[1], "cal")][2])
        l += ["", f"Elegida en calibración (máximo R con gana ≥ 50 %): {el[0]} · {el[1]} → test {res[(el[0], el[1], 'test')][0]}"]
    txt = "\n".join(l)
    (OUT / "nuevas.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
