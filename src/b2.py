"""Estrategia B2 · reversión desde el extremo, como entra el trader de referencia (septiembre 2026).

Lectura de sus 93 entradas revisadas por Juan: entra lejos del VWAP de sesión (más allá de ±1σ en contra), contra el
rolling VWAP, muchas veces tras barrer el extremo de la última hora, y ANTES de que giren el ASH y las XO.

Señal long al cierre de la vela k (short = espejo), variantes a calibrar contra sus entradas:
  sigma   z = (close − VWAP sesión) / σ ≤ −1
  rvwap   close < rolling VWAP (24 h)
  barrida el mínimo de las últimas 5 velas es el mínimo de los últimos 60 min
  V1 = sigma + rvwap + barrida · V2 = sigma + barrida · V3 = sigma + rvwap · V4 = sigma · V5 = rvwap + barrida
Se toma la primera vela en que la condición se cumple, con 15 min de espera entre señales del mismo lado; se ignoran
los primeros 30 min del día UTC (bandas degeneradas). SL = extremo de las últimas 10 velas ± 0,25 ATR; TP = VWAP de sesión.
Calibración = coincidencia con sus entradas (no el PnL). Salida: reports/b2/calibracion.md, rasgos_volumen.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import trader_sep as ts
import volumen

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
VARIANTES = {"V1": ("sigma", "rvwap", "barrida"), "V2": ("sigma", "barrida"), "V3": ("sigma", "rvwap"),
             "V4": ("sigma",), "V5": ("rvwap", "barrida"),
             # con volumen (lo que distingue sus entradas de las señales que no tomó)
             "V6": ("sigma", "vol"), "V7": ("sigma", "vol", "delta_ok"), "V8": ("sigma", "barrida", "vol", "delta_ok"),
             "V9": ("vol", "absor", "delta_ok"), "V10": ("sigma", "vol", "absor"), "V11": ("vol", "burb", "delta_ok"),
             "V12": ("sigma", "rvwap", "vol", "delta_ok")}
ESPERA_MIN, MIN_SESION = 15, 30
ANTES, DESPUES = 15, 5   # una señal "coincide" si cae entre 15 min antes y 5 min después de su entrada


def condiciones(df: pl.DataFrame, sg: float) -> pl.DataFrame:
    z = (pl.col("close") - pl.col("vwap_d")) / (pl.col("vwap_d_p1") - pl.col("vwap_d"))
    if sg > 0:
        bar = pl.col("low").rolling_min(5) <= pl.col("min60")
    else:
        bar = pl.col("high").rolling_max(5) >= pl.col("max60")
    contra = pl.col("ns15") if sg > 0 else pl.col("nb15")
    return df.select("open_time", sigma=(sg * z) <= -1, rvwap=(sg * (pl.col("close") - pl.col("rVWAP"))) < 0, barrida=bar,
                     vol=pl.col("vol15_rel") >= 1.5, absor=pl.col("absorcion5") >= 1.0, delta_ok=(sg * pl.col("delta1")) > -0.1,
                     burb=contra >= 15)


def senales(df: pl.DataFrame, variante: str) -> pl.DataFrame:
    t = df["open_time"].to_numpy()
    min_dia = (t // 60_000) % 1440
    out = []
    for lado, sg in (("long", 1.0), ("short", -1.0)):
        c = condiciones(df, sg)
        ok = np.ones(t.size, dtype=bool)
        for k in VARIANTES[variante]:
            ok &= c[k].fill_null(False).to_numpy()
        ok &= min_dia >= MIN_SESION
        ult = -10**18
        for i in np.flatnonzero(ok):
            if t[i] - ult >= ESPERA_MIN * 60_000 and not ok[i - 1]:
                out.append((int(t[i]), lado))
                ult = t[i]
            elif t[i] - ult >= ESPERA_MIN * 60_000 and ok[i - 1]:
                continue
    return pl.DataFrame(out, schema={"t_senal": pl.Int64, "lado": pl.Utf8}, orient="row").sort("t_senal")


def coincidencia(s: pl.DataFrame, tr: pl.DataFrame) -> dict:
    """recall: entradas del trader con una señal del mismo lado entre 15 min antes y 5 min después.
    precisión: señales dentro de las horas en que él operó (de su 1.ª a su última entrada de cada día, ±1 h) que tienen
    una entrada suya del mismo lado entre 5 min antes y 15 min después."""
    e = tr.select("t_entrada", "lado")
    hits = 0
    for te, lado in e.iter_rows():
        x = s.filter((pl.col("lado") == lado) & (pl.col("t_senal") >= te - ANTES * 60_000) & (pl.col("t_senal") <= te + DESPUES * 60_000))
        hits += x.height > 0
    dias = e.with_columns(d=pl.col("t_entrada") // 86_400_000).group_by("d").agg(a=pl.col("t_entrada").min() - 3_600_000,
                                                                                 b=pl.col("t_entrada").max() + 3_600_000)
    dentro, ok = 0, 0
    for ts_, lado in s.iter_rows():
        if not any(a <= ts_ <= b for _, a, b in dias.iter_rows()):
            continue
        dentro += 1
        y = e.filter((pl.col("lado") == lado) & (pl.col("t_entrada") >= ts_ - DESPUES * 60_000) & (pl.col("t_entrada") <= ts_ + ANTES * 60_000))
        ok += y.height > 0
    return {"recall": hits / e.height, "aciertos": hits, "n_trader": e.height, "senales_en_sus_horas": dentro,
            "precision": ok / dentro if dentro else float("nan"), "senales_mes": s.height}


def rasgos(df: pl.DataFrame, tiempos: pl.DataFrame) -> pl.DataFrame:
    """Rasgos de volumen en la última vela cerrada antes de cada tiempo, con signo a favor del lado."""
    x = tiempos.with_columns(k=pl.col("t") - 60_000).join(df, left_on="k", right_on="open_time", how="left")
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    return x.select(
        "lado",
        delta1=sg * pl.col("delta1"), delta10s=sg * pl.col("delta10s"),
        cvd5=sg * pl.col("cvd5"), cvd15=sg * pl.col("cvd15"),
        div_cvd=(sg * pl.col("ret15") <= -1) & (sg * pl.col("cvd15") > -0.02),
        vol15_rel=pl.col("vol15_rel"), pico10s=pl.col("pico10s"),
        absorcion5=pl.col("absorcion5"),
        burb_contra15=pl.when(sg > 0).then(pl.col("ns15")).otherwise(pl.col("nb15")),
        burb_favor15=pl.when(sg > 0).then(pl.col("nb15")).otherwise(pl.col("ns15")),
        oi15=pl.col("oi15") * 100, oi60=pl.col("oi60") * 100,
    )


ETIQUETAS = [  # (nombre, columna, función) para la tabla de frecuencias
    ("Vela de entrada con delta a favor (más agresión del lado del trade)", "delta1", lambda c: c > 0),
    ("Últimos 10 s con delta a favor (velas de segundos)", "delta10s", lambda c: c > 0),
    ("CVD 5 min a favor", "cvd5", lambda c: c > 0),
    ("CVD 15 min a favor", "cvd15", lambda c: c > 0),
    ("Divergencia: el precio vino ≥ 1 ATR en contra y el CVD 15 min no acompañó", "div_cvd", lambda c: c),
    ("Volumen 15 min ≥ 1,5× lo normal", "vol15_rel", lambda c: c >= 1.5),
    ("Pico en velas de 10 s (≥ 4× la mediana de la hora)", "pico10s", lambda c: c >= 4),
    ("Absorción: mucho volumen y poco rango en 5 velas (≥ 2)", "absorcion5", lambda c: c >= 2),
    ("≥ 15 burbujas grandes en contra en 15 min (ventas para un long)", "burb_contra15", lambda c: c >= 15),
    ("≥ 15 burbujas grandes a favor en 15 min", "burb_favor15", lambda c: c >= 15),
    ("Open interest bajando en 15 min", "oi15", lambda c: c < 0),
    ("Open interest bajando ≥ 0,3 % en 60 min (cierres / liquidaciones)", "oi60", lambda c: c <= -0.3),
]
MEDIANAS = ["delta1", "delta10s", "cvd15", "vol15_rel", "pico10s", "absorcion5", "burb_contra15", "oi60"]


def tabla_rasgos(grupos: dict[str, pl.DataFrame]) -> str:
    noms = list(grupos)
    l = ["| Al entrar… | " + " | ".join(f"{n} (n={g.height})" for n, g in grupos.items()) + " |",
         "|---|" + "---|" * len(noms)]
    for et, col, f in ETIQUETAS:
        vals = [float(g.select(f(pl.col(col)).cast(pl.Float64).mean()).item()) for g in grupos.values()]
        l.append(f"| {et} | " + " | ".join(f"{v:.0%}" for v in vals) + " |")
    l += ["", "Medianas:", "", "| Rasgo | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for col in MEDIANAS:
        vals = [g[col].drop_nulls().median() for g in grupos.values()]
        l.append(f"| {col} | " + " | ".join(f"{v:.2f}" if v is not None else "–" for v in vals) + " |")
    return "\n".join(l)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = volumen.agregar(ts.base("2026-07", "2026-09"), "2026-07", "2026-09")
    sep = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m") == "2026-09")
    sep.select("open_time", "open", "high", "low", "close", "vwap_d", "vwap_d_p1", "vwap_d_m1", "vwap_d_p2", "vwap_d_m2",
               "vwap_w", "rVWAP", "dVAH", "dVAL", "ema11", "ema25", "atr14", "delta1", "delta10s", "vol15_rel", "absorcion5",
               "nb15", "ns15", "cvd15", "pico10s").write_parquet(OUT / "minutos_sep.parquet")
    tr = pl.read_parquet(RAIZ / "reports" / "trader_sep" / "entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    # 1) calibración de la definición contra sus entradas
    l = ["| Variante | Condiciones | Señales en sept. | Sus entradas con señal cerca (recall) | Señales en sus horas que coinciden con una entrada suya (precisión) |",
         "|---|---|---|---|---|"]
    todas = {}
    for v in VARIANTES:
        s = senales(sep, v)
        todas[v] = s
        c = coincidencia(s, tr)
        l.append(f"| {v} | {' + '.join(VARIANTES[v])} | {c['senales_mes']} | {c['aciertos']}/{c['n_trader']} = {c['recall']:.0%} | "
                 f"{c['precision']:.0%} de {c['senales_en_sus_horas']} |")
    (OUT / "calibracion.md").write_text("\n".join(l) + "\n")
    print("\n".join(l))
    for v, s in todas.items():
        s.write_parquet(OUT / f"senales_sep_{v}.parquet")
    # 2) volumen: sus entradas vs las señales B2 que él NO tomó vs un minuto cualquiera
    ent = tr.select(pl.col("t_entrada").alias("t"), "lado")
    s1 = todas["V2"].rename({"t_senal": "t"})
    no_tomadas = s1.join(ent.with_columns(pl.lit(1).alias("x")), on="lado", how="left").with_columns(
        cerca=(pl.col("t_right") - pl.col("t")).abs() <= 20 * 60_000).group_by("t", "lado").agg(pl.col("cerca").any()).filter(~pl.col("cerca"))
    rng = np.random.default_rng(0)
    base_t = rng.choice(sep["open_time"].to_numpy()[60:], 3000, replace=False)
    base = pl.DataFrame({"t": np.r_[base_t, base_t] + 60_000, "lado": ["long"] * 3000 + ["short"] * 3000})
    grupos = {"Sus entradas": rasgos(df, ent), "Señales B2 (V2) que no tomó": rasgos(df, no_tomadas.select("t", "lado")),
              "Minuto cualquiera": rasgos(df, base)}
    txt = tabla_rasgos(grupos)
    (OUT / "rasgos_volumen.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
