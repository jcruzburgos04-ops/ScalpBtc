"""B2 escalonada · test fuera de muestra 2023–2025 con UNA configuración fijada antes de mirar (2026-10-01):
señal V10_hondo_ag, SL común = extremo de 10 velas − 2 ATR, hasta 3 patas con órdenes límite cada 1 ATR, TP = precio
medio + 1 ATR. Mismo simulador que la calibración (velas de 1m, SL primero si cae en la misma vela, sin breakeven).
Salida: reports/b2/test_2023_2025.md"""
from pathlib import Path
import numpy as np, polars as pl
import b2_escalonada as be, b2_timing as bt, trader_sep as ts, volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
COLS = ["open_time", "open", "high", "low", "close", "vwap_d", "vwap_d_p1", "atr14", "delta1", "vol15_rel", "absorcion5", "rVWAP", "nb15", "ns15"]


def anio(a: int) -> pl.DataFrame:
    df = volumen.agregar(ts.base(f"{a - 1}-12", f"{a}-12"), f"{a - 1}-12", f"{a}-12", con_segundos=False)
    df = df.select(COLS).with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    return df.filter(pl.from_epoch("open_time", time_unit="ms").dt.year() == a)


def main() -> None:
    filas = []
    for a in (2023, 2024, 2025):
        m = anio(a)
        s = bt.senales(m, "hondo_ag")
        x = pl.DataFrame(be.simular(m, s, 2.0, 3, "1atr", 1.0)).with_columns(anio=pl.lit(a))
        filas.append(x)
        print(a, x.height, round((x["r"] > 0).mean(), 3), round(x["r"].mean(), 4), flush=True)
    x = pl.concat(filas)
    x.write_parquet(OUT / "test_2023_2025.parquet")
    r = x["r"].to_numpy()
    rng = np.random.default_rng(0)
    bs = [r[rng.integers(0, r.size, r.size)].mean() for _ in range(2000)]
    l = ["B2 escalonada, test 2023–2025 (configuración fijada antes: SL extremo − 2 ATR, 3 patas cada 1 ATR, TP +1 ATR).", "",
         "| Año | Posiciones | Gana | R medio |", "|---|---|---|---|"]
    for a in (2023, 2024, 2025):
        y = x.filter(pl.col("anio") == a)
        l.append(f"| {a} | {y.height} | {(y['r'] > 0).mean():.0%} | {y['r'].mean():+.3f} |")
    l.append(f"| **Total** | {x.height} | {(r > 0).mean():.0%} | {r.mean():+.3f} [IC 95 % {np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}] |")
    gan, per = r[r > 0], r[r <= 0]
    l += ["", f"Ganancia media {gan.mean():+.2f} R · pérdida media {per.mean():+.2f} R · patas usadas {x['patas'].mean():.2f} · "
          f"motivos: " + ", ".join(f"{a} {b}" for a, b in x.group_by("motivo").len().sort("len", descending=True).rows())]
    txt = "\n".join(l); (OUT / "test_2023_2025.md").write_text(txt + "\n"); print(txt)


if __name__ == "__main__":
    main()
