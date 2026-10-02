"""B2 con toma parcial (pedido de Juan 2026-10-02: un win rate de 13–15 % es inaceptable psicológicamente).

Misma señal congelada (b2_final: V10_hondo_ag + EMA 200 de 45m) y mismo filtro R ≥ 2 hasta el TP final.
Salida con parcial: se cierra una fracción f de la posición en +p R; desde ese momento el SL del resto pasa a la entrada
(breakeven); el resto va al TP final. Combinaciones (fijadas antes de mirar):
  SL       extremo de 10 velas ± 0,25 / 0,5 / 1 ATR
  parcial  f = 50 % en +0,5R / +1R ; f = 70 % en +1R
  TP final 2R · 3R · VWAP de sesión · banda ±1σ opuesta · primer nivel a ≥ 2R
Ganadora = R total > 0. Criterio de elección en calibración (jul–sep 2026), fijado antes: máximo R medio entre las
que ganan ≥ 50 % de las veces. Después se mide en 2023–2025. Velas de 1m; si el SL y el parcial o el TP caen en la
misma vela, cuenta el SL. Sin comisiones. Salida: reports/b2/parcial.md
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import polars as pl

import b2_final as bf
import b2_tendencia as bten
import b2_tp

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"


def simular(m: pl.DataFrame, s: pl.DataFrame, b: float, f: float, p: float, tp_modo: str) -> np.ndarray:
    t = m["open_time"].to_numpy()
    h, l, c, atr = (m[x].to_numpy() for x in ("high", "low", "close", "atr14"))
    niv = np.column_stack([m[x].to_numpy() for x in b2_tp.NIV])
    idx = {v: i for i, v in enumerate(t)}
    res = []
    for lado in ("long", "short"):
        sg = 1 if lado == "long" else -1
        libre = -1
        for ts_ in s.filter(pl.col("lado") == lado)["t_senal"].to_list():
            i = idx[ts_]
            if i <= libre:
                continue
            ext = l[i - 9:i + 1].min() if sg > 0 else h[i - 9:i + 1].max()
            fill = c[i]
            sl = ext - sg * b * atr[i]
            rg = sg * (fill - sl)
            if rg <= 0:
                continue
            if tp_modo.endswith("R"):
                tp = fill + sg * float(tp_modo[:-1]) * rg
            elif tp_modo == "vwap":
                tp = niv[i, 0]
            elif tp_modo == "banda":
                tp = niv[i, 1] if sg > 0 else niv[i, 2]
            else:
                d = sg * (niv[i] - fill)
                ok = d >= 2 * rg
                if not ok.any():
                    continue
                tp = fill + sg * d[ok].min()
            if not np.isfinite(tp) or sg * (tp - fill) < 2 * rg - 1e-9:
                continue
            nivel_p = fill + sg * p * rg
            fin = min(i + 1440, t.size - 1)
            stop, cobrado, resto, r, j_sal = sl, 0.0, 1.0, None, fin
            for j in range(i + 1, fin + 1):
                if (l[j] <= stop) if sg > 0 else (h[j] >= stop):
                    r, j_sal = cobrado + resto * sg * (stop - fill) / rg, j
                    break
                if resto == 1.0 and ((h[j] >= nivel_p) if sg > 0 else (l[j] <= nivel_p)):
                    cobrado, resto, stop = f * p, 1.0 - f, fill
                if (h[j] >= tp) if sg > 0 else (l[j] <= tp):
                    r, j_sal = cobrado + resto * sg * (tp - fill) / rg, j
                    break
            if r is None:
                r = cobrado + resto * sg * (c[fin] - fill) / rg
            res.append(r)
            libre = j_sal
    return np.array(res)


def main() -> None:
    cal = bf.preparar(bten.minutos("2026-01", "2026-09", None, "cal"))
    tests = [bf.preparar(bten.minutos(f"{a - 1}-01", f"{a}-12", a, str(a))) for a in (2023, 2024, 2025)]
    filas = []
    for b, (f, p), tp in itertools.product((0.25, 0.5, 1.0), ((0.5, 0.5), (0.5, 1.0), (0.7, 1.0)), ("2R", "3R", "vwap", "banda", "nivel")):
        rc = simular(*cal, b, f, p, tp)
        rt = np.concatenate([simular(*x, b, f, p, tp) for x in tests])
        filas.append((b, f, p, tp, rc, rt))
    ok = [x for x in filas if x[4].size >= 100 and (x[4] > 0).mean() >= 0.5]
    elegida = max(ok, key=lambda x: x[4].mean()) if ok else None
    l = ["B2 congelada + toma parcial (filtro R ≥ 2 al TP final, sin comisiones). Ganadora = R total > 0.", "",
         "| SL | Parcial | TP final | Calib. jul–sep 2026: trades · gana · R | Test 2023–2025: trades · gana · R |", "|---|---|---|---|---|"]
    for b, f, p, tp, rc, rt in filas:
        marca = " **← elegida**" if elegida and (b, f, p, tp) == elegida[:4] else ""
        l.append(f"| {b:g} ATR | {f:.0%} en +{p:g}R | {tp} | {rc.size} · {(rc > 0).mean():.0%} · {rc.mean():+.3f} | "
                 f"{rt.size} · {(rt > 0).mean():.0%} · {rt.mean():+.3f}{marca} |")
    if elegida:
        rt = elegida[5]
        lo, hi = bf.ic(rt)
        l += ["", f"Elegida en calibración (máximo R con gana ≥ 50 %): SL {elegida[0]:g} ATR · {elegida[1]:.0%} en +{elegida[2]:g}R · "
              f"TP {elegida[3]} → test {rt.size} trades, gana {(rt > 0).mean():.0%}, pierde {(rt < 0).mean():.0%}, "
              f"R medio {rt.mean():+.3f} [IC 95 % {lo:+.3f}, {hi:+.3f}]"]
    txt = "\n".join(l)
    (OUT / "parcial.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
