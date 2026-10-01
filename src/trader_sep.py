"""Trades del trader de referencia · septiembre 2026 (capturas de Juan, marcas/trader_sep2026/).

1. Ubicación: las capturas están en UTC+2 (verificado con las 11 órdenes con hora del 28-sep). Cada tarjeta da el lado
   y el precio de entrada en SU exchange, que cotiza unos 10–45 USD por encima de Binance. Dentro de la ventana de la
   captura se buscan los minutos de Binance donde ese precio entra en la vela (low − 10 ≤ P ≤ high + 45) y se toma el
   más cercano a la hora aproximada leída en el gráfico. Se cuentan los "episodios" (tramos separados donde el precio
   pasó por ahí) para medir cuán ambigua es la ubicación.
2. Lectura de indicadores: lo que el trader veía al entrar = la última vela de 1m CERRADA antes de la entrada (para
   los osciladores) y el precio de entrada en Binance (para la ubicación respecto de los niveles).
3. Comparación: cada rasgo se compara con su frecuencia en todos los minutos de septiembre (línea de base), para ver
   qué tienen de distinto sus entradas y no solo qué tienen en común.
Salidas: reports/trader_sep/entradas.parquet, entradas.csv, similitudes.md
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

import f6_variables as f6
from indicadores import ema

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trader_sep"
TZ_CAPTURAS = dt.timezone(dt.timedelta(hours=2))
PREMIO_LO, PREMIO_HI = 10.0, 45.0      # su precio vs la vela de Binance: low − 10 ≤ P ≤ high + 45
NIVELES = {  # nombre en el gráfico → columna
    "VWAP sesión": "vwap_d", "VWAP +1σ": "vwap_d_p1", "VWAP −1σ": "vwap_d_m1", "VWAP +2σ": "vwap_d_p2", "VWAP −2σ": "vwap_d_m2",
    "VWAP semanal": "vwap_w", "wVWAP +1σ": "vwap_w_p1", "wVWAP −1σ": "vwap_w_m1",
    "rolling VWAP": "rVWAP", "rVAH": "rVAH", "rVAL": "rVAL",
    "dVAH": "dVAH", "dVAL": "dVAL", "dPOC": "dPOC", "pdVAH": "pdVAH", "pdVAL": "pdVAL", "pdVWAP": "pdVWAP", "pdPOC": "pdPOC",
    "DO": "DO", "WO": "WO", "PWH": "PWH", "PWL": "PWL", "MNDAY-H": "MNDAY_H_vivo", "MNDAY-L": "MNDAY_L_vivo",
    "pwVWAP": "pwVWAP_vivo", "pwVAH": "pwVAH_vivo", "pwVAL": "pwVAL_vivo", "mVWAP": "mVWAP_vivo", "mVAH": "mVAH_vivo",
    "mVAL": "mVAL_vivo", "7D rVWAP": "r7D_vivo",
    "H4 13EMA": "h4_13", "H4 21EMA": "h4_21", "H4 34EMA": "h4_34", "H4 100EMA": "h4_100", "H4 200EMA": "h4_200",
}


def a_utc_ms(s: str) -> int:
    """'09-28 18:05' (hora de las capturas, UTC+2, año 2026) → ms UTC."""
    d = dt.datetime.strptime("2026-" + s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_CAPTURAS)
    return int(d.timestamp() * 1000)


def ema_h4_vivo(df: pl.DataFrame, n: int) -> np.ndarray:
    """EMA de 4h como la muestra el gráfico en vivo: estado de la última vela de 4h cerrada + el close actual."""
    t, c = df["open_time"].to_numpy(), df["close"].to_numpy()
    b = t // 14_400_000
    fin = np.r_[b[1:] != b[:-1], True]
    e_cerr = ema(c[fin], n)                         # EMA sobre los cierres de 4h
    idx = np.cumsum(np.r_[0, fin[:-1]])             # índice de la vela de 4h en formación
    a = 2.0 / (n + 1)
    prev = np.r_[np.nan, e_cerr][idx]               # EMA de la última cerrada
    return np.where(np.isnan(prev), np.nan, prev + a * (c - prev))


def base(desde: str, hasta: str) -> pl.DataFrame:
    df = f6.por_minuto(desde, hasta).sort("open_time")
    # niveles del día previo (perfil diario UTC terminado)
    dia = pl.col("open_time") // 86_400_000
    pd_ = (df.group_by(dia.alias("d")).agg(pdVAH=pl.col("dVAH").last(), pdVAL=pl.col("dVAL").last(),
                                          pdPOC=pl.col("dPOC").last(), pdVWAP=pl.col("vwap_d").last())
           .with_columns(pl.col("d") + 1))
    df = df.with_columns(d=dia).join(pd_, on="d", how="left").sort("open_time")
    for n in (13, 21, 34, 100, 200):
        df = df.with_columns(pl.Series(f"h4_{n}", ema_h4_vivo(df, n)))
    # contexto previo
    df = df.with_columns(
        ret15=(pl.col("close") - pl.col("close").shift(15)) / pl.col("atr14"),
        ret60=(pl.col("close") - pl.col("close").shift(60)) / pl.col("atr14"),
        min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60),
        lo_dia=pl.col("low").cum_min().over("d"), hi_dia=pl.col("high").cum_max().over("d"),
    )
    return df


def ubicar(tr: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
    t, h, l = df["open_time"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    filas = []
    for r in tr.iter_rows(named=True):
        p = float(r["entrada"])
        a, b, ap = a_utc_ms(r["desde"]), a_utc_ms(r["hasta"]), a_utc_ms(r["aprox"])
        if r["exacta"] == "si":
            m = ap // 60_000 * 60_000
            filas.append({"id": r["id"], "t_entrada": m, "episodios": 1, "dif_min": 0, "toca": True, "candidatos": [m]})
            continue
        i0, i1 = np.searchsorted(t, a), np.searchsorted(t, b, side="right")
        ok = (l[i0:i1] - PREMIO_LO <= p) & (p <= h[i0:i1] + PREMIO_HI)
        if not ok.any() and r.get("fuente") == "hora de Juan":   # su precio no toca: me quedo con la vela que marcó Juan
            m = ap // 60_000 * 60_000
            filas.append({"id": r["id"], "t_entrada": m, "episodios": 0, "dif_min": 0, "toca": False, "candidatos": [m]})
            continue
        if not ok.any():
            filas.append({"id": r["id"], "t_entrada": None, "episodios": 0, "dif_min": None, "toca": False, "candidatos": []})
            continue
        k = np.flatnonzero(ok)
        cortes = np.flatnonzero(np.diff(k) > 3) + 1
        epis = 1 + cortes.size
        candidatos = [int(t[i0 + k[0]])] + [int(t[i0 + k[c]]) for c in cortes]   # primer minuto de cada paso del precio
        j = k[np.argmin(np.abs(t[i0 + k] - ap))]
        filas.append({"id": r["id"], "t_entrada": int(t[i0 + j]), "episodios": epis,
                      "dif_min": int((t[i0 + j] - ap) // 60_000), "toca": True, "candidatos": candidatos})
    return tr.join(pl.DataFrame(filas, schema={"id": pl.Utf8, "t_entrada": pl.Int64, "episodios": pl.Int64,
                                               "dif_min": pl.Int64, "toca": pl.Boolean, "candidatos": pl.List(pl.Int64)}), on="id")


def leer_indicadores(tr: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
    t = df["open_time"].to_numpy()
    cols = {c: df[c].to_numpy() for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32)}
    filas = []
    for r in tr.iter_rows(named=True):
        if r["t_entrada"] is None:
            filas.append({"id": r["id"]})
            continue
        i = int(np.searchsorted(t, r["t_entrada"]))
        k = i - 1                                   # última vela cerrada antes de la entrada
        sg = 1.0 if r["lado"] == "long" else -1.0
        p = float(r["entrada"]) - 20.0              # su precio llevado a Binance (premio medio ≈ 20 USD)
        atr = cols["atr14"][k]
        v = lambda c, j=k: float(cols[c][j])  # noqa: E731
        # nivel más cercano y distancia en ATR (con signo: + = el nivel está del lado "a favor" = soporte para long)
        dist = {n: (p - v(c, i)) / atr for n, c in NIVELES.items() if c in cols and not np.isnan(cols[c][i])}
        cerca = sorted(dist.items(), key=lambda x: abs(x[1]))
        n_05 = sum(abs(d) <= 0.5 for d in dist.values())
        bulls, bears = v("ash_bulls"), v("ash_bears")
        e11, e25 = v("ema11"), v("ema25")
        g_hist = cols["ash_bulls"][k - 30:k + 1] - cols["ash_bears"][k - 30:k + 1]
        x_hist = cols["ema11"][k - 30:k + 1] - cols["ema25"][k - 30:k + 1]
        ult_cruce = lambda s: int(np.argmax((np.sign(s[::-1][1:]) != np.sign(s[::-1][0])))) + 1 if (np.sign(s) != np.sign(s[-1])).any() else 31  # noqa: E731
        sigma = v("vwap_d_p1", i) - v("vwap_d", i)
        sw = v("vwap_w_p1", i) - v("vwap_w", i)
        b5, r5 = v("ash_bulls_5m_vivo"), v("ash_bears_5m_vivo")
        filas.append({
            "id": r["id"],
            "z_vwap_d": (p - v("vwap_d", i)) / sigma if sigma > 0 else np.nan,
            "z_vwap_w": (p - v("vwap_w", i)) / sw if sw > 0 else np.nan,
            "sobre_vwap_w": p > v("vwap_w", i), "sobre_rvwap": p > v("rVWAP", i),
            "nivel1": cerca[0][0], "dist1_atr": cerca[0][1], "nivel2": cerca[1][0], "dist2_atr": cerca[1][1],
            "niveles_05atr": n_05,
            "ash1_a_favor": (bulls > bears) == (sg > 0), "ash1_gn": sg * (bulls - bears) / (bulls + bears),
            "ash1_velas_desde_cruce": ult_cruce(g_hist),
            "xo_a_favor": (e11 > e25) == (sg > 0), "xo_velas_desde_cruce": ult_cruce(x_hist),
            "precio_vs_xo": "arriba" if p > max(e11, e25) else ("abajo" if p < min(e11, e25) else "entre"),
            "ash5_a_favor": (b5 > r5) == (sg > 0), "ash5_gn": sg * (b5 - r5) / (b5 + r5),
            "rvol": v("rvol"), "rvol_max5": float(np.nanmax(cols["rvol"][k - 4:k + 1])),
            "ret15_atr": sg * v("ret15"), "ret60_atr": sg * v("ret60"),
            "cvd5": sg * v("cvd5"), "cvd15": sg * v("cvd15"),
            "grandes5_favor": v("nb5") if sg > 0 else v("ns5"), "grandes5_contra": v("ns5") if sg > 0 else v("nb5"),
            "oi15": v("oi15"),
            # barrida: el extremo en contra de las últimas 5 velas es el más extremo de los últimos 60 min
            "barrida60": bool((np.nanmin(cols["low"][k - 4:k + 1]) <= v("min60")) if sg > 0 else (np.nanmax(cols["high"][k - 4:k + 1]) >= v("max60"))),
            "pos_rango_dia": (p - v("lo_dia")) / (v("hi_dia") - v("lo_dia")) if v("hi_dia") > v("lo_dia") else np.nan,
            "atr14": atr, "hora_utc": int((r["t_entrada"] // 60_000) % 1440) / 60,
        })
    return tr.join(pl.DataFrame(filas, infer_schema_length=None), on="id", how="left")


def confianza(tr: pl.DataFrame) -> pl.DataFrame:
    """alta: orden con hora, o un único paso del precio cerca de donde lo dibujó; media: ≤ 5 pasos y ≤ 30 min de la
    hora leída; baja: el resto (la ubicación al minuto es dudosa, la zona de precio no)."""
    e, d = pl.col("episodios"), pl.col("dif_min").abs()
    return tr.with_columns(confianza=pl.when(pl.col("fuente") == "hora de Juan").then(pl.lit("Juan"))
                           .when(pl.col("fuente") == "ubicación confirmada").then(pl.lit("confirmada"))
                           .when(pl.col("exacta") == "si").then(pl.lit("alta"))
                           .when((e <= 2) & (d <= 15)).then(pl.lit("alta"))
                           .when((e <= 5) & (d <= 30)).then(pl.lit("media")).otherwise(pl.lit("baja")))


RASGOS = {  # nombre → (expresión sobre las entradas, expresión sobre la línea de base); todo "a favor del trade"
    "Precio del lado barato del VWAP de sesión (long debajo / short arriba)": ("z_vwap_d", lambda z: z < 0),
    "Lejos del VWAP de sesión: más allá de 1σ en contra (long < −1σ / short > +1σ)": ("z_vwap_d", lambda z: z <= -1),
    "Más allá de 2σ en contra": ("z_vwap_d", lambda z: z <= -2),
    "Del lado de la tendencia: long sobre el rolling VWAP / short debajo": ("rv", lambda x: x > 0),
    "Del lado de la semana: long sobre el VWAP semanal / short debajo": ("wv", lambda x: x > 0),
    "Un nivel a ≤ 0,25 ATR": ("dmin", lambda x: x <= 0.25),
    "Un nivel a ≤ 0,5 ATR": ("dmin", lambda x: x <= 0.5),
    "Venía en contra los últimos 15 min (≥ 1 ATR)": ("ret15", lambda x: x <= -1),
    "Venía a favor los últimos 15 min (≥ 1 ATR)": ("ret15", lambda x: x >= 1),
    "Barrida: extremo en contra de 60 min en las últimas 5 velas": ("barrida", lambda x: x),
    "ASH 1m ya a favor": ("ash1", lambda x: x),
    "XO 1m ya cruzadas a favor": ("xo", lambda x: x),
    "ASH 5m (en formación) a favor": ("ash5", lambda x: x),
    "RVOL ≥ 1,5 en alguna de las últimas 5 velas": ("rvolmax5", lambda x: x >= 1.5),
    "CVD 5 min a favor (más agresión a favor)": ("cvd5", lambda x: x > 0),
    "Dentro de la ventana de Juan (00:00 UTC → 12:00 NY)": ("ventana", lambda x: x),
}


def linea_base(df: pl.DataFrame) -> pl.DataFrame:
    """Los mismos rasgos en todos los minutos de septiembre, como si se entrara long y short en cada uno."""
    import senales
    sep = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m") == "2026-09")
    cols = [c for c in NIVELES.values() if c in sep.columns]
    dmin = pl.min_horizontal([(pl.col("close") - pl.col(c)).abs() for c in cols]) / pl.col("atr14")
    z = (pl.col("close") - pl.col("vwap_d")) / (pl.col("vwap_d_p1") - pl.col("vwap_d"))
    comun = dict(dmin=dmin, rvolmax5=pl.col("rvol").rolling_max(5), ventana=senales.ventana_operativa(pl.col("open_time")))
    out = []
    for lado, sg in (("long", 1.0), ("short", -1.0)):
        bar = (pl.col("low").rolling_min(5) <= pl.col("min60")) if sg > 0 else (pl.col("high").rolling_max(5) >= pl.col("max60"))
        out.append(sep.select(
            lado=pl.lit(lado), z_vwap_d=sg * z, rv=sg * (pl.col("close") - pl.col("rVWAP")), wv=sg * (pl.col("close") - pl.col("vwap_w")),
            ret15=sg * pl.col("ret15"), barrida=bar, ash1=((pl.col("ash_bulls") > pl.col("ash_bears")) == (sg > 0)),
            xo=((pl.col("ema11") > pl.col("ema25")) == (sg > 0)),
            ash5=((pl.col("ash_bulls_5m_vivo") > pl.col("ash_bears_5m_vivo")) == (sg > 0)), cvd5=sg * pl.col("cvd5"), **comun))
    return pl.concat(out)


def similitudes(tr: pl.DataFrame, df: pl.DataFrame) -> str:
    import senales
    e = tr.filter(pl.col("t_entrada").is_not_null()).with_columns(
        sg=pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0))
    e = e.with_columns(
        rv=pl.when(pl.col("sobre_rvwap") == (pl.col("sg") > 0)).then(1.0).otherwise(-1.0),
        wv=pl.when(pl.col("sobre_vwap_w") == (pl.col("sg") > 0)).then(1.0).otherwise(-1.0),
        dmin=pl.col("dist1_atr").abs(), ret15=pl.col("ret15_atr"), barrida=pl.col("barrida60"), ash1=pl.col("ash1_a_favor"),
        xo=pl.col("xo_a_favor"), ash5=pl.col("ash5_a_favor"), rvolmax5=pl.col("rvol_max5"),
        ventana=senales.ventana_operativa(pl.col("t_entrada")), z_vwap_d=pl.col("z_vwap_d") * pl.col("sg"))
    lb = linea_base(df)
    peso = {l: e.filter(pl.col("lado") == l).height / e.height for l in ("long", "short")}
    filas = []
    for nom, (col, f) in RASGOS.items():
        pe = float(e.select(f(pl.col(col)).cast(pl.Float64).mean()).item())
        pa = float(e.filter(pl.col("confianza").is_in(["Juan", "confirmada"])).select(f(pl.col(col)).cast(pl.Float64).mean()).item())
        pb = sum(peso[l] * float(lb.filter(pl.col("lado") == l).select(f(pl.col(col)).cast(pl.Float64).mean()).item()) for l in peso)
        filas.append((nom, pe, pa, pb))
    n, na = e.height, e.filter(pl.col("confianza").is_in(["Juan", "confirmada"])).height
    l = [f"| Rasgo al entrar | Sus entradas (n={n}) | Revisadas por Juan (n={na}) | Cualquier minuto de sep. | Veces más frecuente |",
         "|---|---|---|---|---|"]
    for nom, pe, pa, pb in filas:
        l.append(f"| {nom} | {pe:.0%} | {pa:.0%} | {pb:.0%} | {pe / pb:.1f}× |" if pb > 0 else f"| {nom} | {pe:.0%} | {pa:.0%} | – | – |")
    niv = e.group_by("nivel1").agg(n=pl.len(), cerca=(pl.col("dmin") <= 0.5).sum()).sort("n", descending=True)
    l += ["", "Nivel más cercano a la entrada (y cuántas veces a ≤ 0,5 ATR):", ""]
    l += [f"- {r['nivel1']}: {r['n']} ({r['cerca']} a ≤ 0,5 ATR)" for r in niv.iter_rows(named=True)]
    datos = {"n": n, "n_conf": na, "rasgos": [{"rasgo": a, "todas": b, "conf": c, "base": d} for a, b, c, d in filas],
             "niveles": niv.to_dicts()}
    (OUT / "similitudes.json").write_text(__import__("json").dumps(datos, ensure_ascii=False))
    return "\n".join(l)


def main() -> None:
    tr = pl.read_csv(RAIZ / "marcas" / "trader_sep2026" / "trades.csv", schema_overrides={"entrada": pl.Float64})
    tr = tr.filter(pl.col("excluir") != "si")          # trades que Juan no encontró en la captura
    df = base("2026-07", "2026-09")
    tr = confianza(ubicar(tr, df))
    tr = leer_indicadores(tr, df)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "similitudes.md").write_text(similitudes(tr, df) + "\n")
    print((OUT / "similitudes.md").read_text())
    tr.write_parquet(OUT / "entradas.parquet")
    tr.write_csv(OUT / "entradas.csv", float_precision=3)
    with pl.Config(tbl_rows=200, tbl_cols=20, tbl_width_chars=250):
        print(tr.select("id", "lado", "entrada", "episodios", "dif_min", "nivel1", "dist1_atr", "z_vwap_d", "ash1_a_favor",
                        "xo_a_favor", "barrida60", "ret15_atr"))


if __name__ == "__main__":
    main()
