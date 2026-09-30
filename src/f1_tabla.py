"""F1 · Tabla de validación contra TradingView (CLAUDE.md §3.4).

10 timestamps al azar dentro de la ventana operativa (00:00 UTC → 12:00 America/New_York) de 2023-01 a 2026-06
(jul–sep 2026 queda afuera mientras la reserva esté pendiente), en días distintos, con al menos uno un lunes
00:0x UTC y uno en un día de cambio de horario de EE. UU. Más un caso extra: una vela oficial reparada.

Salidas: reports/f1/tabla_validacion.md  y  tests/paridad_tv.csv (plantilla para cargar los valores de TV).
"""
from __future__ import annotations

import datetime as dt
import random
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

import indicadores as ind

RAIZ = Path(__file__).resolve().parent.parent
NY, ART, UTC = ZoneInfo("America/New_York"), ZoneInfo("America/Argentina/Buenos_Aires"), dt.timezone.utc
CAMBIOS_DST = [dt.date(2023, 3, 12), dt.date(2023, 11, 5), dt.date(2024, 3, 10), dt.date(2024, 11, 3),
               dt.date(2025, 3, 9), dt.date(2025, 11, 2), dt.date(2026, 3, 8)]

# (columna, etiqueta, dónde se lee en TV)
FILAS = [
    ("close", "close", "ventana de datos"),
    ("ema11", "XO EMA 11", "ventana de datos"),
    ("ema25", "XO EMA 25", "ventana de datos"),
    ("ash_bulls", "ASH Bulls", "ventana de datos"),
    ("ash_bears", "ASH Bears", "ventana de datos"),
    ("rvol", "RVOL real", "ventana de datos"),
    ("vwap_d", "VWAP sesión", "ventana de datos"),
    ("vwap_d_p1", "VWAP sesión +σ1", "ventana de datos"),
    ("vwap_d_m1", "VWAP sesión −σ1", "ventana de datos"),
    ("vwap_d_p2", "VWAP sesión +σ2", "ventana de datos"),
    ("vwap_d_m2", "VWAP sesión −σ2", "ventana de datos"),
    ("vwap_w", "VWAP semana", "ventana de datos"),
    ("vwap_w_p1", "VWAP semana +σ1", "ventana de datos"),
    ("vwap_w_m1", "VWAP semana −σ1", "ventana de datos"),
    ("vwap_w_p2", "VWAP semana +σ2", "ventana de datos"),
    ("vwap_w_m2", "VWAP semana −σ2", "ventana de datos"),
    ("dVAH", "dVAH", "Bar Replay"),
    ("dVAL", "dVAL", "Bar Replay"),
    ("dPOC", "dPOC (prenderlo en ⑫)", "Bar Replay"),
    ("rVAH", "rVAH", "Bar Replay"),
    ("rVAL", "rVAL", "Bar Replay"),
    ("r7D", "7D rVWAP", "Bar Replay"),
    ("r30D", "30D rVWAP", "Bar Replay"),
    ("DO", "DO", "Bar Replay"),
    ("WO", "WO", "Bar Replay"),
    ("PWH", "PWH", "Bar Replay"),
    ("PWL", "PWL", "Bar Replay"),
    ("MNDAY_H", "MNDAY-H", "Bar Replay"),
    ("MNDAY_L", "MNDAY-L", "Bar Replay"),
]
DOBLES = {"r7D", "r30D", "MNDAY_H", "MNDAY_L"}  # tienen versión vivo e historial


def en_ventana(t_ms: int) -> bool:
    u = dt.datetime.fromtimestamp(t_ms / 1000, UTC)
    fin = dt.datetime.combine(u.date(), dt.time(12), NY).astimezone(UTC)
    return u < fin


