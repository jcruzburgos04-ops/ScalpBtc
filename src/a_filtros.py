"""Estrategia A (señal de Juan) + lo aprendido del trader: filtro de tendencia EMA 200 de 45m y breakeven a +0,5R.
TP 2R, SL por last, hasta 4 patas, sin comisiones. Calibración 2023–2024 → test 2025-01..2026-06.
El filtro se aplica a las patas ya simuladas (aproximación: no re-simula las posiciones que se liberarían).
IC por bloques de posición. Salida: reports/f3/a_filtros.md"""
from pathlib import Path

import numpy as np
import polars as pl

from b2_tendencias import ema_tf
from datos import leer_velas_1m

RAIZ = Path(__file__).resolve().parent.parent
F3 = RAIZ / "reports" / "f3"


def ema45() -> pl.DataFrame:
    k = leer_velas_1m("2022-01", "2026-06").select("open_time", "close").sort("open_time")
    v, _ = ema_tf(k["open_time"].to_numpy(), k["close"].to_numpy(), 45, 200)
    return k.with_columns(e45=pl.Series(v))


def con_filtro(t: pl.DataFrame, e: pl.DataFrame) -> pl.DataFrame:
    x = t.join(e, left_on="t_senal", right_on="open_time", how="left")
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    return x.filter((sg * (pl.col("close") - pl.col("e45"))) > 0)


def met(t: pl.DataFrame) -> str:
    r = t["r"].to_numpy()
    pos = t.group_by("pos_id").agg(pl.col("r").sum(), pl.len())
    rp, npat = pos["r"].to_numpy(), pos["len"].to_numpy()
    rng = np.random.default_rng(0)
    bs = []
    for _ in range(1000):
        i = rng.integers(0, rp.size, rp.size)
        bs.append(rp[i].sum() / npat[i].sum())
    return f"{r.size} | {(r > 0).mean():.0%} | {r.mean():+.3f} [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}]"


def main() -> None:
    e = ema45()
    l = ["| Variante | Calib. 2023–2024: patas · gana · R medio [IC 95 %] | Test 2025–2026/06: patas · gana · R medio [IC 95 %] |",
         "|---|---|---|"]
    for nom, suf in (("A base", ""), ("A + breakeven 0,5R", "_be0.5")):
        c = pl.read_parquet(F3 / f"trades_2023-01_2024-12_tp2_slip0_sllast{suf}.parquet")
        t = pl.read_parquet(F3 / f"trades_2025-01_2026-06_tp2_slip0_sllast{suf}.parquet")
        l.append(f"| {nom} | {met(c)} | {met(t)} |")
        l.append(f"| {nom} + EMA 200 de 45m | {met(con_filtro(c, e))} | {met(con_filtro(t, e))} |")
    txt = "\n".join(l)
    (F3 / "a_filtros.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
