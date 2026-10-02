"""Auditoría del motor y de los precios (pedido de Juan 2026-10-02: "asegurate de que no haya errores en los precios").

1. Control con azar: las mismas señales de A en 2025-01..2026-03, pero con el LADO sorteado (SL en el extremo de 10
   velas ± 0,25 ATR del lado sorteado, TP 2R). Sin ventaja, un motor correcto tiene que dar ≈ 33 % de ganadoras y
   R medio ≈ 0 (con TP 2R: P(gana) = 1/3 si el precio es un paseo al azar).
2. Recalculo independiente de 300 patas de A (test) con las barras de 1 s, sin usar el motor: fill = primer trade
   posterior al cierre de la vela de señal; SL y TP en grilla de 0,1; quién se toca primero; R. Se compara con lo que
   dio el motor.
3. Coherencia de precios: fill vs close de la vela de señal, SL del lado correcto, TP a 2R exacto, R de las patas con
   motivo SL = −1 y TP = +2 (sin slippage).
Salida: reports/f3/auditoria_motor.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import motor
from datos import leer_1s
from f3_correr import SL_MARGEN_ATR, preparar

RAIZ = Path(__file__).resolve().parent.parent
F3 = RAIZ / "reports" / "f3"


def azar() -> str:
    s, todas = preparar("2025-01", "2026-03", 2.0)
    rng = np.random.default_rng(7)
    lado = np.where(rng.random(s.height) < 0.5, "long", "short")
    s = s.with_columns(lado=pl.Series(lado)).with_columns(
        sl=pl.when(pl.col("lado") == "long").then(pl.col("min_low10") - SL_MARGEN_ATR * pl.col("atr14"))
        .otherwise(pl.col("max_high10") + SL_MARGEN_ATR * pl.col("atr14")))
    D = motor.Datos("2025-01", "2026-03")
    cols = ["open_time", "lado", "en_ventana", "sl", "tp", "tp_r", "tipo", "atr14", "z_favor", "cruces_ash30", "rvol", "dist5m_atr"]
    patas, _ = motor.simular(D, s.select(cols), motor.Params(sl_por="last", max_patas=1), todas.sort().to_numpy())
    t = motor.a_tabla(patas)
    r = t["r"].to_numpy()
    return (f"Lado al azar, TP 2R, 1 pata: {r.size} trades · gana {(r > 0).mean():.1%} · R medio {r.mean():+.4f} · "
            f"motivos {dict(t.group_by('motivo').len().rows())}")


def recalculo(n: int = 300) -> list[str]:
    t = pl.read_parquet(F3 / "trades_2025-01_2026-06_tp2_slip0_sllast.parquet")
    t = t.filter(pl.col("motivo").is_in(["TP", "SL"])).sample(n, seed=3)
    malos, ok = [], 0
    cache: dict[str, pl.DataFrame] = {}
    for r in t.iter_rows(named=True):
        mes = str(np.datetime64(r["fill_ts"], "ms"))[:7]
        if mes not in cache:
            cache[mes] = leer_1s(mes).select("ts", "h", "l", "c", "ms_first")
        b = cache[mes]
        sg = 1 if r["lado"] == "long" else -1
        # fill: el primer segundo con trades posterior al cierre de la vela de señal
        cierre = r["t_senal"] + 60_000
        f = b.filter(pl.col("ts") >= cierre).head(1)
        fill_ok = abs(f["ts"][0] - r["fill_ts"]) < 1000
        x = b.filter((pl.col("ts") > r["fill_ts"]) & (pl.col("ts") <= r["fill_ts"] + 86_400_000))
        h, l = x["h"].to_numpy(), x["l"].to_numpy()
        toca_tp = (h >= r["tp"]) if sg > 0 else (l <= r["tp"])
        toca_sl = (l <= r["sl"]) if sg > 0 else (h >= r["sl"])
        k_tp = int(np.argmax(toca_tp)) if toca_tp.any() else 10**9
        k_sl = int(np.argmax(toca_sl)) if toca_sl.any() else 10**9
        mio = "TP" if k_tp < k_sl else ("SL" if k_sl < k_tp else "ambiguo")
        r_mio = sg * ((r["tp"] if mio == "TP" else r["sl"]) - r["fill"]) / abs(r["fill"] - r["sl"])
        tp_2r = abs(sg * (r["tp"] - r["fill"]) / abs(r["fill"] - r["sl"]) - 2) < 0.01
        lado_sl = sg * (r["fill"] - r["sl"]) > 0
        if fill_ok and (mio == r["motivo"] or mio == "ambiguo") and abs(r_mio - r["r"]) < 0.02 and tp_2r and lado_sl:
            ok += 1
        else:
            malos.append(f"pos {r['pos_id']} pata {r['pata']}: motor {r['motivo']} {r['r']:+.2f} · recalculo {mio} {r_mio:+.2f} · "
                         f"fill ok {fill_ok} · TP=2R {tp_2r} · SL del lado correcto {lado_sl}")
    return [f"Recalculo independiente con barras de 1 s: {ok}/{n} patas coinciden."] + malos[:10]


def coherencia() -> list[str]:
    t = pl.read_parquet(F3 / "trades_2025-01_2026-06_tp2_slip0_sllast.parquet")
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    x = t.with_columns(dfill=sg * (pl.col("fill") - pl.col("close_senal")) / pl.col("riesgo"),
                       rtp=sg * (pl.col("tp") - pl.col("fill")) / pl.col("riesgo"))
    return [f"Patas: {t.height} · SL del lado correcto: {x.select((sg * (pl.col('fill') - pl.col('sl')) > 0).mean()).item():.1%}",
            f"TP a 2R del fill (±0,02): {x.select(((pl.col('rtp') - 2).abs() < 0.02).mean()).item():.1%} · mediana {x['rtp'].median():.3f}",
            f"Fill vs close de la señal: mediana {x['dfill'].median():+.4f} R, p1 {x['dfill'].quantile(0.01):+.3f} R, p99 {x['dfill'].quantile(0.99):+.3f} R",
            f"R de motivo SL: {x.filter(pl.col('motivo') == 'SL')['r'].describe()['value'].to_list()[2:5]} (media, desvío, mínimo)",
            f"R de motivo TP: {x.filter(pl.col('motivo') == 'TP')['r'].describe()['value'].to_list()[2:5]}",
            f"Motivos: {dict(t.group_by('motivo').len().rows())} · gana {(t['r'] > 0).mean():.1%}"]


def main() -> None:
    l = ["# Auditoría del motor y de los precios", "", "## 1. Control con lado al azar", "", azar(), "",
         "## 2. Recalculo independiente", ""] + recalculo() + ["", "## 3. Coherencia de precios (A, test)", ""] + coherencia()
    txt = "\n".join(l)
    (F3 / "auditoria_motor.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