def elegir(df: pl.DataFrame, semilla: int = 20260930) -> list[int]:
    rnd = random.Random(semilla)
    ts = [t for t in df["open_time"].to_list()]
    elegidos: list[int] = []
    dias: set = set()

    def agregar(t):
        d = dt.datetime.fromtimestamp(t / 1000, UTC).date()
        if d in dias or not en_ventana(t):
            return False
        elegidos.append(t)
        dias.add(d)
        return True

    # 1) un lunes 00:0x UTC
    lunes = [t for t in ts if (t // 60000) % 1440 < 10 and dt.datetime.fromtimestamp(t / 1000, UTC).weekday() == 0]
    agregar(rnd.choice(lunes))
    # 2) un día de cambio de horario de EE. UU., en la última hora de la ventana (donde importa el cambio)
    d = rnd.choice(CAMBIOS_DST)
    fin = dt.datetime.combine(d, dt.time(12), NY).astimezone(UTC)
    agregar(int((fin - dt.timedelta(minutes=rnd.randint(1, 50))).timestamp() * 1000))
    # 3) el resto al azar, días distintos
    while len(elegidos) < 10:
        agregar(rnd.choice(ts))
    return sorted(elegidos)


def fmt(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return str(x)
    return f"{x:,.2f}".replace(",", " ") if abs(x) >= 100 else f"{x:.4f}"


def main() -> None:
    df = ind.cargar("2023-01", "2026-06")
    sel = elegir(df)
    extra = int(dt.datetime(2023, 11, 10, 15, 10, tzinfo=UTC).timestamp() * 1000)  # vela oficial reparada
    filas = df.filter(pl.col("open_time").is_in(sel + [extra])).sort("open_time").to_dicts()

    enc = []
    for r in filas:
        u = dt.datetime.fromtimestamp(r["open_time"] / 1000, UTC)
        a = u.astimezone(ART)
        nota = ""
        if u.date() in CAMBIOS_DST:
            nota = " · cambio de horario EE. UU."
        if u.weekday() == 0 and u.hour == 0 and u.minute < 10:
            nota = " · lunes 00:0x UTC"
        if r["open_time"] == extra:
            nota = " · EXTRA: vela oficial plana reparada"
        enc.append((u.strftime("%Y-%m-%d %H:%M"), a.strftime("%Y-%m-%d %H:%M"), u.strftime("%a"), nota))

    l = ["# F1 · Tabla de validación contra TradingView", "",
         "Gráfico `BINANCE:BTCUSDT.P`, **1m**, con los dos indicadores de `spec/` cargados con la configuración de Juan",
         "(ASH: RSI · 16 · 4 · EMA · close; XO: 11 / 25). La hora es la de **apertura** de la vela (como la muestra TV);",
         "los valores son al **cierre** de esa vela.", "",
         "**Dónde leer cada valor en TV:**",
         "- *ventana de datos*: pasar el mouse sobre la vela; los plots aparecen en la Data Window.",
         "- *Bar Replay*: dVAH/dVAL/dPOC, rVAH/rVAL, 7D, 30D, DO, WO, PWH/PWL y MNDAY sólo se dibujan como etiquetas",
         "  en la última vela (`barstate.islast`). Con Bar Replay parado en la vela, las etiquetas muestran su valor ahí.",
         "- Para 7D, 30D y MNDAY hay dos columnas: **vivo** (lo que se ve en tiempo real, con la vela diaria en formación)",
         "  e **hist** (lo que muestra TV en el historial y probablemente en Bar Replay: la última vela diaria cerrada).",
         "  Anotá cuál de las dos coincide: define qué semántica usa el replay.", "",
         ]
    for n, (u, a, wd, nota) in enumerate(enc, 1):
        l.append(f"- **#{n}** · {u} UTC · {a} ART · {wd}{nota}")
    l.append("")
    cab = "| Valor | TV | " + " | ".join(f"#{n}" for n in range(1, len(filas) + 1)) + " |"
    l += [cab, "|---|---|" + "---|" * len(filas)]
    csv_rows = []
    for col, et, donde in FILAS:
        variantes = [("_vivo", " (vivo)"), ("_hist", " (hist)")] if col in DOBLES else [("", "")]
        for suf, txt in variantes:
            vals = [r[col + suf] for r in filas]
            l.append(f"| {et}{txt} | {donde} | " + " | ".join(fmt(x) for x in vals) + " |")
            for (u, *_), x in zip(enc, vals):
                csv_rows.append({"timestamp_utc": u, "valor": col + suf, "nuestro": x, "tradingview": None})
    l += ["", "Tolerancias propuestas (a acordar): precios y niveles ±0,1 USD (ticks de 0,1); ASH ±0,01; RVOL ±0,001.",
          "Una diferencia chica y pareja en todo el día en las VWAP suele ser volumen distinto entre el feed de TV y Binance;",
          "una diferencia en EMAs/ASH que se achica con el tiempo es semilla (historial distinto)."]
    out = RAIZ / "reports" / "f1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "tabla_validacion.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    pl.DataFrame(csv_rows, schema={"timestamp_utc": pl.Utf8, "valor": pl.Utf8, "nuestro": pl.Float64,
                                   "tradingview": pl.Float64}).write_csv(RAIZ / "tests" / "paridad_tv.csv")
    print("\n".join(l))


if __name__ == "__main__":
    main()
