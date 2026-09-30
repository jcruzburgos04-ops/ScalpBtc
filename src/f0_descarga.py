"""F0 · Descarga, verificación de CHECKSUM y conversión a parquet compacto.

Fuente: data.binance.vision vía su endpoint S3 (el host directo está bloqueado en el entorno cloud).
Todo lo crudo se baja a data/raw/, se verifica (sha256), se procesa y se BORRA: los zips se pueden
volver a bajar gratis en cualquier momento, así que solo se guarda lo procesado en data/proc/.

Salidas (un archivo por mes, AAAA-MM.parquet, zstd):
  klines_1m/       velas oficiales last price (float64, columnas originales de Binance)
  mark_1m/         mark price 1m          (open_time, open, high, low, close)
  index_1m/        index price 1m         (ídem)
  premium_1m/      premium index 1m       (ídem)
  metrics_5m/      OI y ratios cada 5m    (create_time en ms UTC)
  bars_1s/         barras de 1 s desde aggTrades, codificación delta (ver ESQUEMA_1S)
  ordenes_grandes/ órdenes a mercado reconstruidas (agrupadas por ms y lado) con nocional >= PISO_ORDEN_USD
  liq_coinm/       liquidationSnapshot COIN-M BTCUSD_PERP (único archivo real de liquidaciones público)
Integridad: reports/f0/integridad/AAAA-MM.json

Uso:  python src/f0_descarga.py 2022-01 2026-09 [--solo klines,mark,...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import duckdb
import polars as pl
import requests

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw" / str(os.getpid())
PROC = RAIZ / "data" / "proc"
INTEG = RAIZ / "reports" / "f0" / "integridad"

ESCALA_P = 100  # precio en centésimos: el tick de BTCUSDT fue 0,01 en 2022 y después 0,1; 0,01 cubre los dos
ESCALA_Q = 1000  # cantidad en unidades de 0.001 BTC (step de BTCUSDT)
PISO_ORDEN_USD = 100_000  # ~p95 del nocional por orden (mar-2025); el umbral "grande" se elige después por percentil móvil

ESQUEMA_1S = """\
bars_1s (una fila por segundo CON trades; los segundos sin trades no existen):
  dt       int32  segundos desde la fila anterior (la 1.ª fila: segundos desde el inicio del mes UTC)
  do       int32  open − close de la fila anterior, en 0,01 USDT (la 1.ª fila: open absoluto)
  dh, dl   int32  high − open y open − low, en 0,01 USDT
  dc       int32  close − open, en 0,01 USDT
  v, vb    int32  volumen total y volumen taker buy, en 0.001 BTC
  n_agg    int32  n.º de aggTrades;  ntx = n.º de trades − n_agg
  ms_first, ms_last int16  ms dentro del segundo del primer y último trade
Decodificar con src/datos.py:leer_1s() -> ts (ms), o/h/l/c (float), v, vb (BTC), n_agg, n_trades, ms_first, ms_last.
"""

KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
              "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


# ───────────────────────────── descarga ─────────────────────────────

def bajar(ruta: str, destino: Path, reintentos: int = 5) -> Path:
    """Baja ruta (relativa al bucket) y verifica su .CHECKSUM. Devuelve el path local del zip."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    for i in range(reintentos):
        try:
            chk = requests.get(f"{S3}/{ruta}.CHECKSUM", timeout=60)
            chk.raise_for_status()
            esperado = chk.text.split()[0]
            with requests.get(f"{S3}/{ruta}", stream=True, timeout=120) as r:
                r.raise_for_status()
                h = hashlib.sha256()
                with open(destino, "wb") as fh:
                    for bloque in r.iter_content(1 << 22):
                        fh.write(bloque)
                        h.update(bloque)
            if h.hexdigest() != esperado:
                raise ValueError(f"CHECKSUM no coincide: {ruta}")
            return destino
        except Exception as e:  # red o checksum: reintento con backoff
            if i == reintentos - 1:
                raise
            print(f"  reintento {i + 1} {ruta}: {e}")
            time.sleep(2 ** (i + 1))
    raise RuntimeError("inalcanzable")


