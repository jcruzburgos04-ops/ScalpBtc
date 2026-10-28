"""Reporte autocontenido de los trades del trader de referencia (septiembre 2026), para pegar en otra conversación.

Junta todo lo identificado: transcripción de las capturas, ubicación en Binance, revisión de Juan, lectura de
indicadores al entrar, resultado en ATR después de la entrada, nivel donde terminó el recorrido a favor, pérdidas
(calaveras) y los hallazgos agregados. Salida: reports/trader_sep/REPORTE_TRADER.md
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

import b2
import f5_niveles as f5
import trader_sep as ts
import volumen
from b2_filtro_niveles import npoc
from b2_tendencias import ema_tf
from datos import leer_velas_1m

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "trader_sep"
CAP = RAIZ / "marcas" / "trader_sep2026"
UTC2 = dt.timezone(dt.timedelta(hours=2))
PREMIO = 20.0   # su exchange cotiza ≈ 10–45 USD arriba de Binance; se usa 20


def hora(ms, tz=dt.timezone.utc):
    return dt.datetime.fromtimestamp(ms / 1000, tz).strftime("%m-%d %H:%M") if ms is not None else ""


def resultado(t, h, l, atr, ts_, lado, p, hor=240):
    """Recorrido después de la entrada (velas de 1m de Binance, precio llevado a Binance)."""
    i = int(np.searchsorted(t, ts_))
    sg = 1 if lado == "long" else -1
    a = atr[i]
    hh, ll = h[i + 1:i + 1 + hor], l[i + 1:i + 1 + hor]
    fav = (hh - p) / a if sg > 0 else (p - ll) / a
    con = (p - ll) / a if sg > 0 else (hh - p) / a

    def antes(x, y):
        kf = np.argmax(fav >= x) if (fav >= x).any() else 10**9
        kc = np.argmax(con >= y) if (con >= y).any() else 10**9
        return "TP" if kf < kc else ("SL" if kc < 10**9 else "nada")
    # recorrido a favor hasta que vuelve a la entrada (después de 5 velas) o 4 h
    vuelve = np.flatnonzero((ll <= p) if sg > 0 else (hh >= p))
    vuelve = vuelve[vuelve > 5]
    fin = vuelve[0] if vuelve.size else hh.size - 1
    j = int(np.argmax(hh[:fin + 1]) if sg > 0 else np.argmin(ll[:fin + 1]))
    pfin = hh[j] if sg > 0 else ll[j]
    return {"mfe_atr": sg * (pfin - p) / a, "mae_antes_mfe_atr": max(float(np.max(con[:j + 1])), 0.0),
            "min_hasta_mfe": j + 1, "t_fin": int(t[i + 1 + j]), "p_fin": float(pfin),
            "r1_1": antes(1, 1), "r2_1": antes(2, 1), "r1_05": antes(1, 0.5)}


def nivel_en(df_cols, i, precio, atr, tol=0.25):
    cerca = [(n, abs(precio - df_cols[c][i]) / atr) for n, c in f5.NIVELES.items()
             if c in df_cols and np.isfinite(df_cols[c][i]) and abs(precio - df_cols[c][i]) <= tol * atr]
    return " / ".join(n for n, _ in sorted(cerca, key=lambda x: x[1])[:3])


def tabla_trades(df, filas, vol):
    t = df["open_time"].to_numpy()
    h, l, atr = (df[x].to_numpy() for x in ("high", "low", "atr14"))
    cols = {c: df[c].cast(pl.Float64).to_numpy() for c in f5.NIVELES.values() if c in df.columns}
    out = []
    for r in filas.iter_rows(named=True):
        if r.get("t_entrada") is None:
            continue
        p = float(r["entrada"]) - PREMIO
        x = resultado(t, h, l, atr, r["t_entrada"], r["lado"], p)
        jf = int(np.searchsorted(t, x["t_fin"]))
        x["nivel_fin"] = nivel_en(cols, jf, x["p_fin"], atr[jf])
        out.append({"id": r["id"], **x})
    return filas.join(pl.DataFrame(out), on="id", how="left").join(vol, on="id", how="left")


def main() -> None:
    df = npoc(volumen.agregar(ts.base("2026-07", "2026-09"), "2026-07", "2026-09")).sort("open_time")
    k = leer_velas_1m("2022-01", "2026-09").select("open_time", "close").sort("open_time")
    e45, _ = ema_tf(k["open_time"].to_numpy(), k["close"].to_numpy(), 45, 200)
    df = df.join(k.with_columns(e45=pl.Series(e45)).select("open_time", "e45"), on="open_time", how="left")
    gan = pl.read_parquet(OUT / "entradas.parquet")
    perd = pl.read_parquet(OUT / "perdidas.parquet")
    tr = pl.read_csv(CAP / "trades.csv")
    rev = pl.read_csv(CAP / "revision_juan.csv").select("id", pl.col("comentario").alias("comentario_juan"))
    kal = pl.read_csv(CAP / "calaveras.csv")

    def extra(d):
        v = b2.rasgos(df, d.select(pl.col("t_entrada").alias("t"), "lado")).select("vol15_rel", "absorcion5", "delta1", "burb_contra15")
        i = np.searchsorted(df["open_time"].to_numpy(), d["t_entrada"].to_numpy()) - 1
        c, e, h4 = (df[x].to_numpy()[i] for x in ("close", "e45", "h4_200"))
        sg = np.where(d["lado"].to_numpy() == "long", 1, -1)
        return pl.DataFrame({"id": d["id"]}).hstack(v).with_columns(
            ema200_45m_a_favor=pl.Series(sg * (c - e) > 0), ema200_4h_a_favor=pl.Series(sg * (c - h4) > 0))

    g = tabla_trades(df, gan.filter(pl.col("t_entrada").is_not_null()), extra(gan.filter(pl.col("t_entrada").is_not_null())))
    g = g.join(rev, on="id", how="left")
    p = tabla_trades(df, perd, extra(perd)).join(kal.select("id", "hora_aprox_trader", "precio_aprox"), on="id", how="left")

    sg = pl.when(pl.col("lado") == "long").then(1.0).otherwise(-1.0)
    r2 = lambda c: pl.col(c).round(2)  # noqa: E731
    comunes = [r2("z_sesion_lado"), r2("z_semana_lado"), "contra_rvwap", "nivel1", r2("dist1_atr"), "niveles_05atr",
               "ash1_a_favor", "xo_a_favor", "ash5_a_favor", r2("rvol_max5"), r2("vol15_rel"), r2("absorcion5"), r2("delta1"),
               r2("ret15_atr"), r2("ret60_atr"), "barrida60", "burb_contra15", "ema200_45m_a_favor", "ema200_4h_a_favor",
               r2("pos_rango_dia"), pl.col("atr14").round(1), r2("mfe_atr"), r2("mae_antes_mfe_atr"), "min_hasta_mfe",
               "nivel_fin", "r1_1", "r2_1"]

    def prep(d):
        return d.with_columns(hora_utc=pl.col("t_entrada").map_elements(hora, return_dtype=pl.Utf8),
                              hora_trader=pl.col("t_entrada").map_elements(lambda m: hora(m, UTC2), return_dtype=pl.Utf8),
                              z_sesion_lado=pl.col("z_vwap_d") * sg, z_semana_lado=pl.col("z_vwap_w") * sg,
                              contra_rvwap=pl.col("sobre_rvwap") != (pl.col("lado") == "long"))
    g, p = prep(g), prep(p)
    csv_g = g.sort("t_entrada").select("id", "captura", "plataforma", "lado", "entrada", "hora_trader", "hora_utc", "confianza",
                                       "revision", *comunes, "comentario_juan").write_csv(float_precision=2)
    csv_p = p.sort("t_entrada").select("id", "captura", "lado", pl.col("entrada").alias("precio_aprox_trader"), "hora_aprox_trader",
                                       "hora_utc", "toca", *comunes).write_csv(float_precision=2)
    exc = tr.filter(pl.col("excluir") == "si").join(rev, on="id", how="left").select(
        "id", "captura", "plataforma", "lado", "entrada", "aprox", "comentario_juan").write_csv()

    # resúmenes
    n = g.height
    pct = lambda d, e: d.select(e.cast(pl.Float64).mean()).item()  # noqa: E731
    res = {x: (pct(g, pl.col(x) == "TP"), pct(p, pl.col(x) == "TP")) for x in ("r1_1", "r2_1")}
    fin_niv = g.filter(pl.col("nivel_fin") != "").height
    largos = pct(g, pl.col("lado") == "long")
    md = f"""# Trader de referencia · trades de septiembre 2026 · reporte completo

