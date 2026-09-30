"""Tests de consistencia interna de src/indicadores.py contra implementaciones de referencia escritas aparte
(Python directo, sin numba, sin reutilizar nada del módulo). Los tests de paridad con TradingView van en
test_paridad_tv.py cuando Juan complete la tabla de F1.

Uso: python -m pytest tests/ -q   (o python tests/test_indicadores.py)
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import indicadores as ind  # noqa: E402
from datos import leer_velas_1m  # noqa: E402

MS_MIN, MS_DIA = 60_000, 86_400_000
R = random.Random(11)
DF = ind.cargar("2023-01", "2026-09")
K = leer_velas_1m("2022-01", "2026-09").sort("open_time")
T = K["open_time"].to_list()
POS = {t: i for i, t in enumerate(T)}
H, L, C, V = (K[x].to_list() for x in ("high", "low", "close", "volume"))
FILAS = {r["open_time"]: r for r in DF.sample(400, seed=3).iter_rows(named=True)}
MUESTRA = list(FILAS.values())


def cerca(a, b, tol=1e-6):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b)))


def ref_perfil(i0, i1, filas=24, va=70.0):
    hs, ls, vs = H[i0:i1 + 1], L[i0:i1 + 1], V[i0:i1 + 1]
    lo, hi = min(ls), max(hs)
    st = (hi - lo) / filas
    hist = [0.0] * filas
    for h, l, v in zip(hs, ls, vs):
        if v <= 0:
            continue
        if h <= l:
            hist[min(filas - 1, max(0, math.floor((l - lo) / st)))] += v
            continue
        for r in range(filas):
            bot = lo + r * st
            ov = min(h, bot + st) - max(l, bot)
            if ov > 0:
                hist[r] += v * ov / (h - l)
    p = hist.index(max(hist))
    acc, up, dn = hist[p], p, p
    while acc < sum(hist) * va / 100 and (up < filas - 1 or dn > 0):
        vu = hist[up + 1] if up < filas - 1 else -1
        vd = hist[dn - 1] if dn > 0 else -1
        if vu >= vd:
            up += 1
            acc += vu
        else:
            dn -= 1
            acc += vd
    return lo + (p + 0.5) * st, lo + (up + 1) * st, lo + dn * st


def ref_vwap(idx, src):
    sv = sum(V[j] for j in idx)
    m = sum(src(j) * V[j] for j in idx) / sv
    var = sum(V[j] * (src(j) - m) ** 2 for j in idx) / sv
    return m, math.sqrt(var)


def test_perfil_y_dvwap():
    for r in MUESTRA[:60]:
        i = POS[r["open_time"]]
        i0 = POS[r["open_time"] // MS_DIA * MS_DIA]
        poc, vah, val = ref_perfil(i0, i)
        assert cerca(r["dPOC"], poc) and cerca(r["dVAH"], vah) and cerca(r["dVAL"], val), r["open_time"]
        m, _ = ref_vwap(range(i0, i + 1), lambda j: (H[j] + L[j]) / 2)
        assert cerca(r["dVWAP"], m)
        # el VWAP de sesión (curva) y dVWAP son el mismo número en 1m [XO §10]
        assert cerca(r["vwap_d"], m, 1e-9)


def test_rolling_24h():
    for r in MUESTRA[:60]:
        i = POS[r["open_time"]]
        idx = [j for j in range(i - 1500, i + 1) if T[j] > T[i] - 24 * 3_600_000]
        assert len(idx) == 1440
        m, sd = ref_vwap(idx, lambda j: (H[j] + L[j]) / 2)
        assert cerca(r["rVWAP"], m) and cerca(r["rVAH"], m + sd) and cerca(r["rVAL"], m - sd)


def test_vwap_semana_con_sigma():
    for r in MUESTRA[:40]:
        i = POS[r["open_time"]]
        t0 = (T[i] - ind.LUNES_0) // (7 * MS_DIA) * 7 * MS_DIA + ind.LUNES_0
        m, sd = ref_vwap(range(POS[t0], i + 1), lambda j: (H[j] + L[j]) / 2)
        assert cerca(r["vwap_w"], m) and cerca(r["vwap_w_p2"], m + 2 * sd) and cerca(r["vwap_w_m1"], m - sd)


def barras(i0, i1, paso_ms):
    """Velas del TF mayor (open_time múltiplo de paso) con las 1m [i0, i1]; la última puede estar incompleta."""
    out, cur = [], None
    for j in range(i0, i1 + 1):
        b = T[j] // paso_ms
        if cur is None or cur[0] != b:
            cur = [b, H[j], L[j], C[j], V[j]]
            out.append(cur)
        else:
            cur[1], cur[2], cur[3], cur[4] = max(cur[1], H[j]), min(cur[2], L[j]), C[j], cur[4] + V[j]
    return out


def vwap_barras(bs, hlc3=False):
    src = [(b[1] + b[2] + b[3]) / 3 if hlc3 else (b[1] + b[2]) / 2 for b in bs]
    sv = sum(b[4] for b in bs)
    m = sum(s * b[4] for s, b in zip(src, bs)) / sv
    return m, math.sqrt(sum(b[4] * (s - m) ** 2 for s, b in zip(src, bs)) / sv)


def test_mvwap_vivo_e_hist():
    import datetime as dt
    for r in MUESTRA[:25]:
        i = POS[r["open_time"]]
        d = dt.datetime.fromtimestamp(T[i] / 1000, dt.timezone.utc)
        t0 = int(dt.datetime(d.year, d.month, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        bs = barras(POS[t0], i, 3_600_000)
        m, sd = vwap_barras(bs)
        assert cerca(r["mVWAP_vivo"], m) and cerca(r["mVAH_vivo"], m + sd), r["open_time"]
        # historial: sin la vela de 60m en formación (salvo que esta 1m la cierre)
        cierra = (T[i] + MS_MIN) % 3_600_000 == 0
        if not cierra and len(bs) > 1:
            m2, _ = vwap_barras(bs[:-1])
            assert cerca(r["mVWAP_hist"], m2), r["open_time"]


def test_pwvwap():
    for r in MUESTRA[:25]:
        i = POS[r["open_time"]]
        t0 = (T[i] - ind.LUNES_0) // (7 * MS_DIA) * 7 * MS_DIA + ind.LUNES_0
        bs = barras(POS[t0 - 7 * MS_DIA], POS[t0 - MS_MIN], 3_600_000)
        m, sd = vwap_barras(bs)
        assert cerca(r["pwVWAP_vivo"], m), r["open_time"]


def test_rolling_dias():
    for r in MUESTRA[:25]:
        i = POS[r["open_time"]]
        d0 = T[i] // MS_DIA * MS_DIA
        for nd in (7, 30):
            bs = barras(POS[d0 - nd * MS_DIA], i, MS_DIA)
            assert len(bs) == nd + 1
            src = [(b[1] + b[2] + b[3]) / 3 for b in bs]
            ref = sum(s * b[4] for s, b in zip(src, bs)) / sum(b[4] for b in bs)
            assert cerca(r[f"r{nd}D_vivo"], ref), (r["open_time"], nd)


def test_ema_ash_y_semilla():
    # recursión directa sobre los últimos 3000 minutos, sembrada con el valor del módulo: debe coincidir
    a = 2 / 12
    i = POS[MUESTRA[0]["open_time"]]
    full = ind.cargar("2022-01", "2026-09")
    e11 = full["ema11"].to_list()
    x = e11[i - 3000]
    for j in range(i - 2999, i + 1):
        x = a * C[j] + (1 - a) * x
    assert cerca(x, e11[i], 1e-9)
    # §3.2: arrancar la historia 6 meses después cambia la EMA 25 y el ASH en 2023 en forma despreciable
    k2 = K.filter(pl.col("open_time") >= 1_656_633_600_000)  # 2022-07-01
    c2 = k2["close"].to_numpy()
    e25b = ind.ema(c2, 25)
    bu, _ = ind.ash_rsi(c2)
    off = K.height - k2.height
    j = POS[1_672_531_200_000]  # 2023-01-01 00:00
    assert abs(e25b[j - off] - full["ema25"][j]) < 1e-9
    assert abs(bu[j - off] - full["ash_bulls"][j]) < 1e-9


def test_5m_vivo_cierra_igual():
    fin = DF.filter(((pl.col("open_time") + MS_MIN) % (5 * MS_MIN)) == 0).sample(200, seed=1)
    for r in fin.iter_rows(named=True):
        assert cerca(r["ema11_5m_vivo"], r["ema11_5m_cerr"], 1e-9)
        assert cerca(r["ash_bulls_5m_vivo"], r["ash_bulls_5m_cerr"], 1e-9)


def test_ohlc_y_mnday():
    import datetime as dt
    for r in MUESTRA[:40]:
        i = POS[r["open_time"]]
        d0 = T[i] // MS_DIA * MS_DIA
        assert r["DO"] == K["open"][POS[d0]]
        w0 = (T[i] - ind.LUNES_0) // (7 * MS_DIA) * 7 * MS_DIA + ind.LUNES_0
        assert r["WO"] == K["open"][POS[w0]]
        assert r["PWH"] == max(H[POS[w0 - 7 * MS_DIA]:POS[w0]])
        assert r["PWL"] == min(L[POS[w0 - 7 * MS_DIA]:POS[w0]])
        lunes = dt.datetime.fromtimestamp(T[i] / 1000, dt.timezone.utc).weekday() == 0
        fin_lunes = POS[w0 + MS_DIA] - 1 if not lunes else i
        assert r["MNDAY_H_vivo"] == max(H[POS[w0]:fin_lunes + 1])
        assert r["MNDAY_L_vivo"] == min(L[POS[w0]:fin_lunes + 1])


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("test_"):
            f()
            print("ok", nombre)