def existe(ruta: str, reintentos: int = 5) -> bool:
    for i in range(reintentos):
        try:
            return requests.head(f"{S3}/{ruta}", timeout=30).status_code == 200
        except requests.RequestException as e:
            if i == reintentos - 1:
                raise
            print(f"  reintento {i + 1} HEAD {ruta}: {e}")
            time.sleep(2 ** (i + 1))
    return False


def meses(desde: str, hasta: str) -> list[str]:
    d = dt.date.fromisoformat(desde + "-01")
    h = dt.date.fromisoformat(hasta + "-01")
    out = []
    while d <= h:
        out.append(d.strftime("%Y-%m"))
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return out


def meses_ant(mes: str) -> str:
    return (dt.date.fromisoformat(mes + "-01") - dt.timedelta(days=1)).strftime("%Y-%m")


def dias_del_mes(mes: str) -> list[str]:
    d = dt.date.fromisoformat(mes + "-01")
    ayer = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    out = []
    while d.strftime("%Y-%m") == mes and d <= ayer:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def mes_cerrado(mes: str) -> bool:
    hoy = dt.datetime.now(dt.timezone.utc).date()
    return mes < hoy.strftime("%Y-%m")


def zips_del_mes(dataset: str, sub: str, mes: str, simbolo: str = "BTCUSDT", mercado: str = "um",
                 solo_daily: bool = False) -> list[Path]:
    """Baja el zip mensual si el mes está cerrado; si no (o si el dataset no tiene monthly), los diarios."""
    base = f"data/futures/{mercado}/{{f}}/{dataset}/{simbolo}/{sub}"
    etiqueta = f"{simbolo}-{sub.rstrip('/') or dataset}" if sub else f"{simbolo}-{dataset}"
    if not solo_daily and mes_cerrado(mes):
        ruta = base.format(f="monthly") + f"{etiqueta}-{mes}.zip"
        return [bajar(ruta, RAW / Path(ruta).name)]
    out = []
    for dia in dias_del_mes(mes):
        ruta = base.format(f="daily") + f"{etiqueta}-{dia}.zip"
        out.append(bajar(ruta, RAW / Path(ruta).name))
    return out


def csv_de_zip(z: Path) -> Path:
    """Descomprime el único CSV del zip al lado y borra el zip."""
    out = subprocess.run(["unzip", "-o", "-q", str(z), "-d", str(z.parent)], capture_output=True)
    if out.returncode:
        raise RuntimeError(out.stderr.decode())
    nombre = subprocess.run(["unzip", "-Z1", str(z)], capture_output=True, text=True).stdout.split()[0]
    z.unlink()
    return z.parent / nombre


def tiene_header(csv: Path) -> bool:
    with open(csv, "rb") as fh:
        primero = fh.read(1)
    return not primero.isdigit()


# ───────────────────────────── velas 1m ─────────────────────────────

def leer_klines(csvs: list[Path]) -> pl.DataFrame:
    dfs = []
    for c in csvs:
        dfs.append(pl.read_csv(c, has_header=tiene_header(c), new_columns=KLINE_COLS,
                               schema_overrides={c: (pl.Int64 if c in ("open_time", "close_time") else pl.Float64)
                                                 for c in KLINE_COLS}))
        c.unlink()
    return pl.concat(dfs).drop("ignore").with_columns(pl.col("count").cast(pl.Int64)).sort("open_time")


