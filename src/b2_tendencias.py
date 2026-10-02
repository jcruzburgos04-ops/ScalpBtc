"""B2 · indicadores de tendencia en varios marcos (pedido de Juan 2026-10-02: 15m, 30m, 45m, 1h; para él la tendencia
es el rolling VWAP de 24 h).

Indicadores (todos "a favor del lado": long = alcista), con la vela del marco mayor en formación ("vivo"):
  ema{n}_{tf}    precio del lado a favor de la EMA n (50 / 200) del marco tf (15/30/45/60/240 min)
  pend{n}_{tf}   la EMA n del marco tf sube (long) respecto de una vela de ese marco antes
  cruce_{tf}     EMA 21 > EMA 50 del marco tf (long)
  rvwap_lado     precio sobre el rolling VWAP 24 h (long)
  rvwap_pend{m}  el rolling VWAP 24 h sube en los últimos m min (60 / 240) (long)
1) Descriptivo, septiembre 2026: sus ganadas / perdidas / señales B2 que no tomó en sus horas.
2) Test 2023–2025 de cada indicador como filtro de B2 (36 salidas con R ≥ 2 de b2_tp.py, sin comisiones): se reporta
   el R medio promediado sobre las 36 y cuántas son positivas, igual que el filtro de 4h. Muchas pruebas: se marcan
   las que pasan en calibración (jul–sep 2026) Y en test.
Salida: reports/b2/tendencias.md
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import polars as pl

import b2_tendencia as bten
import b2_tp
from indicadores import ema

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
TFS = (15, 30, 45, 60, 240)


def ema_tf(t: np.ndarray, c: np.ndarray, tf: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    """EMA n del marco tf en vivo y su valor una vela del marco antes (para la pendiente)."""
    b = t // (tf * 60_000)
    fin = np.r_[b[1:] != b[:-1], True]
    e = ema(c[fin], n)
    idx = np.cumsum(np.r_[0, fin[:-1]])
    a = 2.0 / (n + 1)
    prev = np.r_[np.nan, e][idx]
    vivo = np.where(np.isnan(prev), np.nan, prev + a * (c - prev))
    return vivo, prev


def agregar(m: pl.DataFrame) -> pl.DataFrame:
    t, c = m["open_time"].to_numpy(), m["close"].to_numpy()
    cols = {}
    for tf in TFS:
        for n in (21, 50, 200):
            v, p = ema_tf(t, c, tf, n)
            cols[f"e{n}_{tf}"], cols[f"e{n}p_{tf}"] = v, p
    m = m.with_columns(**{k: pl.Series(v) for k, v in cols.items()})
    return m.with_columns(rv60=pl.col("rVWAP").shift(60), rv240=pl.col("rVWAP").shift(240))


def indicadores(x: pl.DataFrame) -> dict[str, pl.Expr]:
    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    out = {}
    for tf in TFS:
        for n in (50, 200):
            out[f"precio a favor de la EMA {n} de {tf}m"] = (sg * (pl.col("close") - pl.col(f"e{n}_{tf}"))) > 0
            out[f"EMA {n} de {tf}m apuntando a favor"] = (sg * (pl.col(f"e{n}_{tf}") - pl.col(f"e{n}p_{tf}"))) > 0
        out[f"EMA 21 > EMA 50 de {tf}m (a favor)"] = (sg * (pl.col(f"e21_{tf}") - pl.col(f"e50_{tf}"))) > 0
    out["precio a favor del rolling VWAP 24 h"] = (sg * (pl.col("close") - pl.col("rVWAP"))) > 0
    out["rolling VWAP 24 h subiendo 60 min (a favor)"] = (sg * (pl.col("rVWAP") - pl.col("rv60"))) > 0
    out["rolling VWAP 24 h subiendo 240 min (a favor)"] = (sg * (pl.col("rVWAP") - pl.col("rv240"))) > 0
    return out


def descriptivo(cal: pl.DataFrame) -> list[tuple[str, dict]]:
    gan = pl.read_parquet(RAIZ / "reports/trader_sep/entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    per = pl.read_parquet(RAIZ / "reports/trader_sep/perdidas.parquet")
    s = pl.read_parquet(OUT / "senales_sep_V10_hondo_ag.parquet")
    ent = gan.select("t_entrada", "lado").vstack(per.select("t_entrada", "lado"))
    dias = ent.group_by(pl.col("t_entrada") // 86_400_000).agg(a=pl.col("t_entrada").min() - 3_600_000, b=pl.col("t_entrada").max() + 3_600_000)
    te = ent["t_entrada"].to_numpy()
    no_tom = [(a, l) for a, l in s.select("t_senal", "lado").iter_rows()
              if any(x <= a <= y for _, x, y in dias.iter_rows()) and np.min(np.abs(te - a)) > 20 * 60_000]
    ev = pl.concat([gan.select(pl.col("t_entrada").alias("t"), "lado").with_columns(g=pl.lit("ganadas")),
                    per.select(pl.col("t_entrada").alias("t"), "lado").with_columns(g=pl.lit("perdidas")),
                    pl.DataFrame(no_tom, schema={"t": pl.Int64, "lado": pl.Utf8}, orient="row").with_columns(g=pl.lit("no"))])
    x = ev.with_columns(k=pl.col("t") - 60_000).join(cal, left_on="k", right_on="open_time", how="left")
    res = []
    for nom, e in indicadores(x).items():
        v = {g: float(x.filter(pl.col("g") == g).select(e.cast(pl.Float64).mean()).item()) for g in ("ganadas", "perdidas", "no")}
        res.append((nom, v))
    return sorted(res, key=lambda r: -(r[1]["ganadas"] - r[1]["no"]))


def filtrar(m: pl.DataFrame, s: pl.DataFrame, expr_nom: str) -> pl.DataFrame:
    x = s.join(m, left_on="t_senal", right_on="open_time", how="left")
    e = indicadores(x)[expr_nom]
    return x.filter(e.fill_null(False)).select(s.columns)


def evaluar(datos, filtro: str | None):
    tot = []
    for b, tp, be in itertools.product((0.25, 0.5, 1.0), ("2R", "2.5R", "3R", "vwap", "banda", "nivel"), (None, 1.0)):
        r = []
        for m, s in datos:
            ss = filtrar(m, s, filtro) if filtro else s
            r.append(b2_tp.simular(m, ss, b, tp, be))
        tot.append(np.concatenate(r))
    medias = [x.mean() for x in tot if x.size]
    return float(np.mean(medias)), sum(v > 0 for v in medias), int(np.mean([x.size for x in tot]))


def main() -> None:
    def prep(nombre, desde, hasta, anio):
        m = bten.minutos(desde, hasta, anio, nombre).sort("open_time")
        m = agregar(m).with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
        return m, b2_tp.bt.senales(m, "hondo_ag")
    cal = prep("cal", "2026-01", "2026-09", None)
    tests = [prep(str(a), f"{a - 1}-01", f"{a}-12", a) for a in (2023, 2024, 2025)]
    print("datos listos", flush=True)
    desc = descriptivo(cal[0])
    l = ["## 1. Septiembre 2026: sus entradas vs señales B2 que no tomó", "",
         "| Al entrar… | Ganadas | Perdidas | B2 no tomadas | Ganadas − no tomadas |", "|---|---|---|---|---|"]
    for nom, v in desc:
        l.append(f"| {nom} | {v['ganadas']:.0%} | {v['perdidas']:.0%} | {v['no']:.0%} | {100 * (v['ganadas'] - v['no']):+.0f} pts |")
    l += ["", "## 2. Como filtro de B2 (R ≥ 2, sin comisiones; promedio sobre las 36 salidas)", "",
          "| Filtro | Calib. jul–sep 2026: R medio · salidas positivas | Test 2023–2025: R medio · salidas positivas · trades |",
          "|---|---|---|"]
    filas = [("(sin filtro)", None)] + [(n, n) for n, _ in desc]
    for nom, f in filas:
        rc, pc, _ = evaluar([cal], f)
        rt, pt, nt = evaluar(tests, f)
        l.append(f"| {nom} | {rc:+.3f} · {pc}/36 | {rt:+.3f} · {pt}/36 · {nt} |")
        print(nom, rc, rt, flush=True)
    txt = "\n".join(l)
    (OUT / "tendencias.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