Generado el {dt.date.today():%Y-%m-%d} desde el proyecto de backtest de Juan Cruz (BTC 1m). Todo lo que sigue está medido
sobre datos reales de Binance USD-M `BTCUSDT` perpetuo; no hay datos sintéticos.

## 1. Contexto y convenciones (leer antes de usar los números)

- **Quién**: un trader discrecional de BTC en 1m que Juan sigue. Juan mandó 18 capturas de TradingView (`BTCUSDT.P`,
  1m) del 31-ago al 1-oct-2026, con las tarjetas de PnL de sus posiciones (Variational 25–50x, Nado, TxFlow, RISE),
  listas de órdenes con hora y las herramientas long/short de TV. Las perdidas están marcadas con una calavera.
- **Hora**: el eje de sus capturas está en **UTC+2** (verificado con 11 órdenes con hora del 28-sep contra Binance).
  En este reporte `hora_trader` = UTC+2 y `hora_utc` = UTC. Hora argentina = UTC−3.
- **Precio**: su exchange cotiza ≈ 10–45 USD **arriba** de Binance. Todas las mediciones llevan su precio a Binance
  restando {PREMIO:.0f} USD.
- **Ubicación al minuto**: las tarjetas dan el precio de entrada, no la hora. La hora sale de dónde dibujó la entrada
  en el gráfico. Juan revisó las 105 ubicaciones (24 bien, 75 corregidas, 6 "no sé") y excluyó 12. Por pedido suyo se
  toma la vela de Binance más próxima a su hora (±15 min) donde pasa su precio. Columna `confianza`: Juan = hora que
  marcó Juan; confirmada = la ubicación original estaba bien; alta/media = ubicación automática.
