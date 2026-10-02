"""Salidas del trader: cajas long/short de TradingView en sus capturas (septiembre 2026).

La herramienta de posición de TV dibuja una zona verde (de la entrada al TP) y una roja (de la entrada al SL).
1. Detección por color: verde = G − R ≥ 10; roja = R − G ≥ 8; rectángulos con relleno ≥ 60 %.
2. Posición = una zona verde y una roja que comparten el borde horizontal de la entrada (±8 px) y se superponen en x.
   Long: verde arriba y roja abajo. Short: al revés.
3. Ejes por OCR (tesseract): precio = recta ajustada a las etiquetas del eje derecho/izquierdo; tiempo = recta ajustada
   a las etiquetas HH:MM del eje inferior (días por las etiquetas numéricas y el pase de medianoche), en UTC+2.
Salida: reports/trader_sep/cajas.csv + capturas con las cajas marcadas (reports/trader_sep/cajas/*.jpg)
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import cv2
import numpy as np
import polars as pl
import pytesseract

RAIZ = Path(__file__).resolve().parent.parent
CAP = RAIZ / "marcas" / "trader_sep2026"
OUT = RAIZ / "reports" / "trader_sep"
TZ = dt.timezone(dt.timedelta(hours=2))


def ajuste(xs, ys):
    xs, ys = np.array(xs, float), np.array(ys, float)
    for _ in range(3):
        a, b = np.polyfit(xs, ys, 1)
        res = np.abs(ys - (a * xs + b))
        keep = res <= max(3 * np.median(res), 1e-9)
        if keep.all() or keep.sum() < 3:
            break
        xs, ys = xs[keep], ys[keep]
    return a, b, xs.size


def eje_precio(g):
    pares = []
    for x0, x1 in ((0, 75), (g.shape[1] - 110, g.shape[1])):
        e = cv2.resize(g[:, x0:x1], None, fx=3, fy=3)
        d = pytesseract.image_to_data(e, config="--psm 6 -c tessedit_char_whitelist=0123456789.,", output_type=pytesseract.Output.DICT)
        for t, y, h in zip(d["text"], d["top"], d["height"]):
            t = t.strip()
            if re.fullmatch(r"\d{2},\d{3}\.\d", t):
                pares.append(((y + h / 2) / 3, float(t.replace(",", ""))))
    if len(pares) < 4:
        return None
    a, b, n = ajuste([p[0] for p in pares], [p[1] for p in pares])   # precio = a·y + b
    return a, b, n


def eje_tiempo(g, dia0: dt.date):
    h = g.shape[0]
    e = cv2.resize(g[h - 45:h, :], None, fx=3, fy=3)
    d = pytesseract.image_to_data(e, config="--psm 6", output_type=pytesseract.Output.DICT)
    toks = sorted([(l / 3 + w / 6, t.strip()) for t, l, w in zip(d["text"], d["left"], d["width"]) if t.strip()])
    dia, prev_min, xs, ts = dia0, None, [], []
    for x, t in toks:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
        if m:
            mins = int(m.group(1)) * 60 + int(m.group(2))
            if prev_min is not None and mins < prev_min:
                dia = dia + dt.timedelta(days=1)
            prev_min = mins
            xs.append(x)
            ts.append(dt.datetime.combine(dia, dt.time(mins // 60, mins % 60), TZ).timestamp() * 1000)
        elif re.fullmatch(r"\d{1,2}", t) and 1 <= int(t) <= 31:
            n = int(t)
            nuevo = dia.replace(day=n) if n >= dia.day else (dia.replace(day=1) + dt.timedelta(days=32)).replace(day=n)
            if prev_min is not None:
                dia, prev_min = nuevo, 0
                xs.append(x)
                ts.append(dt.datetime.combine(dia, dt.time(0, 0), TZ).timestamp() * 1000)
            else:
                dia = nuevo
        elif t.lower().startswith("sep") and prev_min is not None:
            dia, prev_min = dt.date(2026, 9, 1), 0
            xs.append(x)
            ts.append(dt.datetime.combine(dia, dt.time(0, 0), TZ).timestamp() * 1000)
    if len(xs) < 4:
        return None
    a, b, n = ajuste(xs, ts)   # ms = a·x + b
    return a, b, n


def rects(m):
    mm = cv2.morphologyEx(m.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        x, y, w, h = cv2.boundingRect(c)
        if w >= 20 and h >= 8 and cv2.contourArea(c) / (w * h) >= 0.6:
            out.append((x, y, w, h))
    return out


def main() -> None:
    tr = pl.read_csv(CAP / "trades.csv")
    (OUT / "cajas").mkdir(parents=True, exist_ok=True)
    filas = []
    for f in sorted(CAP.glob("lote*.jpg")):
        if f.stem in ("lote1_01", "lote2_03"):          # 1-oct (reserva) y zoom repetido del 16-sep
            continue
        x = tr.filter(pl.col("captura") == f.stem)
        d0 = min(x["desde"].to_list()) if x.height else None
        dia0 = dt.date(2026, int(d0[:2]), int(d0[3:5])) - dt.timedelta(days=1) if d0 else dt.date(2026, 9, 1)
        im = cv2.imread(str(f))
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        ep, et = eje_precio(g), eje_tiempo(g, dia0)
        b_, g_, r_ = (im[..., k].astype(int) for k in range(3))
        verdes = rects(((g_ - r_) >= 10) & (g_ >= 45) & (g_ <= 140) & (np.abs(g_ - b_) <= 25))
        rojas = rects(((r_ - g_) >= 8) & (r_ >= 35) & (r_ <= 140) & ((r_ - b_) >= 6))
        dib = im.copy()
        for (vx, vy, vw, vh) in verdes:
            for (rx, ry, rw, rh) in rojas:
                sx = min(vx + vw, rx + rw) - max(vx, rx)
                if sx < 0.5 * min(vw, rw):
                    continue
                if abs((vy + vh) - ry) <= 8:
                    lado, y_tp, y_ent, y_sl = "long", vy, (vy + vh + ry) / 2, ry + rh
                elif abs((ry + rh) - vy) <= 8:
                    lado, y_tp, y_ent, y_sl = "short", vy + vh, (ry + rh + vy) / 2, ry
                else:
                    continue
                x0 = max(vx, rx)
                fila = {"captura": f.stem, "lado": lado, "x0": x0, "x1": min(vx + vw, rx + rw), "y_tp": y_tp, "y_ent": y_ent, "y_sl": y_sl}
                if ep:
                    a, b, _ = ep
                    fila.update(tp=a * y_tp + b, entrada=a * y_ent + b, sl=a * y_sl + b)
                    fila["r_tp"] = abs(fila["tp"] - fila["entrada"]) / abs(fila["entrada"] - fila["sl"])
                if et:
                    a, b, _ = et
                    fila.update(t_entrada=int(a * x0 + b), t_fin=int(a * fila["x1"] + b))
                filas.append(fila)
                cv2.rectangle(dib, (vx, vy), (vx + vw, vy + vh), (0, 255, 0), 3)
                cv2.rectangle(dib, (rx, ry), (rx + rw, ry + rh), (0, 0, 255), 3)
                cv2.putText(dib, f"{len(filas)}", (x0 + 4, int(y_ent) - 6), 0, 1.0, (0, 255, 255), 2)
        cv2.imwrite(str(OUT / "cajas" / f"{f.stem}.jpg"), cv2.resize(dib, None, fx=0.5, fy=0.5))
        print(f.stem, "precio", ep and ep[2], "tiempo", et and et[2], "posiciones", sum(1 for q in filas if q["captura"] == f.stem), flush=True)
    df = pl.DataFrame(filas).with_row_index("caja", offset=1)
    df.write_csv(OUT / "cajas.csv", float_precision=1)
    print(df.select("caja", "captura", "lado", "entrada", "tp", "sl", "r_tp"))


if __name__ == "__main__":
    main()
