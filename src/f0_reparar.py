"""F0 · Reparaciones confirmadas por Juan (2026-09-30).

1. Velas 1m oficiales rotas (count = 0, velas planas con volumen 0 mientras hubo trades): se reemplazan por
   la vela reconstruida desde las barras de 1s de aggTrades.
   → data/proc/velas_1m_reparadas.parquet  (open_time, open, high, low, close, volume, taker_buy_volume, count)
2. Minutos sin mark price: se reconstruyen como  mark ≈ last + b(t),  con b = mark − last (close a close).
   b(t) se interpola linealmente entre la mediana de b en los 60 min previos al hueco y la de los 60 min
   posteriores. O/H/L/C del mark = O/H/L/C del last + b(t).
   Ojo: las mechas del last son más largas que las del mark, así que el mark reconstruido toca niveles que el
   real quizás no tocó → el SL se dispara MÁS que con el mark real (sesgo conservador). Se mide abajo.
   → data/proc/mark_1m_reconstruido.parquet  (open_time, open, high, low, close)
3. Validación del método del mark: se tapan días completos donde SÍ hay mark real y se compara.
   → reports/f0/reparaciones.md

Uso: python src/f0_reparar.py
"""
from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

import polars as pl

from datos import PROC, leer, leer_1s

RAIZ = Path(__file__).resolve().parent.parent
VENTANA_BASE = 60  # minutos a cada lado del hueco para estimar la base mark − last