- **Muestra sesgada**: las tarjetas muestran posiciones abiertas en ganancia. Las pérdidas salen de las calaveras
  (15, con hora y precio aproximados). Win rate aproximado: 93 ganadas vs 15 perdidas ≈ **86 %**.
- **Las entradas vienen agrupadas** (varias tarjetas por jugada, ampliaciones): no son independientes.
- **Fuera del análisis**: las entradas del 1-oct-2026 (caen en el período de reserva del backtest, oct–dic 2026,
  que no se mira) y 4 posiciones swing que aparecen en varias capturas (TxFlow short 81 511,9 y 81 198,2; Nado long
  76 258 y 76 446).

### Su gráfico
- Líneas: VWAP **blanco = sesión** (ancla 00:00 UTC), VWAP **rojo = semanal** (lunes 00:00 UTC), **amarillo = rolling
  VWAP** (24 h). Bandas ±1σ/±2σ.
- Etiquetas que usa: MNDAY-H/L (máximo/mínimo del lunes), dVAH/dVAL/dPOC (perfil del día), pdVAL (día previo),
  pwVAL/pwVWAP (semana previa), rVAH/rVAL (perfil rolling 24 h), EMAs de 4h 13/34/100, DO.
- Volumen: Volume Suite, CVD, ampliación de velas de TV; en sus reviews menciona orderflow en Aggr (10 s).

### Su estilo según 9 reviews en PDF (feb–may 2026)
Reversión a la media en rango: "edge to edge" (banda ±2σ → banda opuesta), "mean to edge" (VWAP de sesión → ±1σ/±2σ),
"momentum loss", "first test best test". Niveles que más nombra: VWAP de sesión ("the mean") y sus bandas, S/R manuales,
VWAP anclados, DO / apertura de futuros / NYO / IB, bandas semanales, dVAL, cinta de EMAs. Lee orderflow (esfuerzo sin
resultado, absorción), elige el contexto ("meta" del día) y maneja el trade (scratch rápido, parciales).

