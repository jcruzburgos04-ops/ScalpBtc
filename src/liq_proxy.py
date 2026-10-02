"""Proxy de liquidaciones por minuto (§6b.3) y su validación contra liquidaciones reales.

Por qué proxy: Binance no publica liquidaciones de USD-M; lo único real y gratis es COIN-M BTCUSD_PERP
2023-06-25 → 2024-10-14 (`data/proc/liq_coinm/`). Para 2025–2026 hace falta un proxy desde aggTrades + OI.

Liquidación de SHORTS (= compras forzadas; sirve a una ruptura LONG), minuto m (vela cerrada, sin mirar adelante):
  barrido_b  nocional de las órdenes a mercado COMPRADORAS reconstruidas (ms, lado) que barren ≥ 3 precios (las
             liquidaciones son órdenes IOC que se comen el libro) con nocional ≥ 100 k USD, en USD.
  oi_cae     el último OI de 5m publicado al cierre del minuto bajó respecto del anterior (cierre de posiciones).
  liq_s      proxy = barrido_b ≥ umbral y oi_cae. Umbral = p90 móvil (7 días, minutos con barrido > 0) del barrido_b.
Liquidación de LONGS (sirve a una ruptura SHORT) = espejo con las vendedoras (liq_l).
Validación: en 2023-07..2024-09, proporción de minutos con liquidación real COIN-M del mismo lado cuando el proxy se
enciende vs cuando no (lift). Salida: reports/trendlines/liq_proxy.md
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "proc"
OUT = RAIZ / "reports" / "trendlines"
M = 60_000


def meses(desde: str, hasta: str) -> list[str]:
    return pl.date_range(pl.date(int(desde[:4]), int(desde[5:]), 1), pl.date(int(hasta[:4]), int(hasta[5:]), 1),
                         "1mo", eager=True).dt.strftime("%Y-%m").to_list()


def por_minuto(desde: str, hasta: str) -> pl.DataFrame:
    ms = meses(desde, hasta)
    o = pl.concat([pl.scan_parquet(PROC / "ordenes_grandes" / f"{m}.parquet")
                   .filter(pl.col("n_agg") >= 3)
                   .select(open_time=pl.col("ts") // M * M, buy="buy",
                           usd=pl.col("q").cast(pl.Float64) / 1000 * pl.col("pmin").cast(pl.Float64) / 100)
                   .group_by("open_time").agg(barrido_b=pl.col("usd").filter(pl.col("buy")).sum(),
                                              barrido_s=pl.col("usd").filter(~pl.col("buy")).sum()).collect()
                   for m in ms]).sort("open_time")
    oi = pl.concat([pl.read_parquet(PROC / "metrics_5m" / f"{m}.parquet", columns=["create_time", "sum_open_interest"])
                    for m in ms]).sort("create_time").unique("create_time", keep="first").sort("create_time")
    oi = oi.with_columns(d_oi=pl.col("sum_open_interest").diff())
    grilla = pl.DataFrame({"open_time": pl.int_range(o["open_time"].min(), o["open_time"].max() + M, M, eager=True)})
    x = grilla.join(o, on="open_time", how="left").with_columns(pl.col("barrido_b", "barrido_s").fill_null(0.0))
    # OI publicado con create_time ≤ cierre del minuto (open_time + 60 s)
    x = x.with_columns(cierre=pl.col("open_time") + M).join_asof(
        oi.select(pl.col("create_time").alias("cierre"), "d_oi"), on="cierre", strategy="backward").drop("cierre")
    p90 = lambda c: pl.when(pl.col(c) > 0).then(pl.col(c)).rolling_quantile(0.9, window_size=7 * 1440, min_samples=1440)  # noqa: E731
    x = x.with_columns(ub=p90("barrido_b").shift(1), us=p90("barrido_s").shift(1))
    return x.with_columns(liq_s=(pl.col("barrido_b") >= pl.col("ub")) & (pl.col("barrido_b") > 0) & (pl.col("d_oi") < 0),
                          liq_l=(pl.col("barrido_s") >= pl.col("us")) & (pl.col("barrido_s") > 0) & (pl.col("d_oi") < 0))


def reales(desde: str, hasta: str) -> pl.DataFrame:
    """Liquidaciones reales COIN-M por minuto, en USD (contrato BTCUSD_PERP = 100 USD). BUY = shorts liquidados."""
    ms = [m for m in meses(desde, hasta) if (PROC / "liq_coinm" / f"{m}.parquet").exists()]
    d = pl.concat([pl.read_parquet(PROC / "liq_coinm" / f"{m}.parquet") for m in ms]).unique()
    return d.group_by(open_time=pl.col("time") // M * M).agg(
        real_s=(pl.col("original_quantity") * 100).filter(pl.col("side") == "BUY").sum(),
        real_l=(pl.col("original_quantity") * 100).filter(pl.col("side") == "SELL").sum())


def main() -> None:
    x = por_minuto("2023-07", "2024-09").join(reales("2023-07", "2024-09"), on="open_time", how="left").with_columns(pl.col("real_s", "real_l").fill_null(0.0))
    l = ["# Proxy de liquidaciones vs liquidaciones reales COIN-M (2023-07..2024-09)", "",
         "Proxy: orden a mercado que barre ≥ 3 precios, ≥ p90 móvil de 7 días, con el OI de 5m bajando. Real: liquidaciones "
         "COIN-M BTCUSD_PERP del mismo lado en el mismo minuto (muestra: Binance manda ≤ 1 por segundo).", "",
         "| Lado | Minutos con proxy | Con liq. real (proxy sí) | Con liq. real (proxy no) | Lift | Liq. real ≥ 50 k USD (sí / no) |",
         "|---|---|---|---|---|---|"]
    for nom, p, r in (("shorts liquidados (compras forzadas)", "liq_s", "real_s"), ("longs liquidados (ventas forzadas)", "liq_l", "real_l")):
        si, no = x.filter(pl.col(p)), x.filter(~pl.col(p))
        a, b = (si[r] > 0).mean(), (no[r] > 0).mean()
        a5, b5 = (si[r] >= 50_000).mean(), (no[r] >= 50_000).mean()
        l.append(f"| {nom} | {si.height} ({si.height / x.height:.1%}) | {a:.0%} | {b:.0%} | {a / b:.1f}× | {a5:.0%} / {b5:.0%} ({a5 / b5:.1f}×) |")
    txt = "\n".join(l)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "liq_proxy.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
