"""Trades perdidos del trader (calaveras, lado confirmado por Juan 2026-10-02) vs sus entradas ganadoras.
Cada calavera se ubica como las tarjetas: minuto de Binance más cercano a la hora leída (±30 min) donde el precio pasa
por el precio de la calavera (tolerancia ±0,5 ATR). La calavera marca la caja long/short de TV, así que su precio y
hora son aproximados: comparación descriptiva, n = 15. Salida: reports/trader_sep/perdidas_vs_ganadas.md"""
from pathlib import Path
import datetime as dt
import numpy as np, polars as pl
import trader_sep as ts, volumen, b2

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trader_sep"


def main():
    k = pl.read_csv(RAIZ / "marcas/trader_sep2026/calaveras.csv").filter(pl.col("lado").is_not_null() & (pl.col("lado") != ""))
    df = volumen.agregar(ts.base("2026-07", "2026-09"), "2026-07", "2026-09").sort("open_time")
    t, h, l, atr = (df[x].to_numpy() for x in ("open_time", "high", "low", "atr14"))
    filas = []
    for r in k.iter_rows(named=True):
        ap = ts.a_utc_ms(r["hora_aprox_trader"]); p = float(r["precio_aprox"])
        i0, i1 = np.searchsorted(t, ap - 30 * 60_000), np.searchsorted(t, ap + 30 * 60_000)
        tol = 0.5 * atr[i0:i1]
        ok = (l[i0:i1] - tol <= p) & (p <= h[i0:i1] + tol)
        j = np.flatnonzero(ok)
        m = int(t[i0 + j[np.argmin(np.abs(t[i0 + j] - ap))]]) if j.size else ap // 60_000 * 60_000
        filas.append({"id": r["id"], "captura": r["captura"], "plataforma": "calavera", "lado": r["lado"], "entrada": p + 20,
                      "t_entrada": m, "toca": bool(j.size)})
    perd = ts.leer_indicadores(pl.DataFrame(filas), df)
    gan = pl.read_parquet(OUT / "entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    vg = b2.rasgos(df, gan.select(pl.col("t_entrada").alias("t"), "lado"))
    vp = b2.rasgos(df, perd.select(pl.col("t_entrada").alias("t"), "lado"))
    perd.write_parquet(OUT / "perdidas.parquet")
    def fr(x, e):
        return float(x.select(e.cast(pl.Float64).mean()).item())
    sgc = lambda d: pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)  # noqa: E731
    rasgos = [
        ("Más allá de 1σ del VWAP de sesión, en contra", lambda d: d.select(((pl.col("z_vwap_d") * sgc(d)) <= -1).mean()).item()),
        ("Contra el rolling VWAP", lambda d: d.select((pl.col("sobre_rvwap") != (pl.col("lado") == "long")).mean()).item()),
        ("Contra el VWAP semanal", lambda d: d.select((pl.col("sobre_vwap_w") != (pl.col("lado") == "long")).mean()).item()),
        ("Barrida del extremo de 60 min", lambda d: d.select(pl.col("barrida60").mean()).item()),
        ("Venía ≥ 1 ATR en contra en 15 min", lambda d: d.select((pl.col("ret15_atr") <= -1).mean()).item()),
        ("ASH 1m a favor", lambda d: d.select(pl.col("ash1_a_favor").mean()).item()),
        ("XO 1m a favor", lambda d: d.select(pl.col("xo_a_favor").mean()).item()),
        ("ASH 5m a favor", lambda d: d.select(pl.col("ash5_a_favor").mean()).item()),
        ("Nivel a ≤ 0,5 ATR", lambda d: d.select((pl.col("dist1_atr").abs() <= 0.5).mean()).item()),
        ("Dentro de la ventana de Juan (hora UTC < 16)", lambda d: d.select((pl.col("hora_utc") < 16).mean()).item()),
    ]
    vol = [("Volumen 15 min ≥ 1,5×", pl.col("vol15_rel") >= 1.5), ("Absorción ≥ 1", pl.col("absorcion5") >= 1),
           ("Delta de la vela a favor", pl.col("delta1") > 0), ("CVD 15 min a favor", pl.col("cvd15") > 0),
           ("≥ 15 burbujas grandes en contra en 15 min", pl.col("burb_contra15") >= 15)]
    lin = [f"Ganadas (tarjetas): {gan.height} · perdidas (calaveras): {perd.height} ({int(perd['toca'].sum())} ubicadas por precio). "
           "Lado = el del trade; n chico: diferencias de < 25 puntos no son concluyentes.", "",
           "| Al entrar… | Ganadas | Perdidas |", "|---|---|---|"]
    for n, f in rasgos:
        lin.append(f"| {n} | {f(gan):.0%} | {f(perd):.0%} |")
    for n, e in vol:
        lin.append(f"| {n} | {fr(vg, e):.0%} | {fr(vp, e):.0%} |")
    lin += ["", "| Mediana | Ganadas | Perdidas |", "|---|---|---|"]
    for c, d1, d2 in [("z_vwap_d·lado", gan.select(pl.col("z_vwap_d") * sgc(gan)).to_series(), perd.select(pl.col("z_vwap_d") * sgc(perd)).to_series()),
                      ("ret15_atr", gan["ret15_atr"], perd["ret15_atr"]), ("ret60_atr", gan["ret60_atr"], perd["ret60_atr"]),
                      ("vol15_rel", vg["vol15_rel"], vp["vol15_rel"]), ("absorcion5", vg["absorcion5"], vp["absorcion5"]),
                      ("delta1", vg["delta1"], vp["delta1"]), ("hora_utc", gan["hora_utc"], perd["hora_utc"])]:
        lin.append(f"| {c} | {d1.median():.2f} | {d2.median():.2f} |")
    txt = "\n".join(lin); (OUT / "perdidas_vs_ganadas.md").write_text(txt + "\n"); print(txt)
    print(perd.select("id", "lado", "t_entrada", "toca", pl.col("z_vwap_d").round(2), "barrida60", pl.col("ret15_atr").round(1)))


if __name__ == "__main__":
    main()