## 2. Qué hace al entrar (93 ganadas, mismo lado, vs un minuto cualquiera de septiembre)

{(OUT / "similitudes.md").read_text().split(chr(10) + chr(10) + "Nivel")[0]}

Además (rasgos de volumen, 93 entradas vs señales de precio que no tomó vs minuto cualquiera): volumen de 15 min ≥ 1,5×
lo normal 68 % / 28 % / 31 % (mediana 2,6× / 1,0× / 1,0×); absorción (volumen alto con poco rango) ≥ 2: 32 % / 4 % / 5 %;
≥ 15 órdenes grandes en contra en 15 min 61 % / 24 % / 22 %; delta de la vela de entrada a favor 52 % (mediana +1 %): entra
cuando la agresión en contra se agota. Tendencia: a favor de la EMA 200 de 4h el 78 % (opera ~{largos:.0%} longs en un mes
alcista). Sus entradas casi nunca están pegadas a un nivel (≤ 0,5 ATR: 48 % vs 45 % al azar).

**Resumen**: compra abajo de la media de la sesión (más allá de −1σ), después de una barrida del mínimo de la última hora
y de una caída de ~1 ATR en 15 min, con volumen alto y absorción, ANTES de que giren los osciladores (ASH/XO de 1m y 5m
todavía en contra), a favor de la tendencia de 45m–4h y en contra del rolling VWAP de 24 h.

## 3. Ganadas vs perdidas (93 vs 15 calaveras)

{(OUT / "perdidas_vs_ganadas.md").read_text()}
Lectura: sus pérdidas son entradas "de confirmación" a mitad de camino (cerca del VWAP, sin barrida, con los osciladores
ya a favor, menos volumen y absorción); sus ganadoras son las de extremo con absorción. n = 15: descriptivo.

## 4. Qué pasa después de entrar (velas de 1m de Binance, 4 h)

- Avanza +1 ATR antes de ir −1 ATR en contra: ganadas {res['r1_1'][0]:.0%}, perdidas {res['r1_1'][1]:.0%}.
- Avanza +2 ATR antes de −1 ATR (relación 1:2): ganadas {res['r2_1'][0]:.0%}, perdidas {res['r2_1'][1]:.0%}.
- Recorrido a favor de las ganadas hasta que el precio vuelve a la entrada (o 4 h): mediana
  {g['mfe_atr'].median():.1f} ATR (p25 {g['mfe_atr'].quantile(0.25):.1f}, p75 {g['mfe_atr'].quantile(0.75):.1f}), en una mediana de
  {g['min_hasta_mfe'].median():.0f} minutos. En contra antes de ese máximo: mediana {g['mae_antes_mfe_atr'].median():.2f} ATR; el {(g['mae_antes_mfe_atr'] <= 0).mean():.0%} nunca fue en contra de su precio (entra muy cerca del extremo).
- Para comparar: las señales automáticas que intentaron copiarlo (B2) dan 50 % en +1/−1 y 34 % en +2/−1 (≈ azar).

## 5. Dónde termina el recorrido a favor (proxy de sus salidas)

No se pudieron leer automáticamente las cajas long/short de TV (muy tenues). Se usa el extremo a favor que alcanzó cada
ganadora antes de volver a la entrada. {fin_niv} de {n} terminan a ≤ 0,25 ATR de algún nivel (columna `nivel_fin`).

{(OUT / "salidas.md").read_text().split("## 2.")[1].split(chr(10), 1)[1].strip()}

Placebo = el mismo nivel desplazado ±0,2–1 % por día; "veces más" = cuánto más frecuente que el placebo.

## 6. Qué se sacó de esto en el backtest (resumen, sin comisiones, en R)

