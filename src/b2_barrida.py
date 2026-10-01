"""B2 · ¿qué pasa con el extremo de la PRIMERA señal? (ronda 2 de Juan: "después del primer B2 hay una mecha que barre
el low → SL").

Período: jul–sep 2026 (calibración de B2; 2023–2025 sigue intacto para el test). Disparo: V10_hondo_ag.
Jugada = señales del mismo lado separadas por < 60 min. Para cada señal (long; short espejo):
  extremo  mínimo de las últimas 10 velas al disparar (base del SL); SL = extremo − 0,25 ATR; TP = VWAP de sesión
  barrido  el precio pierde el extremo antes de tocar el TP (horizonte 24 h, velas de 1m; si SL y TP caen en la misma
           vela se cuenta SL)
Variantes de entrada:
  todas         todas las señales
  primera       solo la primera de cada jugada
  segunda+      solo las siguientes
  tras_barrida  se ignora la primera; se entra en la primera señal posterior que llega DESPUÉS de que el precio barrió
                el extremo de la primera (la trampa ya saltó), con su propio extremo
Resultado en R por velas de 1m, sin breakeven ni comisiones (diagnóstico; el test final va con el motor de 1 s).
Salida: reports/b2/barrida_primera.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import b2_timing as bt
import trader_sep as ts
import volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
CACHE = OUT / "minutos_jul_sep.parquet"
JUGADA_MIN = 60


def minutos() -> pl.DataFrame:
    if CACHE.exists():
        return pl.read_parquet(CACHE)
    df = volumen.agregar(ts.base("2026-06", "2026-09"), "2026-06", "2026-09")
    df = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m") >= "2026-07").select(
        "open_time", "open", "high", "low", "close", "vwap_d", "vwap_d_p1", "vwap_d_m1", "vwap_d_p2", "vwap_d_m2",
        "vwap_w", "rVWAP", "dVAH", "dVAL", "ema11", "ema25", "atr14", "delta1", "delta10s", "vol15_rel", "absorcion5",
        "nb15", "ns15", "cvd15", "pico10s")
    df.write_parquet(CACHE)
    return df


def resolver(m: pl.DataFrame, s: pl.DataFrame) -> pl.DataFrame:
    t = m["open_time"].to_numpy()
    h, l, c, atr, vw = (m[x].to_numpy() for x in ("high", "low", "close", "atr14", "vwap_d"))
    filas = []
    for ts_, lado in s.select("t_senal", "lado").iter_rows():
        i = int(np.searchsorted(t, ts_))
        sg = 1 if lado == "long" else -1
        ext = l[i - 9:i + 1].min() if sg > 0 else h[i - 9:i + 1].max()
        sl = ext - sg * 0.25 * atr[i]
        tp, fill = vw[i], c[i]
        riesgo = sg * (fill - sl)
        fin = min(i + 1440, t.size)
        hh, ll = h[i + 1:fin], l[i + 1:fin]
        toca_tp = (hh >= tp) if sg > 0 else (ll <= tp)
        toca_sl = (ll <= sl) if sg > 0 else (hh >= sl)
        pierde_ext = (ll < ext) if sg > 0 else (hh > ext)
        k_tp = int(np.argmax(toca_tp)) if toca_tp.any() else 10**9
        k_sl = int(np.argmax(toca_sl)) if toca_sl.any() else 10**9
        k_ex = int(np.argmax(pierde_ext)) if pierde_ext.any() else 10**9
        if sg * (tp - fill) <= 0 or riesgo <= 0:
            r = np.nan                                  # el TP ya quedó atrás: no hay trade
        elif k_sl <= k_tp and k_sl < 10**9:
            r = -1.0
        elif k_tp < 10**9:
            r = sg * (tp - fill) / riesgo
        else:
            r = sg * (c[fin - 1] - fill) / riesgo
        filas.append({"t_senal": ts_, "lado": lado, "ext": ext, "r": r, "r_tp": sg * (tp - fill) / riesgo if riesgo > 0 else np.nan,
                      "barre_ext": k_ex < k_tp, "t_barre": int(t[i + 1 + k_ex]) if k_ex < 10**9 else None,
                      "min_hasta_barrida": k_ex + 1 if k_ex < 10**9 else None, "sl": k_sl <= k_tp and k_sl < 10**9})
    return pl.DataFrame(filas)


def jugadas(r: pl.DataFrame) -> pl.DataFrame:
    r = r.sort("lado", "t_senal")
    r = r.with_columns(nueva=(pl.col("t_senal").diff().over("lado").fill_null(10**12) >= JUGADA_MIN * 60_000))
    r = r.with_columns(jugada=pl.col("nueva").cum_sum().over("lado"))
    return r.with_columns(orden=pl.int_range(1, pl.len() + 1).over("lado", "jugada"))


def tras_barrida(r: pl.DataFrame) -> pl.DataFrame:
    """En cada jugada: la primera señal posterior a que el precio barriera el extremo de la primera."""
    out = []
    for (_, _), g in r.group_by("lado", "jugada"):
        g = g.sort("t_senal")
        tb = g["t_barre"][0]
        if tb is None:
            continue
        x = g.filter((pl.col("orden") > 1) & (pl.col("t_senal") > tb))
        if x.height:
            out.append(x.head(1))
    return pl.concat(out) if out else r.head(0)


def linea(nom: str, x: pl.DataFrame) -> str:
    x = x.filter(pl.col("r").is_not_nan())
    if x.height == 0:
        return f"| {nom} | 0 | – | – | – | – |"
    return (f"| {nom} | {x.height} | {x['barre_ext'].mean():.0%} | {x['sl'].mean():.0%} | {(x['r'] > 0).mean():.0%} | "
            f"{x['r'].mean():+.3f} |")


def main() -> None:
    m = minutos().sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    s = bt.senales(m, "hondo_ag")
    r = jugadas(resolver(m, s))
    r.write_parquet(OUT / "barrida_senales.parquet")
    njug = r.select(pl.struct("lado", "jugada").n_unique()).item()
    l = [f"Señales B2 (±1,5σ + agotamiento) jul–sep 2026: {r.height} en {njug} jugadas "
         f"({(r.group_by('lado', 'jugada').len()['len'] > 1).mean():.0%} de las jugadas tienen más de una señal).", "",
         "| Entrada | Trades | Le barren el extremo antes del TP | Termina en SL | Gana | R medio (TP VWAP, sin BE) |",
         "|---|---|---|---|---|---|",
         linea("Todas las señales", r), linea("Solo la 1.ª señal de cada jugada", r.filter(pl.col("orden") == 1)),
         linea("Solo 2.ª señal en adelante", r.filter(pl.col("orden") > 1)),
         linea("1.ª señal de jugadas con una sola señal", r.filter((pl.col("orden") == 1) & (pl.col("jugada").count().over("lado", "jugada") == 1))),
         linea("1.ª señal de jugadas con varias señales", r.filter((pl.col("orden") == 1) & (pl.col("jugada").count().over("lado", "jugada") > 1))),
         linea("Ignorar la 1.ª y entrar tras la barrida de su extremo", tras_barrida(r))]
    p1 = r.filter((pl.col("orden") == 1) & pl.col("barre_ext"))
    l += ["", f"Cuando barren el extremo de la 1.ª señal: mediana {p1['min_hasta_barrida'].median():.0f} min después "
          f"(p25 {p1['min_hasta_barrida'].quantile(0.25):.0f}, p75 {p1['min_hasta_barrida'].quantile(0.75):.0f})."]
    txt = "\n".join(l)
    (OUT / "barrida_primera.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
