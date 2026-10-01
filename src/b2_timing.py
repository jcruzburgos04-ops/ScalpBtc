"""B2 · calibración del MOMENTO de entrada (revisión de Juan de los 14 casos, 2026-10-01: "se toma más abajo",
"aparece una B2 siempre antes de la entrada óptima", "muchas B2 seguidas → podría sacarme el SL").

El setup (V10: más allá de ±1σ en contra + volumen 15 min ≥ 1,5× + absorción) queda igual; cambia el disparo:
  base     primera vela con el setup (como hasta ahora)
  agota    setup en alguna de las últimas 10 velas Y la vela no hace un extremo nuevo de 5 velas, cierra a favor y su
           delta es a favor (la agresión en contra se agotó)
  agota2   ídem pero además la vela previa sí hizo el extremo (gira justo después del extremo)
  hondo    setup con el precio más allá de ±1,5σ
  hondo_ag hondo + agota
Medidas contra sus entradas de septiembre: recall/precisión (como b2.py), diferencia de precio con su entrada en ATR
(+ = B2 entra peor que él: más arriba en un long) y señales del mismo lado en los 30 min previos a cada entrada suya.
Salida: reports/b2/calibracion_momento.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

import b2

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
DISPAROS = ["base", "agota", "agota2", "hondo", "hondo_ag"]


def senales(m: pl.DataFrame, disparo: str) -> pl.DataFrame:
    t = m["open_time"].to_numpy()
    o, h, l, c = (m[x].to_numpy() for x in ("open", "high", "low", "close"))
    d1 = m["delta1"].to_numpy()
    z = ((m["close"] - m["vwap_d"]) / (m["vwap_d_p1"] - m["vwap_d"])).to_numpy()
    min_dia = (t // 60_000) % 1440
    out = []
    for lado, sg in (("long", 1.0), ("short", -1.0)):
        cnd = b2.condiciones(m, sg)
        setup = np.ones(t.size, bool)
        for k in b2.VARIANTES["V10"]:
            setup &= cnd[k].fill_null(False).to_numpy()
        if disparo.startswith("hondo"):
            setup &= (sg * z) <= -1.5
        armado = np.convolve(setup.astype(int), np.ones(10, int))[: t.size] > 0
        ext = (l if sg > 0 else -h)
        prev5 = np.r_[np.full(5, np.inf), np.array([ext[i - 5:i].min() for i in range(5, t.size)])]
        sin_extremo = ext > prev5                                   # no hizo un extremo nuevo de 5 velas
        hizo_extremo = ext <= prev5
        a_favor = (sg * (c - o) > 0) & (sg * np.nan_to_num(d1) > 0)
        if disparo in ("base", "hondo"):
            ok = setup
        elif disparo in ("agota", "hondo_ag"):
            ok = armado & sin_extremo & a_favor
        else:  # agota2
            ok = armado & sin_extremo & a_favor & np.r_[False, hizo_extremo[:-1]]
        ok &= min_dia >= b2.MIN_SESION
        ult = -10**18
        for i in np.flatnonzero(ok):
            if t[i] - ult >= b2.ESPERA_MIN * 60_000 and (disparo not in ("base", "hondo") or not ok[i - 1]):
                out.append((int(t[i]), lado, float(c[i])))
                ult = t[i]
    return pl.DataFrame(out, schema={"t_senal": pl.Int64, "lado": pl.Utf8, "precio": pl.Float64}, orient="row").sort("t_senal")


def medir(s: pl.DataFrame, tr: pl.DataFrame, m: pl.DataFrame) -> dict:
    c = b2.coincidencia(s.select("t_senal", "lado"), tr)
    atr = dict(zip(m["open_time"].to_list(), m["atr14"].to_list()))
    gaps, previas = [], []
    for te, lado, p in tr.select("t_entrada", "lado", "entrada").iter_rows():
        sg = 1 if lado == "long" else -1
        x = s.filter((pl.col("lado") == lado) & (pl.col("t_senal") >= te - 15 * 60_000) & (pl.col("t_senal") <= te + 5 * 60_000))
        if x.height:
            j = int(np.argmin(np.abs(x["t_senal"].to_numpy() - te)))
            gaps.append(sg * (x["precio"][j] - (p - 20)) / atr.get(te - 60_000, np.nan))
        previas.append(s.filter((pl.col("lado") == lado) & (pl.col("t_senal") < te) & (pl.col("t_senal") >= te - 30 * 60_000)).height)
    c["gap_atr"] = float(np.nanmedian(gaps)) if gaps else float("nan")
    c["previas"] = float(np.mean(previas))
    return c


def main() -> None:
    m = pl.read_parquet(OUT / "minutos_sep.parquet").sort("open_time")
    m = m.with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    tr = pl.read_parquet(RAIZ / "reports" / "trader_sep" / "entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    l = ["| Disparo | Señales/día | Sus entradas detectadas | Precisión en sus horas | Precio de B2 vs el suyo (mediana, ATR; + = peor) | Señales B2 en los 30 min previos a su entrada |",
         "|---|---|---|---|---|---|"]
    for d in DISPAROS:
        s = senales(m, d)
        s.write_parquet(OUT / f"senales_sep_V10_{d}.parquet")
        c = medir(s, tr, m)
        l.append(f"| {d} | {s.height / 30:.1f} | {c['aciertos']}/{c['n_trader']} = {c['recall']:.0%} | {c['precision']:.0%} de {c['senales_en_sus_horas']} | "
                 f"{c['gap_atr']:+.2f} | {c['previas']:.2f} |")
    txt = "\n".join(l)
    (OUT / "calibracion_momento.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