- Copiar sus entradas con reglas (estrategia "B2": más allá de ±1,5σ + volumen + absorción + vela que gira con delta a
  favor) detecta ~45 % de sus entradas, pero el resultado cae al azar: lo que no se pudo codificar es su selección del
  contexto y su manejo del trade. B2 congelada (filtro EMA 200 de 45m, TP VWAP): +0,064 R por trade en test, gana 13 %.
- Lo que sí se trasladó: el **filtro de tendencia EMA 200 de 45m** (el más robusto de 24 filtros) y el **TP en el nivel
  opuesto** (MNDAY-H/L, VWAP ±2σ de sesión y semanal, dVAH/dVAL), que mejoran la estrategia de Juan.
- Estudio de niveles 2025–2026 con placebo y corrección por comparaciones múltiples: MNDAY-L y MNDAY-H son los niveles
  que más rechazan (+8,5 y +7,9 puntos sobre el placebo); el VWAP de sesión, ±1σ, dPOC y DO se atraviesan MÁS que el
  placebo.

## 7. Datos por trade

Columnas (todas medidas con la última vela de 1m cerrada antes de la entrada; "a favor" = en la dirección del trade):
- `entrada`: precio de la tarjeta (su exchange; Binance ≈ −{PREMIO:.0f}). `hora_trader` UTC+2, `hora_utc` UTC (minuto de Binance).
- `z_sesion_lado`, `z_semana_lado`: distancia al VWAP de sesión / semanal en σ, con signo del trade (negativo = lado barato:
  long debajo, short arriba). `contra_rvwap`: long debajo / short arriba del rolling VWAP 24 h.
- `nivel1`, `dist1_atr`: nivel más cercano y distancia en ATR(14) de 1m (+ = el nivel queda del lado del soporte).
  `niveles_05atr`: cuántos niveles a ≤ 0,5 ATR.
- `ash1/xo/ash5_a_favor`: ASH 1m (RSI 16/4 EMA), cruce de EMAs 11/25 de 1m y ASH de 5m en formación ya a favor.
- `rvol_max5`: RVOL máximo de las últimas 5 velas. `vol15_rel`: volumen de 15 min / mediana del día. `absorcion5`:
  volumen relativo de 5 velas / rango de 5 velas en ATR. `delta1`: (compras − ventas agresivas) / volumen de la vela.
- `ret15_atr`, `ret60_atr`: movimiento de 15 / 60 min en ATR, con signo del trade (negativo = venía en contra).
- `barrida60`: el extremo en contra de las últimas 5 velas es el más extremo de los últimos 60 min.
- `burb_contra15`: órdenes a mercado ≥ 100 k USD en contra en los últimos 15 min.
- `ema200_45m_a_favor`, `ema200_4h_a_favor`: precio del lado del trade respecto de esas EMAs.
- `pos_rango_dia`: posición en el rango del día UTC hasta ese momento (0 = mínimo, 1 = máximo).
- `mfe_atr`: recorrido a favor hasta que vuelve a la entrada (o 4 h); `mae_antes_mfe_atr`: lo máximo en contra antes de
  ese extremo; `min_hasta_mfe`: minutos hasta el extremo; `nivel_fin`: niveles a ≤ 0,25 ATR del extremo.
- `r1_1`, `r2_1`: qué llega primero en 4 h: +1 ATR / −1 ATR y +2 ATR / −1 ATR (TP, SL o nada).
- `revision`: control de Juan de la ubicación automática original (bien / mal → corregida / nose).

### 7.1 Ganadas (tarjetas, {n})

```csv
{csv_g}```

### 7.2 Perdidas (calaveras, {p.height}; hora y precio aproximados, `toca` = el precio pasó por ahí en ±30 min; con `toca` = false la ubicación no es confiable y sus columnas tampoco: K07, K13 y K16, por ejemplo)

```csv
{csv_p}```

### 7.3 Excluidas por Juan (no se encontró el trade en el gráfico, duplicadas o lado dudoso)

```csv
{exc}```
"""
    (OUT / "REPORTE_TRADER.md").write_text(md)
    print(md[:3000])
    print("...", len(md), "caracteres")


if __name__ == "__main__":
    main()