def mes_de(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m")


def velas_desde_1s(meses: list[str], minutos: set[int]) -> pl.DataFrame:
    out = []
    for mes in sorted(set(meses)):
        b = leer_1s(mes).with_columns(open_time=pl.col("ts") // 60_000 * 60_000).filter(pl.col("open_time").is_in(list(minutos)))
        out.append(b.group_by("open_time", maintain_order=True).agg(
            open=pl.col("o").first(), high=pl.col("h").max(), low=pl.col("l").min(), close=pl.col("c").last(),
            volume=pl.col("v").sum(), taker_buy_volume=pl.col("vb").sum(), count=pl.col("n_trades").sum().cast(pl.Int64)))
    return pl.concat(out).sort("open_time")


def reparar_velas(k: pl.DataFrame) -> pl.DataFrame:
    rotas = k.filter(pl.col("count") == 0)["open_time"]
    rep = velas_desde_1s([mes_de(t) for t in rotas], set(rotas.to_list()))
    # redondeo a la grilla de 0,001 BTC para que no queden restos de punto flotante al sumar
    rep = rep.with_columns(pl.col("volume", "taker_buy_volume").round(3))
    rep.write_parquet(PROC / "velas_1m_reparadas.parquet", compression="zstd")
    return rep


def reconstruir_mark(last: pl.DataFrame, mark: pl.DataFrame, huecos: list[int]) -> pl.DataFrame:
    """last: velas 1m de last price (open_time, open, high, low, close); mark: mark real disponible.
    huecos: open_time de los minutos a reconstruir."""
    base = last.select("open_time", lc="close").join(mark.select("open_time", mc="close"), on="open_time") \
        .with_columns(b=pl.col("mc") - pl.col("lc")).sort("open_time")
    hs = sorted(huecos)
    # agrupar minutos contiguos en tramos
    tramos, ini, prev = [], hs[0], hs[0]
    for t in hs[1:]:
        if t - prev != 60_000:
            tramos.append((ini, prev))
            ini = t
        prev = t
    tramos.append((ini, prev))
    out = []
    for a, z in tramos:
        antes = base.filter(pl.col("open_time").is_between(a - VENTANA_BASE * 60_000, a - 1))["b"]
        despues = base.filter(pl.col("open_time").is_between(z + 1, z + VENTANA_BASE * 60_000))["b"]
        b0 = antes.median() if antes.len() else despues.median()
        b1 = despues.median() if despues.len() else b0
        tr = last.filter(pl.col("open_time").is_between(a, z)).with_columns(
            f=((pl.col("open_time") - a) / max(z - a, 1)))
        tr = tr.with_columns(b=b0 + (b1 - b0) * pl.col("f"))
        out.append(tr.select("open_time", *[(pl.col(c) + pl.col("b")).alias(c) for c in ("open", "high", "low", "close")]))
    return pl.concat(out).sort("open_time")


def validar_mark(last: pl.DataFrame, mark: pl.DataFrame, n_dias: int = 40, semilla: int = 7) -> dict:
    """Tapa n_dias completos (con mark real) y compara la reconstrucción contra el mark real."""
    dias = mark.select(d=pl.col("open_time") // 86_400_000).unique()["d"].to_list()
    random.Random(semilla).shuffle(dias)
    res = []
    for d in dias[:n_dias]:
        mins = list(range(d * 86_400_000, (d + 1) * 86_400_000, 60_000))
        rec = reconstruir_mark(last, mark.filter(~pl.col("open_time").is_in(mins)), mins)
        j = rec.join(mark, on="open_time", suffix="_real")
        res.append(j.with_columns(dia=pl.lit(d)))
    j = pl.concat(res)
    rango = (j["high_real"] - j["low_real"])
    return {
        "dias": n_dias, "minutos": j.height,
        "close_err_abs_mediana_usd": float((j["close"] - j["close_real"]).abs().median()),
        "close_err_abs_p95_usd": float((j["close"] - j["close_real"]).abs().quantile(0.95)),
        "close_err_rel_p95_pct": float(((j["close"] - j["close_real"]).abs() / j["close_real"]).quantile(0.95) * 100),
        "high_rec_mayor_que_real_pct": float((j["high"] > j["high_real"]).mean() * 100),
        "low_rec_menor_que_real_pct": float((j["low"] < j["low_real"]).mean() * 100),
        "exceso_high_mediana_usd": float((j["high"] - j["high_real"]).median()),
        "exceso_low_mediana_usd": float((j["low_real"] - j["low"]).median()),
        "rango_real_mediana_usd": float(rango.median()),
    }


def main() -> None:
    k = leer("klines_1m")
    rep = reparar_velas(k)
    last = k.select("open_time", "open", "high", "low", "close").update(
        rep.select("open_time", "open", "high", "low", "close"), on="open_time")
    mark = leer("mark_1m")
    huecos = sorted(set(last["open_time"].to_list()) - set(mark["open_time"].to_list()))
    rec = reconstruir_mark(last, mark, huecos)
    rec.write_parquet(PROC / "mark_1m_reconstruido.parquet", compression="zstd")
    v = validar_mark(last.filter(pl.col("open_time") >= 1_735_689_600_000),  # validación en 2025–2026
                     mark.filter(pl.col("open_time") >= 1_735_689_600_000))

    f = lambda ms: dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    l = ["# F0 · Reparaciones (confirmadas por Juan el 2026-09-30)", "",
         "## 1. Velas 1m oficiales rotas → reconstruidas desde aggTrades", "",
         f"{rep.height} minutos reemplazados (`data/proc/velas_1m_reparadas.parquet`). `datos.leer_velas_1m()` ya los aplica.", "",
         "| open_time (UTC) | O | H | L | C | V (BTC) | trades |", "|---|---|---|---|---|---|---|"]
    for r in rep.head(12).iter_rows(named=True):
        l.append(f"| {f(r['open_time'])} | {r['open']} | {r['high']} | {r['low']} | {r['close']} | {r['volume']:.3f} | {r['count']} |")
    l += [f"| … ({rep.height - 12} más) | | | | | | |", "",
          "## 2. Mark price reconstruido", "",
          f"{rec.height} minutos reconstruidos (`data/proc/mark_1m_reconstruido.parquet`). `datos.leer_mark_1m()` ya los aplica.", "",
          "Método: mark ≈ last + b(t), b = mark − last interpolada entre la mediana de los 60 min previos y la de los 60 posteriores al hueco.", "",
          "| Tramo (UTC) | Minutos |", "|---|---|"]
    tr = rec.with_columns(g=(pl.col("open_time").diff().fill_null(0) != 60_000).cum_sum()) \
        .group_by("g", maintain_order=True).agg(a=pl.col("open_time").first(), n=pl.len())
    for r in tr.iter_rows(named=True):
        l.append(f"| {f(r['a'])} | {r['n']} |")
    l += ["", f"### Validación: {v['dias']} días de 2025–2026 con mark real, tapados y reconstruidos ({v['minutos']} minutos)", "",
          "| Métrica | Valor |", "|---|---|",
          f"| Error absoluto del close, mediana | {v['close_err_abs_mediana_usd']:.2f} USD |",
          f"| Error absoluto del close, p95 | {v['close_err_abs_p95_usd']:.2f} USD ({v['close_err_rel_p95_pct']:.4f} %) |",
          f"| Minutos con high reconstruido > high real | {v['high_rec_mayor_que_real_pct']:.1f} % |",
          f"| Minutos con low reconstruido < low real | {v['low_rec_menor_que_real_pct']:.1f} % |",
          f"| Exceso del high, mediana | {v['exceso_high_mediana_usd']:.2f} USD |",
          f"| Exceso del low, mediana | {v['exceso_low_mediana_usd']:.2f} USD |",
          f"| Rango H−L del mark real, mediana | {v['rango_real_mediana_usd']:.2f} USD |", "",
          "Lectura: si high/low reconstruidos superan al real en la mayoría de los minutos, el SL por mark se dispara",
          "más seguido que en la realidad en esos días (sesgo conservador). Los trades que caigan en minutos",
          "reconstruidos se marcan en el motor (F3) para poder excluirlos en la sensibilidad."]
    (RAIZ / "reports" / "f0" / "reparaciones.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
