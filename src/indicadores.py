"""F1 · Réplica de los indicadores de Juan (spec/*.pine) sobre velas de 1m.

Cada valor está "al cierre" de la vela de 1m con open_time t, o sea con toda la información hasta t+59,999 s.
Nada mira hacia adelante.

Dos semánticas para lo que en Pine sale de request.security(..., lookahead_off) contra un TF mayor:
  *_vivo : lo que Juan ve en tiempo real → la vela del TF mayor EN FORMACIÓN, armada con las velas de 1m cerradas.
  *_hist : lo que muestra TradingView en el historial (ventana de datos, Bar Replay) → el valor de la última
           vela del TF mayor YA CERRADA. En la última vela de 1m de cada vela mayor, las dos coinciden.
Las etiquetas DO/WO/MO/YO/PWH/PWL/PQH/PQL usan lookahead_on sobre valores ya conocidos: una sola versión.

Referencias al .pine entre corchetes, p. ej. [XO §2], [ASH ashCalc].
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl
from numba import njit

from datos import leer_velas_1m

MS_MIN = 60_000
MS_DIA = 86_400_000
LUNES_0 = 345_600_000  # 1970-01-05 00:00 UTC fue lunes: las semanas de TradingView (cripto) arrancan lunes 00:00 UTC

# Parámetros confirmados por Juan (CLAUDE.md §1)
ASH_LEN, ASH_SMOOTH = 16, 4
XO_RAPIDA, XO_LENTA = 11, 25
RVOL_LEN = 20
PERFIL_FILAS, PERFIL_VA = 24, 70.0
ROLL_MS = 24 * 3_600_000
ATR_LEN = 14


# ═════════════════════════════ primitivas de Pine ═════════════════════════════

@njit(cache=True)
def sma(x, n):
    """ta.sma: na mientras la ventana tenga algún na."""
    out = np.full(x.size, np.nan)
    s, cnt = 0.0, 0
    for i in range(x.size):
        if np.isnan(x[i]):
            cnt, s = 0, 0.0
            continue
        s += x[i]
        cnt += 1
        if cnt > n:
            s -= x[i - n]
        if cnt >= n:
            out[i] = s / n
    return out


@njit(cache=True)
def _ema_alpha(x, n, a):
    """sum := na(sum[1]) ? ta.sma(src, n) : a*src + (1-a)*nz(sum[1])  — ta.ema (a=2/(n+1)) y ta.rma (a=1/n)."""
    out = np.full(x.size, np.nan)
    semilla = sma(x, n)
    prev = np.nan
    for i in range(x.size):
        if np.isnan(prev):
            prev = semilla[i]
        else:
            prev = a * x[i] + (1.0 - a) * prev
        out[i] = prev
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return _ema_alpha(x, n, 2.0 / (n + 1.0))


def rma(x: np.ndarray, n: int) -> np.ndarray:
    return _ema_alpha(x, n, 1.0 / n)


def ash_rsi(c: np.ndarray, n: int = ASH_LEN, sm: int = ASH_SMOOTH) -> tuple[np.ndarray, np.ndarray]:
    """[ASH ashCalc] modo RSI con ma EMA: Bulls0 = 0.5(|Δ|+Δ), Bears0 = 0.5(|Δ|−Δ), Δ = close − close[1]."""
    d = np.full(c.size, np.nan)
    d[1:] = c[1:] - c[:-1]
    bulls = 0.5 * (np.abs(d) + d)
    bears = 0.5 * (np.abs(d) - d)
    return ema(ema(bulls, n), sm), ema(ema(bears, n), sm)


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = ATR_LEN) -> np.ndarray:
    """ta.atr: rma del true range; la primera vela usa high − low."""
    tr = h - l
    pc = c[:-1]
    tr[1:] = np.maximum(np.maximum(h[1:] - l[1:], np.abs(h[1:] - pc)), np.abs(l[1:] - pc))
    return rma(tr, n)


# ═════════════════════════════ VWAP anclado nativo [XO §7 f_vwap] ═════════════════════════════

@njit(cache=True)
def vwap_anclado(src, vol, reset):
    """Acumula (p − c) con c = primer precio del período. Devuelve (vwap, σ)."""
    n = src.size
    vw = np.full(n, np.nan)
    sd = np.full(n, np.nan)
    c = np.nan
    s1 = sv = s2 = 0.0
    for i in range(n):
        if reset[i] or np.isnan(c):
            c = src[i]
        d = src[i] - c
        v = 0.0 if np.isnan(vol[i]) else vol[i]
        if reset[i]:
            s1, sv, s2 = d * v, v, v * d * d
        else:
            s1 += d * v
            sv += v
            s2 += v * d * d
        m = s1 / sv if sv > 0 else 0.0
        vr = s2 / sv - m * m if sv > 0 else 0.0
        vw[i] = c + m
        sd[i] = np.sqrt(max(vr, 0.0))
    return vw, sd


# ═════════════════════════════ perfil diario y rolling 24h [XO §10] ═════════════════════════════

@njit(cache=True)
def perfil_diario(h, l, v, s, ini_dia, filas, va):
    """Para cada vela i: perfil de las velas de 1m desde el inicio del día UTC hasta i (inclusive).
    Devuelve dVWAP, dPOC, dVAH, dVAL."""
    n = h.size
    dvw = np.full(n, np.nan)
    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    val = np.full(n, np.nan)
    hist = np.zeros(filas)
    for i in range(n):
        a = ini_dia[i]
        sv = ssv = 0.0
        lo, hi = 1e300, -1e300
        for j in range(a, i + 1):
            sv += v[j]
            ssv += s[j] * v[j]
            lo = min(lo, l[j])
            hi = max(hi, h[j])
        dvw[i] = ssv / sv if sv > 0 else np.nan
        st = (hi - lo) / filas
        if st <= 0 or sv <= 0:
            poc[i], vah[i], val[i] = hi, hi, lo
            continue
        hist[:] = 0.0
        for j in range(a, i + 1):
            if v[j] > 0:
                r0 = min(filas - 1, max(0, int(np.floor((l[j] - lo) / st))))
                r1 = min(filas - 1, max(0, int(np.floor((h[j] - lo) / st))))
                if h[j] <= l[j]:
                    hist[r0] += v[j]
                else:
                    for r in range(r0, r1 + 1):
                        bot = lo + r * st
                        ov = min(h[j], bot + st) - max(l[j], bot)
                        if ov > 0:
                            hist[r] += v[j] * ov / (h[j] - l[j])
        # array.indexof(hist, array.max(hist)): primera fila con el máximo
        p = 0
        for r in range(filas):
            if hist[r] > hist[p]:
                p = r
        tgt = hist.sum() * va / 100.0
        acc = hist[p]
        up = dn = p
        while acc < tgt and (up < filas - 1 or dn > 0):
            vu = hist[up + 1] if up < filas - 1 else -1.0
            vd = hist[dn - 1] if dn > 0 else -1.0
            if vu >= vd:
                up += 1
                acc += vu
            else:
                dn -= 1
                acc += vd
        poc[i] = lo + (p + 0.5) * st
        vah[i] = lo + (up + 1) * st
        val[i] = lo + dn * st
    return dvw, poc, vah, val


@njit(cache=True)
def rolling_24h(t, s, v, ventana_ms, k):
    """rVWAP ± k·σ sobre las velas de 1m con open_time > t_i − ventana (incluye la vela i)."""
    n = t.size
    m_out = np.full(n, np.nan)
    sd_out = np.full(n, np.nan)
    a = 0
    for i in range(n):
        corte = t[i] - ventana_ms
        while t[a] <= corte:
            a += 1
        w = wx = 0.0
        for j in range(a, i + 1):
            w += v[j]
            wx += s[j] * v[j]
        if w > 0:
            m = wx / w
            w2 = 0.0
            for j in range(a, i + 1):
                d = s[j] - m
                w2 += v[j] * d * d
            m_out[i] = m
            sd_out[i] = np.sqrt(max(w2 / w, 0.0))
    return m_out, sd_out * k


# ═════════════════════════════ VWAP de TF mayor vía request.security [XO §7 f_anchVwap] ═════════════════════════════

@njit(cache=True)
def vwap_tf_mayor(balde, periodo, h, l, c, v, hlc3):
    """Simula request.security(TF, f_anchVwap(src, período), lookahead_off) en un gráfico de 1m.
    balde[i]: id de la vela del TF de cálculo (60m, D) que contiene la vela de 1m i.
    periodo[i]: id del período de anclaje (semana, mes, trimestre, año) de esa vela.
    Devuelve, en versión vivo (vela mayor en formación): vwap, σ, vwap previo, σ previo."""
    n = h.size
    vw = np.full(n, np.nan)
    sd = np.full(n, np.nan)
    pvw = np.full(n, np.nan)
    psd = np.full(n, np.nan)
    s0 = s1 = s2 = 0.0          # sumas de las velas mayores cerradas del período en curso (centradas en c0)
    c0 = np.nan
    fin_vw = fin_sd = np.nan    # valor al cierre de la última vela mayor cerrada
    prev_vw = prev_sd = np.nan  # valor final del período anterior
    bh = bl = bv = 0.0
    for i in range(n):
        nueva = i == 0 or balde[i] != balde[i - 1]
        if nueva:
            if i > 0:
                # cerrar la vela mayor anterior: sumarla al período
                sb = (bh + bl + c[i - 1]) / 3.0 if hlc3 else (bh + bl) / 2.0
                if np.isnan(c0):
                    c0 = sb
                d = sb - c0
                s0 += bv
                s1 += bv * d
                s2 += bv * d * d
                m = s1 / s0 if s0 > 0 else 0.0
                fin_vw = c0 + m
                fin_sd = np.sqrt(max(s2 / s0 - m * m, 0.0)) if s0 > 0 else 0.0
            if i == 0 or periodo[i] != periodo[i - 1]:
                if i > 0:
                    prev_vw, prev_sd = fin_vw, fin_sd
                s0 = s1 = s2 = 0.0
                c0 = np.nan
            bh, bl, bv = h[i], l[i], v[i]
        else:
            bh = max(bh, h[i])
            bl = min(bl, l[i])
            bv += v[i]
        sb = (bh + bl + c[i]) / 3.0 if hlc3 else (bh + bl) / 2.0
        cc = sb if np.isnan(c0) else c0
        d = sb - cc
        t0, t1, t2 = s0 + bv, s1 + bv * d, s2 + bv * d * d
        m = t1 / t0 if t0 > 0 else 0.0
        vw[i] = cc + m
        sd[i] = np.sqrt(max(t2 / t0 - m * m, 0.0)) if t0 > 0 else 0.0
        pvw[i], psd[i] = prev_vw, prev_sd
    return vw, sd, pvw, psd


@njit(cache=True)
def rolling_dias(dia, h, l, c, v, dias):
    """[XO §9b] rVWAP de N días sobre velas DIARIAS con fuente hlc3, ventana time ≥ time − N·1D (inclusiva):
    la vela diaria en curso + las N anteriores. Versión vivo (diaria en formación). Devuelve (valor, ventana_llena)."""
    n = h.size
    out = np.full(n, np.nan)
    llena = np.zeros(n, dtype=np.bool_)
    # velas diarias cerradas: hlc3·v y v
    nd = dia[n - 1] - dia[0] + 1
    pv_d = np.zeros(nd)
    v_d = np.zeros(nd)
    bh = bl = bv = 0.0
    for i in range(n):
        k = dia[i] - dia[0]
        if i == 0 or dia[i] != dia[i - 1]:
            bh, bl, bv = h[i], l[i], v[i]
        else:
            bh = max(bh, h[i])
            bl = min(bl, l[i])
            bv += v[i]
        src = (bh + bl + c[i]) / 3.0
        spv = src * bv
        sv = bv
        for j in range(max(0, k - dias), k):
            spv += pv_d[j]
            sv += v_d[j]
        out[i] = spv / sv if sv > 0 else np.nan
        llena[i] = k - dias >= 0
        if i == n - 1 or dia[i + 1] != dia[i]:
            pv_d[k] = src * bv  # la vela diaria cerró: queda fija para los días siguientes
            v_d[k] = bv
    return out, llena


def a_hist(vivo: np.ndarray, balde: np.ndarray) -> np.ndarray:
    """Versión historial de request.security(lookahead_off): en cada vela de 1m, el valor de la última vela mayor
    CERRADA. Es el valor vivo de la última vela de 1m de cada balde, arrastrado hasta que cierra el siguiente."""
    n = vivo.size
    cierra = np.ones(n, dtype=bool)
    cierra[:-1] = balde[1:] != balde[:-1]
    out = np.full(n, np.nan)
    out[cierra] = vivo[cierra]
    # arrastrar hacia adelante
    idx = np.where(cierra, np.arange(n), -1)
    idx = np.maximum.accumulate(idx)
    ok = idx >= 0
    out[ok] = vivo[idx[ok]]
    return out


# ═════════════════════════════ TF de 5m [ASH cuadro MTF] ═════════════════════════════

@njit(cache=True)
def ema_paso(prev, x, n):
    return 2.0 / (n + 1.0) * x + (1.0 - 2.0 / (n + 1.0)) * prev


def cinco_min(t: np.ndarray, c: np.ndarray) -> dict[str, np.ndarray]:
    """ASH y EMAs de 5m. Vivo: estado al cierre de la última vela de 5m cerrada + una actualización con la vela de
    5m en formación (close = close de la última 1m). Cerrada: valores de la última vela de 5m completa."""
    b5 = t // (5 * MS_MIN)
    fin = np.ones(t.size, dtype=bool)
    fin[:-1] = b5[1:] != b5[:-1]
    c5 = c[fin]  # closes de las velas de 5m (la última puede estar incompleta: se descarta abajo si hace falta)
    e11, e25 = ema(c5, XO_RAPIDA), ema(c5, XO_LENTA)
    d = np.full(c5.size, np.nan)
    d[1:] = c5[1:] - c5[:-1]
    bu, be = 0.5 * (np.abs(d) + d), 0.5 * (np.abs(d) - d)
    abu, abe = ema(bu, ASH_LEN), ema(be, ASH_LEN)
    sbu, sbe = ema(abu, ASH_SMOOTH), ema(abe, ASH_SMOOTH)
    # índice de la vela de 5m (en el arreglo c5) a la que pertenece cada 1m, y de la anterior cerrada
    k = np.cumsum(fin) - fin  # nº de velas de 5m cerradas antes de la vela de 1m i = índice de su vela de 5m
    kp = k - 1                # última vela de 5m cerrada antes de la que está en formación
    ok = kp >= 0
    out = {n: np.full(t.size, np.nan) for n in ("ema11_5m_vivo", "ema25_5m_vivo", "ash_bulls_5m_vivo", "ash_bears_5m_vivo")}
    kpi = np.where(ok, kp, 0)
    cprev = c5[kpi]
    dv = c - cprev
    buv, bev = 0.5 * (np.abs(dv) + dv), 0.5 * (np.abs(dv) - dv)
    a11, a25 = 2 / (XO_RAPIDA + 1), 2 / (XO_LENTA + 1)
    aa, asm = 2 / (ASH_LEN + 1), 2 / (ASH_SMOOTH + 1)
    out["ema11_5m_vivo"] = np.where(ok, a11 * c + (1 - a11) * e11[kpi], np.nan)
    out["ema25_5m_vivo"] = np.where(ok, a25 * c + (1 - a25) * e25[kpi], np.nan)
    abu_v = aa * buv + (1 - aa) * abu[kpi]
    abe_v = aa * bev + (1 - aa) * abe[kpi]
    out["ash_bulls_5m_vivo"] = np.where(ok, asm * abu_v + (1 - asm) * sbu[kpi], np.nan)
    out["ash_bears_5m_vivo"] = np.where(ok, asm * abe_v + (1 - asm) * sbe[kpi], np.nan)
    # versión cerrada: la vela de 5m que termina en esta 1m ya vale; si no, la anterior
    kc = np.where(fin, k, kp)
    okc = kc >= 0
    kci = np.where(okc, kc, 0)
    out["ema11_5m_cerr"] = np.where(okc, e11[kci], np.nan)
    out["ema25_5m_cerr"] = np.where(okc, e25[kci], np.nan)
    out["ash_bulls_5m_cerr"] = np.where(okc, sbu[kci], np.nan)
    out["ash_bears_5m_cerr"] = np.where(okc, sbe[kci], np.nan)
    return out


# ═════════════════════════════ niveles OHLC [XO §11] ═════════════════════════════

def niveles_ohlc(df: pl.DataFrame) -> pl.DataFrame:
    """DO WO MO YO (open del período en curso), PWH/PWL (semana previa), PQH/PQL (trimestre previo),
    MNDAY-H/L (vivo e historial)."""
    ts = pl.from_epoch("open_time", time_unit="ms")
    d = df.select("open_time", "open", "high", "low").with_columns(
        dia=pl.col("open_time") // MS_DIA,
        sem=(pl.col("open_time") - LUNES_0) // (7 * MS_DIA),
        mes=ts.dt.year() * 12 + ts.dt.month() - 1,
        trim=ts.dt.year() * 4 + (ts.dt.month() - 1) // 3,
        anio=ts.dt.year(),
        lunes=ts.dt.weekday() == 1,
    )
    for p, nombre in [("dia", "DO"), ("sem", "WO"), ("mes", "MO"), ("anio", "YO")]:
        d = d.with_columns(pl.col("open").first().over(p).alias(nombre))
    for p, (nh, nl) in [("sem", ("PWH", "PWL")), ("trim", ("PQH", "PQL"))]:
        agg = d.group_by(p).agg(hh=pl.col("high").max(), ll=pl.col("low").min()).with_columns(pl.col(p) + 1)
        d = d.join(agg.rename({"hh": nh, "ll": nl}), on=p, how="left")
    # MNDAY vivo: el lunes, high/low acumulados del lunes hasta esta vela; martes a domingo, el lunes completo
    d = d.with_columns(
        mh_run=pl.col("high").cum_max().over("dia"), ml_run=pl.col("low").cum_min().over("dia"))
    lun = d.filter(pl.col("lunes")).group_by("sem").agg(mh=pl.col("high").max(), ml=pl.col("low").min())
    d = d.join(lun, on="sem", how="left").join(
        lun.with_columns(pl.col("sem") + 1).rename({"mh": "mh_prev", "ml": "ml_prev"}), on="sem", how="left")
    ultimo_min = (pl.col("open_time") % MS_DIA) == MS_DIA - MS_MIN
    d = d.with_columns(
        MNDAY_H_vivo=pl.when(pl.col("lunes")).then(pl.col("mh_run")).otherwise(pl.col("mh")),
        MNDAY_L_vivo=pl.when(pl.col("lunes")).then(pl.col("ml_run")).otherwise(pl.col("ml")),
        # historial: durante el lunes la vela diaria cerrada es el domingo → queda el lunes de la semana pasada
        MNDAY_H_hist=pl.when(pl.col("lunes") & ~ultimo_min).then(pl.col("mh_prev")).otherwise(pl.col("mh")),
        MNDAY_L_hist=pl.when(pl.col("lunes") & ~ultimo_min).then(pl.col("ml_prev")).otherwise(pl.col("ml")),
    )
    return d.sort("open_time").select("DO", "WO", "MO", "YO", "PWH", "PWL", "PQH", "PQL",
                                      "MNDAY_H_vivo", "MNDAY_L_vivo", "MNDAY_H_hist", "MNDAY_L_hist")


# ═════════════════════════════ armado completo ═════════════════════════════

def calcular(desde: str | None = None, hasta: str | None = None) -> pl.DataFrame:
    """Todos los indicadores por vela de 1m. Se calcula siempre desde el inicio de los datos (2022-01, calentamiento)
    y se recorta a [desde, hasta] (AAAA-MM)."""
    k = leer_velas_1m().sort("open_time")
    t = k["open_time"].to_numpy()
    o, h, l, c = (k[x].to_numpy() for x in ("open", "high", "low", "close"))
    v = k["volume"].to_numpy()
    hl2 = (h + l) / 2.0
    ts = pl.from_epoch(k["open_time"], time_unit="ms")
    dia = (t // MS_DIA).astype(np.int64)
    sem = ((t - LUNES_0) // (7 * MS_DIA)).astype(np.int64)
    mes = (ts.dt.year() * 12 + ts.dt.month() - 1).to_numpy().astype(np.int64)
    trim = (ts.dt.year() * 4 + (ts.dt.month() - 1) // 3).to_numpy().astype(np.int64)
    anio = ts.dt.year().to_numpy().astype(np.int64)
    hora = (t // 3_600_000).astype(np.int64)

    col: dict[str, np.ndarray] = {}
    col["ema11"], col["ema25"] = ema(c, XO_RAPIDA), ema(c, XO_LENTA)
    col["ash_bulls"], col["ash_bears"] = ash_rsi(c)
    col["rvol"] = v / sma(v, RVOL_LEN)
    col["atr14"] = atr(h.copy(), l, c)

    reset_d = np.r_[True, dia[1:] != dia[:-1]]
    reset_w = np.r_[True, sem[1:] != sem[:-1]]
    for nom, rs in [("vwap_d", reset_d), ("vwap_w", reset_w)]:
        vw, sd = vwap_anclado(hl2, v, rs)
        col[nom] = vw
        for kk in (1, 2):
            col[f"{nom}_p{kk}"] = vw + kk * sd
            col[f"{nom}_m{kk}"] = vw - kk * sd

    ini_dia = np.zeros(t.size, dtype=np.int64)
    idx = np.where(reset_d, np.arange(t.size), 0)
    ini_dia[:] = np.maximum.accumulate(idx)
    col["dVWAP"], col["dPOC"], col["dVAH"], col["dVAL"] = perfil_diario(h, l, v, hl2, ini_dia, PERFIL_FILAS, PERFIL_VA)
    rm, rsd = rolling_24h(t, hl2, v, ROLL_MS, 1.0)
    col["rVWAP"], col["rVAH"], col["rVAL"] = rm, rm + rsd, rm - rsd

    # VWAP de TF mayor [XO §7]: pw y m/pm en 60m; pq e y en diario. Todos con hl2.
    for nom, balde, periodo in [("w", hora, sem), ("m", hora, mes), ("q", dia, trim), ("y", dia, anio)]:
        vw, sd, pvw, psd = vwap_tf_mayor(balde, periodo, h, l, c, v, False)
        for suf, arr in [("VWAP", vw), ("VAH", vw + sd), ("VAL", vw - sd),
                         ("pVWAP", pvw), ("pVAH", pvw + psd), ("pVAL", pvw - psd)]:
            base = f"p{nom}{suf[1:]}" if suf.startswith("p") else f"{nom}{suf}"
            col[f"{base}_vivo"] = arr
            col[f"{base}_hist"] = a_hist(arr, balde)
    # rolling multi-día [XO §9b], velas diarias hlc3
    for nd in (7, 30, 90, 365):
        r, llena = rolling_dias(dia, h, l, c, v, nd)
        col[f"r{nd}D_vivo"] = r
        col[f"r{nd}D_hist"] = a_hist(r, dia)
        col[f"r{nd}D_llena"] = llena
    col.update(cinco_min(t, c))

    out = pl.DataFrame({"open_time": t, "open": o, "high": h, "low": l, "close": c, "volume": v,
                        "reparada": k["reparada"].to_numpy(), **col})
    out = pl.concat([out, niveles_ohlc(k)], how="horizontal")
    # descartar columnas que no son etiquetas del indicador (w y q en curso, y previo)
    out = out.drop([x for x in out.columns if x.startswith(("wVWAP", "wVAH", "wVAL", "qVWAP", "qVAH", "qVAL",
                                                             "pyVWAP", "pyVAH", "pyVAL"))])
    if desde or hasta:
        m = pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m")
        out = out.filter((m >= (desde or "0000")) & (m <= (hasta or "9999")))
    return out


CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"


def cargar(desde: str | None = None, hasta: str | None = None, recalcular: bool = False) -> pl.DataFrame:
    """Indicadores desde la caché (data/cache/indicadores_1m.parquet, no versionada); la arma si no existe."""
    f = CACHE / "indicadores_1m.parquet"
    if recalcular or not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        calcular().write_parquet(f, compression="zstd")
    df = pl.read_parquet(f)
    if desde or hasta:
        m = pl.from_epoch("open_time", time_unit="ms").dt.strftime("%Y-%m")
        df = df.filter((m >= (desde or "0000")) & (m <= (hasta or "9999")))
    return df


if __name__ == "__main__":
    import time as _t
    t0 = _t.time()
    df = cargar(recalcular=True)
    print(df.shape, f"{_t.time() - t0:.0f} s")
