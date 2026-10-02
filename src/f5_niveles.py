"""F5 · Importancia de los niveles/etiquetas (§8 de CLAUDE.md) + qué niveles usa el trader (sept 2026).

Parte 1 · descriptivo 2025-01 → 2026-09 (oct–dic 2026 es reserva). Para cada nivel:
  toque     la vela de 1m llega al nivel (±0,1 ATR) viniendo de un lado: las 30 velas previas no lo tocaron
            (cada toque abre un "episodio"; el siguiente toque cuenta desde que el precio se aleja otra vez 30 min)
  resultado en los 60 min siguientes: RECHAZO si el precio vuelve 1 ATR hacia el lado de donde vino antes de pasar
            1 ATR al otro lado; RUPTURA si pasa primero; nada si ninguna.
  placebo   el mismo nivel desplazado un % fijo por día (±0,2 % a ±1 %, signo y tamaño al azar, 5 sorteos): misma
            forma y dinámica, otra ubicación. Con muchas líneas cerca, el placebo dice cuánto rechazo hay "por azar".
  importancia = P(rechazo | nivel real) − P(rechazo | placebo), IC 95 % por bootstrap, p-valor (z de dos
            proporciones) y corrección de Benjamini-Hochberg sobre todos los niveles.
  condicionado al n.º de toque del día (1.º / 2.º / 3.º+) y a la subsesión (Asia 00–07, Londres 07–13, NY 13–21 UTC).
Parte 2 · trader: para sus 93 entradas ganadas + 15 perdidas, qué niveles estaban a ≤ 0,25 ATR, frente a 50 placebos.
Salida: reports/f5/niveles.md, niveles.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from numba import njit

import trader_sep as ts
from b2_filtro_niveles import npoc

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "f5"
NIVELES = {**ts.NIVELES, "nPOC (abajo)": "nPOC_abajo", "nPOC (arriba)": "nPOC_arriba", "MO": "MO", "YO": "YO",
           "PQH": "PQH", "PQL": "PQL", "yVAH": "yVAH_vivo", "yVAL": "yVAL_vivo", "yVWAP": "yVWAP_vivo",
           "30D rVWAP": "r30D_vivo", "VWAP +2σ semanal": "vwap_w_p2", "VWAP −2σ semanal": "vwap_w_m2"}
TOL, VUELTA, LIBRE, HORIZ = 0.1, 1.0, 30, 60


@njit(cache=True)
def toques(h, l, c, atr, L, tol, vuelta, libre, horiz):
    n = h.size
    ev_i = np.empty(n, np.int64); ev_lado = np.empty(n, np.int64); ev_res = np.empty(n, np.int64)
    k = 0
    ultimo_toque = -10**9
    for i in range(libre + 1, n - horiz - 1):
        if not (np.isfinite(L[i]) and np.isfinite(atr[i])) or atr[i] <= 0:
            continue
        t = tol * atr[i]
        toca = l[i] <= L[i] + t and h[i] >= L[i] - t
        if not toca:
            continue
        if i - ultimo_toque <= libre:
            ultimo_toque = i
            continue
        ultimo_toque = i
        lado = 1 if c[i - 1] > L[i - 1] else -1          # +1: venía de arriba (el nivel sería soporte)
        d = vuelta * atr[i]
        res = 0
        for j in range(i + 1, i + horiz + 1):
            arriba = h[j] >= L[i] + d
            abajo = l[j] <= L[i] - d
            if arriba or abajo:
                if arriba and abajo:
                    res = 0
                elif (arriba and lado == 1) or (abajo and lado == -1):
                    res = 1                                 # rechazo: volvió hacia donde venía
                else:
                    res = -1                                # ruptura
                break
        ev_i[k] = i; ev_lado[k] = lado; ev_res[k] = res
        k += 1
    return ev_i[:k], ev_lado[:k], ev_res[:k]


def placebo(L: np.ndarray, dia: np.ndarray, rng) -> np.ndarray:
    dias = np.unique(dia)
    off = rng.uniform(0.002, 0.01, dias.size) * rng.choice([-1, 1], dias.size)
    return L * (1 + off[np.searchsorted(dias, dia)])


def stats(res_real, res_pl):
    a, b = (res_real == 1).sum(), (res_real != 0).sum()
    c_, d = (res_pl == 1).sum(), (res_pl != 0).sum()
    p1, p0 = a / max(b, 1), c_ / max(d, 1)
    p = (a + c_) / max(b + d, 1)
    se = np.sqrt(p * (1 - p) * (1 / max(b, 1) + 1 / max(d, 1)))
    z = (p1 - p0) / se if se > 0 else 0.0
    from math import erf, sqrt
    pval = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return b, p1, p0, p1 - p0, pval


def bh(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    o = np.argsort(p)
    m = p.size
    ok = np.zeros(m, bool)
    thr = q * (np.arange(1, m + 1)) / m
    pas = np.flatnonzero(p[o] <= thr)
    if pas.size:
        ok[o[: pas.max() + 1]] = True
    return ok


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = npoc(ts.base("2024-12", "2026-09").sort("open_time"))
    df = df.filter(pl.from_epoch("open_time", time_unit="ms").dt.year() >= 2025)
    h, l, c, atr = (df[x].to_numpy().astype(np.float64) for x in ("high", "low", "close", "atr14"))
    t = df["open_time"].to_numpy()
    dia = t // 86_400_000
    hora = (t // 3_600_000) % 24
    rng = np.random.default_rng(0)
    filas = []
    for nom, col in NIVELES.items():
        if col not in df.columns:
            continue
        L = df[col].cast(pl.Float64).to_numpy()
        ei, el, er = toques(h, l, c, atr, L, TOL, VUELTA, LIBRE, HORIZ)
        if ei.size < 50:
            continue
        pr = [toques(h, l, c, atr, placebo(L, dia, rng), TOL, VUELTA, LIBRE, HORIZ)[2] for _ in range(5)]
        rp = np.concatenate(pr)
        n, p1, p0, dif, pval = stats(er, rp)
        b = []
        for _ in range(300):
            x = er[rng.integers(0, er.size, er.size)]
            b.append(np.mean(x[x != 0] == 1))
        # condicionado: n.º de toque del día y subsesión
        nt = np.zeros(ei.size, int)
        for k in range(ei.size):
            nt[k] = 1 + ((dia[ei[:k]] == dia[ei[k]])).sum()
        cond = {}
        for et, m in (("1.º toque", nt == 1), ("2.º", nt == 2), ("3.º+", nt >= 3),
                      ("Asia", hora[ei] < 7), ("Londres", (hora[ei] >= 7) & (hora[ei] < 13)), ("NY", (hora[ei] >= 13) & (hora[ei] < 21))):
            x = er[m]
            cond[et] = (x == 1).sum() / max((x != 0).sum(), 1) if (x != 0).sum() >= 20 else np.nan
        filas.append({"nivel": nom, "toques": int(n), "rechazo": p1, "rechazo_placebo": p0, "importancia": dif,
                      "ic_lo": p1 - p0 - 1.96 * np.std(b), "ic_hi": p1 - p0 + 1.96 * np.std(b), "p": pval,
                      **{f"rech_{k}": v for k, v in cond.items()}})
        print(nom, n, round(p1, 3), round(p0, 3), flush=True)
    r = pl.DataFrame(filas)
    r = r.with_columns(bh=pl.Series(bh(r["p"].to_numpy()))).sort("importancia", descending=True)
    r.write_csv(OUT / "niveles.csv", float_precision=4)
    # parte 2: trader
    tr = pl.concat([pl.read_parquet(RAIZ / "reports/trader_sep/entradas.parquet").filter(pl.col("t_entrada").is_not_null())
                    .select("t_entrada", "lado", "entrada").with_columns(g=pl.lit("ganada")),
                    pl.read_parquet(RAIZ / "reports/trader_sep/perdidas.parquet").select("t_entrada", "lado", "entrada").with_columns(g=pl.lit("perdida"))])
    dt = npoc(ts.base("2026-07", "2026-09").sort("open_time"))
    idx = {v: i for i, v in enumerate(dt["open_time"].to_list())}
    ii = np.array([idx[x] for x in tr["t_entrada"].to_list()])
    p = tr["entrada"].to_numpy() - 20
    a_ = dt["atr14"].to_numpy()[ii]
    dd = dt["open_time"].to_numpy() // 86_400_000
    tf = []
    for nom, col in NIVELES.items():
        if col not in dt.columns:
            continue
        L = dt[col].cast(pl.Float64).to_numpy()
        cerca = np.abs(p - L[ii]) <= 0.25 * a_
        pl_ = np.mean([np.mean(np.abs(p - placebo(L, dd, rng)[ii]) <= 0.25 * a_) for _ in range(50)])
        tf.append((nom, cerca.mean(), pl_, cerca.sum()))
    tf.sort(key=lambda x: -(x[1] - x[2]))
    l = ["# F5 · Importancia de los niveles", "",
         f"2025-01 → 2026-09, velas de 1m. Toque = el precio llega al nivel (±{TOL} ATR) tras {LIBRE} min sin tocarlo. Rechazo = vuelve "
         f"{VUELTA} ATR hacia donde venía antes de pasar {VUELTA} ATR al otro lado (en {HORIZ} min). Placebo = mismo nivel desplazado "
         "±0,2–1 % por día. Importancia = rechazo real − rechazo placebo. BH = significativo con Benjamini-Hochberg (q = 5 %).", "",
         "| Nivel | Toques | Rechazo | Placebo | Importancia [IC 95 %] | BH | 1.º toque | 2.º | 3.º+ | Asia | Londres | NY |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda v: "–" if v is None or v != v else f"{v:.0%}"  # noqa: E731
    for x in r.iter_rows(named=True):
        l.append(f"| {x['nivel']} | {x['toques']} | {x['rechazo']:.0%} | {x['rechazo_placebo']:.0%} | {100 * x['importancia']:+.1f} pts "
                 f"[{100 * x['ic_lo']:+.1f}, {100 * x['ic_hi']:+.1f}] | {'sí' if x['bh'] else 'no'} | {f(x['rech_1.º toque'])} | "
                 f"{f(x['rech_2.º'])} | {f(x['rech_3.º+'])} | {f(x['rech_Asia'])} | {f(x['rech_Londres'])} | {f(x['rech_NY'])} |")
    l += ["", "## Qué niveles tenía cerca el trader al entrar (sept 2026, ganadas + perdidas)", "",
          "| Nivel | Entradas a ≤ 0,25 ATR | Placebo | Veces más |", "|---|---|---|---|"]
    for nom, a1, a0, n in tf[:20]:
        l.append(f"| {nom} | {n} ({a1:.0%}) | {a0:.0%} | {a1 / a0:.1f}× |" if a0 > 0 else f"| {nom} | {n} ({a1:.0%}) | 0 % | – |")
    txt = "\n".join(l)
    (OUT / "niveles.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