def proc_velas(mes: str, dataset: str, carpeta: str, completas: bool) -> pl.DataFrame:
    csvs = [csv_de_zip(z) for z in zips_del_mes(dataset, "1m/", mes)]
    df = leer_klines(csvs)
    if not completas:  # mark/index/premium: volumen y demás columnas vienen en 0
        df = df.select("open_time", "open", "high", "low", "close")
    (PROC / carpeta).mkdir(parents=True, exist_ok=True)
    df.write_parquet(PROC / carpeta / f"{mes}.parquet", compression="zstd", compression_level=19)
    return df


def huecos_1m(df: pl.DataFrame, mes: str) -> dict:
    ini = int(dt.datetime.fromisoformat(mes + "-01").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    fin_d = (dt.date.fromisoformat(mes + "-01").replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    ayer_fin = dt.datetime.now(dt.timezone.utc).date()
    fin_d = min(fin_d, ayer_fin)
    fin = int(dt.datetime.combine(fin_d, dt.time(), dt.timezone.utc).timestamp() * 1000)
    esperado = set(range(ini, fin, 60_000))
    ts = df["open_time"].to_list()
    presentes = set(ts)
    faltan = sorted(esperado - presentes)
    dias = {}
    for t in faltan:
        d = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date().isoformat()
        dias[d] = dias.get(d, 0) + 1
    return {"esperados": len(esperado), "presentes": len(presentes & esperado), "duplicados": len(ts) - len(presentes),
            "fuera_de_rango": len(presentes - esperado), "faltantes_por_dia": dias}


# ───────────────────────────── aggTrades ─────────────────────────────

AGG_COLS = ("{'agg_trade_id':'BIGINT','price':'DOUBLE','quantity':'DOUBLE','first_trade_id':'BIGINT',"
            "'last_trade_id':'BIGINT','transact_time':'BIGINT','is_buyer_maker':'BOOLEAN'}")


def cargar_aggtrades(con: duckdb.DuckDBPyConnection, csvs: list[Path], tabla: str) -> dict:
    """Carga los CSV en `tabla` descartando filas duplicadas exactas y devuelve el chequeo de ids."""
    partes = " UNION ALL ".join(
        f"SELECT * FROM read_csv('{c}', header={str(tiene_header(c)).lower()}, columns={AGG_COLS})" for c in csvs)
    n_crudo = con.execute(f"SELECT count(*) FROM ({partes})").fetchone()[0]
    con.execute(f"""CREATE OR REPLACE TABLE {tabla} AS SELECT DISTINCT agg_trade_id id,
        CAST(round(price*{ESCALA_P}) AS INTEGER) p, CAST(round(quantity*{ESCALA_Q}) AS BIGINT) q,
        last_trade_id-first_trade_id+1 ntr, first_trade_id, transact_time t, NOT is_buyer_maker buy, price, quantity
        FROM ({partes})""")
    for c in csvs:
        c.unlink()
    r = dict(zip(["n", "min_id", "max_id", "ids_con_contenido_distinto", "saltos_agg_id", "ids_faltantes",
                  "saltos_trade_id"], con.execute(f"""
        WITH s AS (SELECT id, first_trade_id f, first_trade_id+ntr-1 l,
                   lag(id) OVER (ORDER BY id) pid, lag(first_trade_id+ntr-1) OVER (ORDER BY id) pl FROM {tabla})
        SELECT count(*), min(id), max(id), count(*)-count(DISTINCT id), count(*) FILTER (WHERE id-pid>1),
               coalesce(sum(id-pid-1) FILTER (WHERE id-pid>1), 0), count(*) FILTER (WHERE f-pl>1) FROM s""").fetchone()))
    r["filas_duplicadas_descartadas"] = n_crudo - r["n"]
    r["huecos"] = [
        {"ids": int(n), "desde_utc": dt.datetime.fromtimestamp(a / 1000, dt.timezone.utc).isoformat(),
         "hasta_utc": dt.datetime.fromtimestamp(b / 1000, dt.timezone.utc).isoformat()}
        for n, a, b in con.execute(f"""WITH s AS (SELECT id, t, lag(id) OVER (ORDER BY id) pid, lag(t) OVER (ORDER BY id) pt
            FROM {tabla}) SELECT id-pid-1, pt, t FROM s WHERE id-pid>1 ORDER BY id-pid DESC LIMIT 20""").fetchall()]
    return r


def proc_aggtrades(mes: str, klines: pl.DataFrame, id_previo: int | None = None) -> dict:
    con = duckdb.connect()
    (RAW / "duckdb_tmp").mkdir(parents=True, exist_ok=True)
    con.execute(f"SET memory_limit='10GB'; SET preserve_insertion_order=false; "
                f"SET temp_directory='{RAW / 'duckdb_tmp'}';")
    integ: dict = {}
    ids = cargar_aggtrades(con, [csv_de_zip(z) for z in zips_del_mes("aggTrades", "", mes)], "a")
    ids["fuente"] = "monthly" if mes_cerrado(mes) else "daily"
    problemas = lambda r: r["ids_faltantes"] + r["filas_duplicadas_descartadas"] + r["ids_con_contenido_distinto"] \
        + (r["min_id"] - id_previo - 1 if id_previo is not None else 0)
    if mes_cerrado(mes) and problemas(ids) > 0:
        # el archivo mensual de Binance a veces viene roto (días faltantes o repetidos): se rehace con los diarios.
        # Se descarta el mensual antes de cargar los diarios para no tener dos meses en memoria.
        integ["ids_monthly_descartado"] = ids
        con.execute("DROP TABLE a")
        ids = cargar_aggtrades(con, [csv_de_zip(z) for z in zips_del_mes("aggTrades", "", mes, solo_daily=True)], "a")
        ids["fuente"] = "daily"
        if problemas(ids) > problemas(integ["ids_monthly_descartado"]):
            raise ValueError(f"{mes}: los diarios tienen más problemas que el mensual")
    if id_previo is not None:
        ids["ids_faltantes_vs_mes_anterior"] = ids["min_id"] - id_previo - 1
    integ["ids"] = ids
    if ids["ids_con_contenido_distinto"]:
        raise ValueError(f"{mes}: agg_trade_id repetido con contenido distinto")

    # precios y cantidades alineados a la grilla (si no, la codificación entera perdería información)
    integ["fuera_de_grilla"] = con.execute(f"""SELECT count(*) FILTER (WHERE abs(price*{ESCALA_P}-p)>1e-6),
        count(*) FILTER (WHERE abs(quantity*{ESCALA_Q}-q)>1e-6) FROM a""").fetchone()
    if any(integ["fuera_de_grilla"]):  # la codificación entera perdería información: no seguir
        raise ValueError(f"{mes}: precios/cantidades fuera de grilla {integ['fuera_de_grilla']}")
    con.execute("ALTER TABLE a DROP price; ALTER TABLE a DROP quantity; ALTER TABLE a DROP first_trade_id;")

    ini_mes = int(dt.datetime.fromisoformat(mes + "-01").replace(tzinfo=dt.timezone.utc).timestamp())
    b = con.execute(f"""SELECT t//1000 s, arg_min(p, id) o, max(p) h, min(p) l, arg_max(p, id) c,
            sum(q) v, coalesce(sum(q) FILTER (WHERE buy), 0) vb, count(*) n_agg, sum(ntr) n_tr,
            min(t%1000) ms_first, max(t%1000) ms_last
        FROM a GROUP BY 1 ORDER BY 1""").pl()
    enc = b.select(
        dt=pl.col("s").diff().fill_null(pl.col("s").first() - ini_mes).cast(pl.Int32),
        do=(pl.col("o") - pl.col("c").shift(1)).fill_null(pl.col("o").first()).cast(pl.Int32),
        dh=(pl.col("h") - pl.col("o")).cast(pl.Int32), dl=(pl.col("o") - pl.col("l")).cast(pl.Int32),
        dc=(pl.col("c") - pl.col("o")).cast(pl.Int32),
        v=pl.col("v").cast(pl.Int32), vb=pl.col("vb").cast(pl.Int32),
        n_agg=pl.col("n_agg").cast(pl.Int32), ntx=(pl.col("n_tr") - pl.col("n_agg")).cast(pl.Int32),
        ms_first=pl.col("ms_first").cast(pl.Int16), ms_last=pl.col("ms_last").cast(pl.Int16))
    # verificación de que la codificación es sin pérdida antes de escribir
    assert b["v"].max() <= 2**31 - 1 and (b["h"] - b["l"]).max() <= 2**31 - 1, "desborde"
    (PROC / "bars_1s").mkdir(parents=True, exist_ok=True)
    enc.write_parquet(PROC / "bars_1s" / f"{mes}.parquet", compression="zstd", compression_level=19, statistics=False)
    integ["bars_1s"] = {"filas": b.height}

    # órdenes a mercado reconstruidas: aggTrades con el mismo ms y el mismo lado
    o = con.execute(f"""SELECT t, buy, sum(q) q, min(p) pmin, max(p) pmax, count(*) n_agg,
            FROM a GROUP BY t, buy
        HAVING sum(p*q) >= {PISO_ORDEN_USD * ESCALA_P * ESCALA_Q} ORDER BY t""").pl()
    o = o.select(ts=pl.col("t"), buy=pl.col("buy"), q=pl.col("q").cast(pl.Int32),
                 pmin=pl.col("pmin").cast(pl.Int32), dp=(pl.col("pmax") - pl.col("pmin")).cast(pl.Int32),
                 n_agg=pl.col("n_agg").cast(pl.Int32))
    (PROC / "ordenes_grandes").mkdir(parents=True, exist_ok=True)
    o.write_parquet(PROC / "ordenes_grandes" / f"{mes}.parquet", compression="zstd", compression_level=19)
    integ["ordenes_grandes"] = {"filas": o.height, "piso_usd": PISO_ORDEN_USD}

    # velas 1m reconstruidas vs klines oficiales
    m = con.execute("""SELECT (t//60000)*60000 open_time, arg_min(p, id) o, max(p) h, min(p) l, arg_max(p, id) c,
            sum(q) v, sum(q) FILTER (WHERE buy) vb, sum(ntr) n FROM a GROUP BY 1""").pl()
    con.close()
    k = klines.select("open_time",
                      ko=(pl.col("open") * ESCALA_P).round().cast(pl.Int64), kh=(pl.col("high") * ESCALA_P).round().cast(pl.Int64),
                      kl=(pl.col("low") * ESCALA_P).round().cast(pl.Int64), kc=(pl.col("close") * ESCALA_P).round().cast(pl.Int64),
                      kv=(pl.col("volume") * ESCALA_Q).round().cast(pl.Int64),
                      kvb=(pl.col("taker_buy_volume") * ESCALA_Q).round().cast(pl.Int64), kn=pl.col("count"))
    j = k.join(m, on="open_time", how="full", coalesce=True)
    solo_k = j.filter(pl.col("o").is_null() & (pl.col("kv") > 0))
    solo_a = j.filter(pl.col("ko").is_null())
    ambos = j.filter(pl.col("o").is_not_null() & pl.col("ko").is_not_null())
    difs = ambos.filter((pl.col("o") != pl.col("ko")) | (pl.col("h") != pl.col("kh")) | (pl.col("l") != pl.col("kl"))
                        | (pl.col("c") != pl.col("kc"))
                        | ((pl.col("v") - pl.col("kv")).abs() > 1e-6 * pl.col("kv").cast(pl.Float64)))
    # Las diferencias vienen casi siempre en pares de minutos contiguos (trades en el borde del minuto que
    # aggTrades asigna al minuto anterior y la kline al siguiente). Se agrupan las rachas de minutos
    # consecutivos con diferencia de volumen; si la racha suma 0 es "corrimiento de borde", si no es residual.
    r = (ambos.sort("open_time")
         .with_columns(dv=pl.col("v") - pl.col("kv"), dn=pl.col("n") - pl.col("kn"))
         .filter((pl.col("dv") != 0) | (pl.col("dn") != 0))
         .with_columns(racha=(pl.col("open_time").diff().fill_null(0) != 60_000).cum_sum())
         .group_by("racha", maintain_order=True)
         .agg(desde=pl.col("open_time").first(), minutos=pl.len(), dv=pl.col("dv").sum(), dn=pl.col("dn").sum()))
    resid = r.filter((pl.col("dv") != 0) | (pl.col("dn") != 0))
    integ["reconstruccion_1m"] = {
        "minutos_comparados": ambos.height, "minutos_solo_klines_con_volumen": solo_k.height,
        "minutos_solo_aggtrades": solo_a.height,
        "minutos_high_low_close_distinto": ambos.filter((pl.col("h") != pl.col("kh")) | (pl.col("l") != pl.col("kl"))
                                                        | (pl.col("c") != pl.col("kc"))).height,
        "minutos_open_distinto": ambos.filter(pl.col("o") != pl.col("ko")).height,
        "minutos_volumen_distinto": difs.filter(pl.col("v") != pl.col("kv")).height,
        "minutos_count_distinto": ambos.filter(pl.col("n") != pl.col("kn")).height,
        "rachas_corrimiento_borde": r.height - resid.height,
        "rachas_residuales": resid.height,
        "residual_total_btc": float(resid["dv"].sum() or 0) / ESCALA_Q,
        "residual_total_trades": int(resid["dn"].sum() or 0),
        "residuales": [{"desde_utc": dt.datetime.fromtimestamp(x["desde"] / 1000, dt.timezone.utc).isoformat(),
                        "minutos": x["minutos"], "dv_btc": float(x["dv"]) / ESCALA_Q, "dn": int(x["dn"])}
                       for x in resid.sort(pl.col("dv").abs(), descending=True).head(20).to_dicts()],
        "volumen_total_klines_btc": float(k["kv"].sum()) / ESCALA_Q,
        "volumen_total_aggtrades_btc": float(m["v"].sum()) / ESCALA_Q,
    }
    return integ


# ───────────────────────────── metrics / liquidaciones ─────────────────────────────

def proc_metrics(mes: str) -> dict:
    csvs = [csv_de_zip(z) for z in zips_del_mes("metrics", "", mes, solo_daily=True)]
    df = pl.concat([pl.read_csv(c, infer_schema_length=0) for c in csvs])
    for c in csvs:
        c.unlink()
    df = df.select(
        create_time=pl.col("create_time").str.to_datetime("%Y-%m-%d %H:%M:%S", time_zone="UTC").dt.epoch("ms"),
        **{c: pl.col(c).cast(pl.Float64, strict=False) for c in df.columns if c not in ("create_time", "symbol")},
    ).sort("create_time")
    (PROC / "metrics_5m").mkdir(parents=True, exist_ok=True)
    df.write_parquet(PROC / "metrics_5m" / f"{mes}.parquet", compression="zstd", compression_level=19)
    t = df["create_time"]
    return {"filas": df.height, "duplicados": df.height - t.n_unique(),
            "saltos_distintos_de_5m": int((t.diff().drop_nulls() != 300_000).sum()),
            "nulos_oi": int(df["sum_open_interest"].null_count())}


def proc_liq_coinm(mes: str) -> dict:
    csvs = []
    for dia in dias_del_mes(mes):
        ruta = f"data/futures/cm/daily/liquidationSnapshot/BTCUSD_PERP/BTCUSD_PERP-liquidationSnapshot-{dia}.zip"
        if existe(ruta) is False:
            continue
        csvs.append(csv_de_zip(bajar(ruta, RAW / Path(ruta).name)))
    if not csvs:
        return {"dias": 0}
    df = pl.concat([pl.read_csv(c, infer_schema_length=0) for c in csvs]).select(
        time=pl.col("time").cast(pl.Int64), side="side", order_type="order_type", time_in_force="time_in_force",
        original_quantity=pl.col("original_quantity").cast(pl.Float64), price=pl.col("price").cast(pl.Float64),
        average_price=pl.col("average_price").cast(pl.Float64), order_status="order_status",
        last_fill_quantity=pl.col("last_fill_quantity").cast(pl.Float64),
        accumulated_fill_quantity=pl.col("accumulated_fill_quantity").cast(pl.Float64)).sort("time")
    for c in csvs:
        c.unlink()
    (PROC / "liq_coinm").mkdir(parents=True, exist_ok=True)
    df.write_parquet(PROC / "liq_coinm" / f"{mes}.parquet", compression="zstd", compression_level=19)
    return {"dias": len(csvs), "filas": df.height, "filas_duplicadas_exactas": df.height - df.unique().height}


# ───────────────────────────── orquestación ─────────────────────────────

def procesar_mes(mes: str, solo: set[str]) -> None:
    INTEG.mkdir(parents=True, exist_ok=True)
    f_integ = INTEG / f"{mes}.json"
    integ = json.loads(f_integ.read_text()) if f_integ.exists() else {}
    t0 = time.time()
    klines = None
    if "klines" in solo or "aggtrades" in solo:
        klines = proc_velas(mes, "klines", "klines_1m", completas=True)
        integ["klines_1m"] = huecos_1m(klines, mes)
    for ds, carpeta in [("markPriceKlines", "mark_1m"), ("indexPriceKlines", "index_1m"),
                        ("premiumIndexKlines", "premium_1m")]:
        if carpeta.split("_")[0] in solo:
            df = proc_velas(mes, ds, carpeta, completas=False)
            integ[carpeta] = huecos_1m(df, mes)
            if carpeta == "mark_1m" and klines is not None:
                # desacoples mark vs last: |close_mark − close_last| / close_last
                j = df.join(klines.select("open_time", last="close"), on="open_time")
                d = ((j["close"] - j["last"]).abs() / j["last"])
                integ["mark_1m"]["desacople"] = {"max_pct": round(float(d.max()) * 100, 4),
                                                 "min_>0.1%": int((d > 0.001).sum()), "min_>0.5%": int((d > 0.005).sum())}
    if "metrics" in solo:
        integ["metrics_5m"] = proc_metrics(mes)
    if "liq" in solo and "2023-06" <= mes <= "2024-10":
        integ["liq_coinm"] = proc_liq_coinm(mes)
    if "aggtrades" in solo:
        previo = INTEG / f"{meses_ant(mes)}.json"
        id_previo = json.loads(previo.read_text()).get("ids", {}).get("max_id") if previo.exists() else None
        integ.update(proc_aggtrades(mes, klines, id_previo))
    integ["segundos_proceso"] = round(time.time() - t0, 1)
    f_integ.write_text(json.dumps(integ, indent=1, ensure_ascii=False, default=str))
    print(f"{mes} ok ({integ['segundos_proceso']} s)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("desde")
    ap.add_argument("hasta")
    ap.add_argument("--solo", default="klines,mark,index,premium,metrics,liq,aggtrades")
    args = ap.parse_args()
    solo = set(args.solo.split(","))
    RAW.mkdir(parents=True, exist_ok=True)
    (PROC / "LEEME_bars_1s.txt").parent.mkdir(parents=True, exist_ok=True)
    (PROC / "LEEME_bars_1s.txt").write_text(ESQUEMA_1S)
    for mes in meses(args.desde, args.hasta):
        procesar_mes(mes, solo)
    shutil.rmtree(RAW, ignore_errors=True)


if __name__ == "__main__":
    main()
