"""Pendiente de las rectas amarillas punteadas de las capturas del trader (Juan 2026-11-01: "calculá la pendiente que
utiliza el trader en sus trendlines, para ver si hay algún grado en común").

HALLAZGO: esas rectas NO son trendlines. Son la diagonal punteada de la herramienta Long/Short de TradingView, que une
la entrada con el precio en el borde derecho de la caja: 12 de 28 arrancan a ≤ 35 USD del precio de entrada de una
tarjeta de la misma captura, quedan dentro de las cajas verde/roja y varias terminan en el mismo punto. En las 17 capturas de septiembre 2026
(la del 1-oct queda afuera: reserva) se marcaron a mano 29 rectas candidatas; cada una se ajusta sola sobre los
píxeles amarillos (`afinar`: muestreo a lo largo de la recta, búsqueda en la normal y ajuste robusto). Se conservan
las que ajustan con residuo ≤ 1,5 px (o se marcan como dudosas).

Para cada recta:
- ángulo en pantalla (grados) tal como quedó en la captura. Depende del zoom de cada captura: no es comparable entre
  capturas ni con lo que el trader veía al dibujarla.
- precio de los extremos por OCR del eje de precios (recta ajustada a todas las etiquetas).
- hora de los extremos por OCR del eje de tiempo (interpolación entre etiquetas; el eje no es lineal en estas
  capturas), UTC+2 → UTC.
- pendiente en USD por minuto, en % por hora y en ATR(14) de 1m por vela (ATR de Binance a la mitad de la línea).
- ángulo "normalizado": el que tendría la recta en un gráfico donde 1 ATR de alto ocupa lo mismo que 10 velas de ancho.
Salida: reports/trader_sep/trendlines.md, trendlines.csv y trendlines.png (capturas marcadas en reports/trader_sep/trendlines/)
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import cv2
import numpy as np
import polars as pl
import pytesseract

import indicadores as ind
from trader_cajas import eje_precio

RAIZ = Path(__file__).resolve().parent.parent
CAP = RAIZ / "marcas" / "trader_sep2026"
OUT = RAIZ / "reports" / "trader_sep"
TZ = dt.timezone(dt.timedelta(hours=2))      # hora de las capturas
VELAS_POR_ATR = 10                           # escala del ángulo normalizado: 1 ATR de alto = 10 velas de ancho

# captura → (día del primer label del eje, [rectas aproximadas (x0, y0, x1, y1, nota)]) en píxeles de la captura
LINEAS = {
    "lote1_02": ("2026-09-28", [(1019, 887, 1475, 347, ""), (70, 602, 210, 575, "cortada por el borde"),
                                (70, 650, 210, 575, "cortada por el borde")]),
    "lote1_03": ("2026-09-26", [(88, 598, 575, 300, ""), (1260, 766, 1714, 657, ""), (1402, 841, 1714, 657, "")]),
    "lote2_01": ("2026-09-17", [(851, 799, 1428, 380, ""), (900, 867, 1950, 48, ""), (1030, 630, 1100, 700, "naranja")]),
    "lote2_02": ("2026-09-16", [(720, 475, 860, 720, ""), (1100, 540, 1600, 310, "")]),
    "lote2_04": ("2026-09-14", [(368, 39, 686, 371, "")]),
    "lote2_05": ("2026-09-14", [(133, 875, 706, 492, ""), (1080, 280, 1800, 890, "")]),
    "lote3_01": ("2026-09-13", [(684, 756, 1353, 244, "parte bajo una imagen")]),
    "lote3_02": ("2026-09-10", [(205, 737, 404, 625, ""), (1413, 717, 1797, 604, "")]),
    "lote3_03": ("2026-09-08", [(280, 805, 380, 630, ""), (1025, 567, 1069, 436, "dudosa")]),
    "lote3_04": ("2026-09-07", [(578, 353, 722, 502, ""), (942, 379, 1741, 891, "")]),
    "lote3_05": ("2026-09-03", [(62, 795, 910, 440, ""), (870, 481, 1581, 798, "")]),
    "lote4_01": ("2026-09-02", [(955, 656, 1702, 366, ""), (1176, 803, 1702, 372, ""), (225, 927, 860, 707, "")]),
    "lote4_02": ("2026-09-01", [(200, 742, 604, 471, ""), (780, 740, 920, 410, "")]),
    "lote4_03": ("2026-08-31", [(154, 1034, 988, 328, "")]),
}


def afinar(s, xa, ya, xb, yb, w=9, thr=10):
    """Recta punteada amarilla cerca de (xa,ya)-(xb,yb) sobre el mapa de "amarillez" s."""
    H, W = s.shape
    p0, p1 = np.array([xa, ya], float), np.array([xb, yb], float)
    L = np.linalg.norm(p1 - p0); u = (p1 - p0) / L; n = np.array([-u[1], u[0]])
    pts = []
    for t in np.arange(0, L, 1.0):
        cand = np.array([p0 + t * u + k * n for k in range(-w, w + 1)])
        xi, yi = np.round(cand[:, 0]).astype(int), np.round(cand[:, 1]).astype(int)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        if ok.sum() < 2 * w:
            continue
        v = s[yi[ok], xi[ok]]
        k = int(v.argmax())
        if v[k] - np.median(v) > thr:
            pts.append(cand[ok][k])
    p = np.array(pts)
    keep = np.ones(len(p), bool)
    for _ in range(8):
        m = p[keep].mean(0); d = np.linalg.svd(p[keep] - m)[2][0]; nn = np.array([-d[1], d[0]])
        res = np.abs((p - m) @ nn)
        keep = res < max(1.5, 2.5 * np.median(res[keep]))
    m = p[keep].mean(0); d = np.linalg.svd(p[keep] - m)[2][0]
    d = d if d[0] > 0 else -d
    tt = (p[keep] - m) @ d
    a0, a1 = m + tt.min() * d, m + tt.max() * d
    return a0, a1, float(np.median(res[keep])), int(keep.sum()) / max(float(tt.max() - tt.min()), 1.0)


def eje_tiempo(g, dia0: dt.date):
    """(x, ms UTC) de cada etiqueta del eje de tiempo. Las horas son UTC+2; un número de día o "Sep" marca las 00:00."""
    H = g.shape[0]
    e = cv2.resize(g[H - 45:H, :], None, fx=3, fy=3)
    d = pytesseract.image_to_data(e, config="--psm 6", output_type=pytesseract.Output.DICT)
    toks = sorted([(l / 3 + w / 6, t.strip()) for t, l, w in zip(d["text"], d["left"], d["width"]) if t.strip()])
    dia, prev, out = dia0, None, []
    for x, t in toks:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
        if m:
            mins = int(m.group(1)) * 60 + int(m.group(2))
            if prev is not None and mins < prev:
                dia += dt.timedelta(days=1)
            prev = mins
            out.append((x, dt.datetime.combine(dia, dt.time(mins // 60, mins % 60), TZ)))
        elif re.fullmatch(r"\d{1,2}", t) and 1 <= int(t) <= 31 or t.lower().startswith("sep"):
            # etiqueta de día: fija la fecha (00:00 de ese día) aunque no se haya leído la etiqueta anterior
            n = 1 if t.lower().startswith("sep") else int(t)
            nuevo = dia.replace(day=n) if n >= dia.day else (dia.replace(day=1) + dt.timedelta(days=32)).replace(day=n)
            if not 1 <= (nuevo - dia).days <= 2:      # basura del OCR (no es el día siguiente)
                continue
            dia, prev = nuevo, 0
            out.append((x, dt.datetime.combine(dia, dt.time(0, 0), TZ)))
    xs = np.array([o[0] for o in out]); ts = np.array([o[1].timestamp() * 1000 for o in out])
    ok = np.r_[True, np.diff(ts) > 0]
    return xs[ok], ts[ok]


def main() -> None:
    (OUT / "trendlines").mkdir(parents=True, exist_ok=True)
    df = ind.cargar("2026-08", "2026-09").select("open_time", "high", "low", "close", "atr14").sort("open_time")
    t1, atr = df["open_time"].to_numpy(), df["atr14"].to_numpy()
    filas = []
    for cap, (dia0, lineas) in LINEAS.items():
        f = CAP / f"{cap}.jpg"
        im = cv2.imread(str(f)); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        s = (im[..., 1].astype(float) + im[..., 2]) / 2 - im[..., 0]
        a_p, b_p, n_p = eje_precio(g)
        xs, ts = eje_tiempo(g, dt.date.fromisoformat(dia0))
        precio = lambda y: a_p * y + b_p  # noqa: E731
        tiempo = lambda x: float(np.interp(x, xs, ts))  # noqa: E731
        for k, (xa, ya, xb, yb, nota) in enumerate(lineas):
            p0, p1, resid, cob = afinar(s, xa, ya, xb, yb)
            ang = float(np.degrees(np.arctan2(-(p1[1] - p0[1]), p1[0] - p0[0])))
            pa, pb = precio(p0[1]), precio(p1[1])
            ta, tb = tiempo(p0[0]), tiempo(p1[0])
            mins = (tb - ta) / 60_000
            usd_min = (pb - pa) / mins
            i0, i1 = np.searchsorted(t1, [ta, tb])
            if i1 >= t1.size or i0 >= i1:
                print("fuera de rango:", cap, k + 1, dt.datetime.fromtimestamp(ta / 1000, dt.timezone.utc), dt.datetime.fromtimestamp(tb / 1000, dt.timezone.utc))
                continue
            a = float(np.median(atr[i0:i1]))          # ATR(14) de 1m mediano en el tramo de la línea
            atr_vela = usd_min / a
            filas.append({
                "captura": cap, "n": k + 1, "lado": "alcista" if pb > pa else "bajista",
                "desde_utc": dt.datetime.fromtimestamp(ta / 1000, dt.timezone.utc).strftime("%m-%d %H:%M"),
                "hasta_utc": dt.datetime.fromtimestamp(tb / 1000, dt.timezone.utc).strftime("%m-%d %H:%M"),
                "minutos": mins, "p_desde": pa, "p_hasta": pb, "usd_min": usd_min,
                "pct_hora": usd_min * 60 / ((pa + pb) / 2) * 100, "atr14": a, "atr_por_vela": atr_vela,
                "ang_normalizado": float(np.degrees(np.arctan(atr_vela * VELAS_POR_ATR))),
                "ang_pantalla": ang, "usd_px": -a_p, "min_px": mins / (p1[0] - p0[0]),
                "px_largo": float(np.hypot(*(p1 - p0))), "resid_px": resid, "cobertura": cob, "nota": nota,
                "x0": p0[0], "y0": p0[1], "x1": p1[0], "y1": p1[1],
            })
            cv2.line(im, tuple(np.round(p0).astype(int)), tuple(np.round(p1).astype(int)), (255, 0, 255), 3)
            cv2.putText(im, f"{k + 1}: {ang:.0f} gr", (int(p0[0]), int(p0[1]) - 8), 0, 0.9, (255, 0, 255), 2)
        cv2.imwrite(str(OUT / "trendlines" / f"{cap}.jpg"), cv2.resize(im, None, fx=0.6, fy=0.6))
    t = pl.DataFrame(filas)
    t.write_csv(OUT / "trendlines.csv", float_precision=3)
    print(t.select("captura", "n", "lado", "desde_utc", "hasta_utc", pl.col("minutos").round(0), pl.col("usd_min").round(2),
                   pl.col("pct_hora").round(3), pl.col("atr_por_vela").round(3), pl.col("ang_normalizado").round(1),
                   pl.col("ang_pantalla").round(1), pl.col("resid_px").round(2), "nota"))


if __name__ == "__main__":
    main()
