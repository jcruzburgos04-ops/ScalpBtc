"""B2 escalonada (opción 1 aprobada por Juan, 2026-10-01): el movimiento se trata como una zona, como hace el trader.

Long (short espejo), señales V10_hondo_ag:
  pata 1   en la 1.ª señal de B2. SL común = extremo de 10 velas − k · ATR (fijo desde la pata 1).
  patas 2… en cada señal B2 siguiente del mismo lado, mientras la posición sigue abierta, si el precio está al menos
           0,5 ATR mejor que la última pata; hasta N patas.
  riesgo   1R repartido en N partes iguales contra el SL común: si las N patas tocan el SL se pierde 1R; con menos
           patas, menos.
  TP       vwap: VWAP de sesión al abrir · mitad: mitad de camino entre el precio medio y el VWAP · 1atr: precio medio + 1 ATR
           (se recalcula con cada pata).
Velas de 1m, si SL y TP caen en la misma vela cuenta el SL, horizonte 24 h, sin breakeven ni comisiones.
Período: jul–sep 2026 (calibración). Salida: reports/b2/escalonada.md
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import polars as pl

import b2_barrida as bb
import b2_timing as bt

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "reports" / "b2"
PASO_ATR = 0.5


def simular(m: pl.DataFrame, s: pl.DataFrame, k: float, n: int, tp_modo: str, escalera: float = 0.0) -> list[dict]:
    t = m["open_time"].to_numpy()
    h, l, c, atr, vw = (m[x].to_numpy() for x in ("high", "low", "close", "atr14", "vwap_d"))
    idx = {v: i for i, v in enumerate(t)}
    sen = {lado: [idx[x] for x in s.filter(pl.col("lado") == lado)["t_senal"].to_list()] for lado in ("long", "short")}
    out = []
    for lado, lista in sen.items():
        sg = 1 if lado == "long" else -1
        libre_desde = -1
        for j, i0 in enumerate(lista):
            if i0 <= libre_desde:
                continue
            a = atr[i0]
            ext = l[i0 - 9:i0 + 1].min() if sg > 0 else h[i0 - 9:i0 + 1].max()
            sl = ext - sg * k * a
            vw0 = vw[i0]
            if sg * (vw0 - c[i0]) <= 0 or sg * (c[i0] - sl) <= 0:
                continue
            patas = [c[i0]]
            pend = [x for x in lista[j + 1:]]
            fin = min(i0 + 1440, t.size - 1)
            resultado, i_sal = None, fin
            i = i0 + 1
            while i <= fin:
                media = float(np.mean(patas))
                tp = vw0 if tp_modo == "vwap" else (media + (vw0 - media) / 2 if tp_modo == "mitad" else media + sg * a)
                toca_sl = (l[i] <= sl) if sg > 0 else (h[i] >= sl)
                toca_tp = (h[i] >= tp) if sg > 0 else (l[i] <= tp)
                if toca_sl:
                    resultado, salida, i_sal = "SL", sl, i
                    break
                if toca_tp:
                    resultado, salida, i_sal = "TP", tp, i
                    break
                if escalera:                        # órdenes límite cada `escalera` ATR por debajo de la pata 1
                    nivel = patas[0] - sg * escalera * a * len(patas)
                    if len(patas) < n and ((l[i] <= nivel) if sg > 0 else (h[i] >= nivel)) and sg * (nivel - sl) > 0:
                        patas.append(nivel)
                        continue                     # reevalúa la misma vela con la pata nueva (SL/TP)
                elif pend and pend[0] == i:          # nueva señal B2: ampliar si el precio mejoró
                    pend.pop(0)
                    if len(patas) < n and sg * (patas[-1] - c[i]) >= PASO_ATR * a and sg * (c[i] - sl) > 0:
                        patas.append(c[i])
                i += 1
            if resultado is None:
                salida = c[fin]
                resultado = "tope"
            # cada pata arriesga 1/n R contra el SL común
            r = sum((sg * (salida - p)) / (sg * (p - sl)) / n for p in patas)
            out.append({"t": int(t[i0]), "lado": lado, "patas": len(patas), "motivo": resultado, "r": r})
            libre_desde = i_sal
    return out


def main() -> None:
    m = bb.minutos().sort("open_time").with_columns(min60=pl.col("low").rolling_min(60), max60=pl.col("high").rolling_max(60))
    s = bt.senales(m, "hondo_ag")
    l = ["Jul–sep 2026 (calibración), velas de 1m, sin breakeven ni comisiones. R por posición (1R = las N patas en el SL).", "",
         "| SL detrás del extremo | Patas máx. | TP | Posiciones | Gana | R medio | Patas usadas (media) |", "|---|---|---|---|---|---|---|"]
    filas = []
    for k, n, tp in itertools.product((0.25, 1.0, 2.0, 3.0), (1, 2, 3), ("vwap", "mitad", "1atr")):
        x = pl.DataFrame(simular(m, s, k, n, tp))
        filas.append((k, n, tp, x.height, (x["r"] > 0).mean(), x["r"].mean(), x["patas"].mean()))
        l.append(f"| {k:g} ATR | {n} | {tp} | {x.height} | {(x['r'] > 0).mean():.0%} | {x['r'].mean():+.3f} | {x['patas'].mean():.2f} |")
    l += ["", "Ampliación con órdenes límite escalonadas (cada X ATR por debajo de la pata 1, en vez de esperar otra señal):", "",
          "| SL detrás del extremo | Patas | Escalón | TP | Posiciones | Gana | R medio | Patas usadas |", "|---|---|---|---|---|---|---|---|"]
    for k, n, esc, tp in itertools.product((2.0, 3.0), (2, 3), (0.5, 1.0), ("vwap", "mitad", "1atr")):
        x = pl.DataFrame(simular(m, s, k, n, tp, esc))
        l.append(f"| {k:g} ATR | {n} | {esc:g} ATR | {tp} | {x.height} | {(x['r'] > 0).mean():.0%} | {x['r'].mean():+.3f} | {x['patas'].mean():.2f} |")
    txt = "\n".join(l)
    (OUT / "escalonada.md").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
