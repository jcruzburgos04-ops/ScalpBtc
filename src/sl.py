"""F3 · Definiciones candidatas del SL (CLAUDE.md §4.1), sin lookahead: solo velas cerradas hasta la de la señal (i).

Long (short = espejo). Cada función devuelve el EXTREMO de referencia; el SL = extremo − margen.
  ext_k      mínimo de las últimas k velas (incluida la de la señal)
  fractal_n  último fractal de Williams confirmado (n velas a cada lado, todas ya cerradas) por debajo del cierre
  zigzag     mínimo más bajo desde el último máximo de swing (fractal alto n=2), con al menos una vela posterior
             de mínimo más alto (el mínimo no puede ser la vela de la señal)
  evento     mínimo desde que el ASH empezó a girar (inicio de la racha en que la brecha Bulls−Bears se cierra)
Margen: fracción del ATR(14) de 1m.
"""
from __future__ import annotations

import numpy as np


def ext_k(l: np.ndarray, h: np.ndarray, i: int, largo: bool, k: int) -> float:
    return float(l[i - k + 1:i + 1].min()) if largo else float(h[i - k + 1:i + 1].max())


def fractal(l: np.ndarray, h: np.ndarray, c: np.ndarray, i: int, largo: bool, n: int, max_atras: int = 120) -> float:
    for j in range(i - n, max(n, i - max_atras), -1):  # j + n <= i: confirmado al cierre de i
        if largo:
            v = l[j]
            if v < l[j - n:j].min() and v < l[j + 1:j + n + 1].min() and v < c[i]:
                return float(v)
        else:
            v = h[j]
            if v > h[j - n:j].max() and v > h[j + 1:j + n + 1].max() and v > c[i]:
                return float(v)
    return np.nan


def zigzag(l: np.ndarray, h: np.ndarray, c: np.ndarray, i: int, largo: bool, max_atras: int = 120) -> float:
    # último swing en contra (fractal alto n=2 para el long) confirmado
    a = None
    for j in range(i - 2, max(2, i - max_atras), -1):
        if largo and h[j] > h[j - 2:j].max() and h[j] > h[j + 1:j + 3].max():
            a = j
            break
        if not largo and l[j] < l[j - 2:j].min() and l[j] < l[j + 1:j + 3].min():
            a = j
            break
    if a is None:
        return np.nan
    seg = l[a:i + 1] if largo else h[a:i + 1]
    k = int(np.argmin(seg) if largo else np.argmax(seg)) + a
    if k == i:  # todavía no hay una vela posterior que lo confirme
        return np.nan
    return float(seg.min() if largo else seg.max())


def evento(l: np.ndarray, h: np.ndarray, g: np.ndarray, i: int, largo: bool, max_atras: int = 120) -> float:
    """g = Bulls − Bears del ASH de 1m. Para el long la brecha (negativa) se cierra: g sube vela a vela."""
    s = i
    while s > i - max_atras and (g[s] > g[s - 1] if largo else g[s] < g[s - 1]):
        s -= 1
    return float(l[s:i + 1].min()) if largo else float(h[s:i + 1].max())


def candidatos(l, h, c, g, i, largo) -> dict[str, float]:
    out = {f"ext_{k}": ext_k(l, h, i, largo, k) for k in (2, 3, 5, 10)}
    out.update({f"fractal_{n}": fractal(l, h, c, i, largo, n) for n in (1, 2, 3)})
    out["zigzag"] = zigzag(l, h, c, i, largo)
    out["evento"] = evento(l, h, g, i, largo)
    return out
