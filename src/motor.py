"""F3 · Motor de ejecución (CLAUDE.md §4).

Una PATA = un trade independiente con su fill, su SL, su TP y su resolución intravela (§4.3).
  · Fill: precio del primer tick posterior al cierre de la vela de señal = open de la primera barra de 1 s con
    ts ≥ cierre (§4.1).
  · TP (last, orden límite): primer segundo de aggTrades que alcanza el precio (barras de 1 s).
  · SL (mark price, 1m): primer minuto en que el mark toca el SL. Si en ese mismo minuto el last también tocó el TP,
    o si es el minuto de la entrada, se arma un mark sintético segundo a segundo = last de 1 s + base (mark − last)
    interpolada entre la apertura y el cierre del minuto, y se verifica que reproduzca el high/low del mark 1m. Si
    ordena los eventos sin empate, se usa ese orden; si no, el caso es AMBIGUO: pérdida en el criterio conservador
    y TP en el optimista (§4.2).
  · Tope técnico 24 h: sale al cierre de la última vela.
POSICIÓN (§4.3): una a la vez; señales a favor agregan patas (máx. 4 abiertas, cada una con R ≥ R_MIN hasta su TP);
señales en contra se ignoran y se registran. INVALIDACIÓN (§5.1, opcional, redefinida por Juan 2026-10-01), POR PATA:
al cierre de la primera vela con ≥ 30 min reales desde el fill de esa pata, |close − fill| ≤ 0,5 R, el precio cruzó
el fill ≥ 7 veces y el ASH de 1m cruzó ≥ 3 veces desde su entrada → se cierra esa pata; las demás siguen.
SL: por defecto por LAST price al segundo (confirmado por Juan 2026-10-01); el modo "mark" queda como variante.
Todo en ms UTC; resultados en R.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from datos import leer_1s, leer_mark_1m, leer_velas_1m

MS_MIN = 60_000
TICK = 0.1
TOPE_MS = 24 * 3_600_000
TOL_SINT = 2e-4          # tolerancia relativa para aceptar que el mark sintético reproduce high/low del mark 1m
APALANC_MAX = 125.0      # apalancamiento máximo de BTCUSDT (primer tramo): solo para marcar factibilidad


@dataclass
class Params:
    slip_sl_ticks: float = 0.0
    invalidacion: bool = False
    inv_min: int = 30
    inv_x_r: float = 0.5
    max_patas: int = 4
    r_min: float = 2.0
    sl_por: str = "last"   # "last" (confirmado 2026-10-01): SL por last al segundo, sin sintético · "mark": variante
    be_r: float | None = None      # scratch: al llegar a +be_r R a favor, el SL pasa a la entrada (breakeven)
    parcial_r: float | None = None  # toma parcial: al llegar a +parcial_r R se cierra parcial_f de la pata (orden límite)
    parcial_f: float = 0.5          # y el SL del resto pasa a la entrada
    corte_min: int | None = None   # scratch por tiempo: si a los corte_min minutos no llegó a +corte_r R, sale a mercado
    corte_r: float = 0.5
    inv_cruces_fill: int = 7  # invalidación: el precio cruzó el fill de la pata al menos estas veces (cierres de 1m)
    inv_cruces_ash: int = 3   # invalidación: el ASH de 1m cruzó (Bulls/Bears) al menos estas veces desde la entrada


class Datos:
    """Acceso rápido a velas 1m (last), mark 1m y barras de 1 s (cacheadas por mes)."""

    def __init__(self, desde: str, hasta: str):
        k = leer_velas_1m(desde, hasta).sort("open_time")
        self.t = k["open_time"].to_numpy()
        self.c = k["close"].to_numpy()
        m = leer_mark_1m(desde, hasta).sort("open_time")
        mm = pl.DataFrame({"open_time": self.t}).join(m, on="open_time", how="left")
        self.mo, self.mh, self.ml, self.mc = (mm[x].to_numpy() for x in ("open", "high", "low", "close"))
        self.mrec = mm["reconstruido"].fill_null(False).to_numpy()
        import indicadores
        ia = indicadores.cargar(desde, hasta).select("open_time", "ash_bulls", "ash_bears")
        ia = pl.DataFrame({"open_time": self.t}).join(ia, on="open_time", how="left")
        self.ash_signo = np.sign((ia["ash_bulls"] - ia["ash_bears"]).fill_null(0).to_numpy())
        self._s: dict[str, dict] = {}

    def idx(self, t_ms: int) -> int:
        return int(np.searchsorted(self.t, t_ms))

    def seg(self, mes: str) -> dict:
        if mes not in self._s:
            if len(self._s) > 3:
                self._s.pop(next(iter(self._s)))
            b = leer_1s(mes)
            self._s[mes] = {x: b[x].to_numpy() for x in ("ts", "o", "h", "l", "c")}
        return self._s[mes]

    def barras_1s(self, desde_ms: int, hasta_ms: int) -> dict:
        """Barras de 1 s con ts en [desde, hasta), pudiendo cruzar de mes."""
        import datetime as dt
        out = {x: [] for x in ("ts", "o", "h", "l", "c")}
        t = desde_ms
        while t < hasta_ms:
            d = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc)
            mes = d.strftime("%Y-%m")
            prox = int(dt.datetime(d.year + (d.month == 12), d.month % 12 + 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            s = self.seg(mes)
            a, z = np.searchsorted(s["ts"], t), np.searchsorted(s["ts"], min(hasta_ms, prox))
            for x in out:
                out[x].append(s[x][a:z])
            t = prox
        return {x: np.concatenate(v) if v else np.array([]) for x, v in out.items()}


@dataclass
class Pata:
    pos_id: int
    n: int
    lado: str
    t_senal: int
    fill_ts: int
    fill: float
    sl: float
    tp: float
    salida_ts: int = 0
    salida: float = np.nan
    motivo: str = ""
    ambiguo: bool = False
    resuelto_sintetico: bool = False
    salida_opt: float = np.nan
    motivo_opt: str = ""
    mark_reconstruido: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def riesgo(self) -> float:
        return abs(self.fill - self.sl)

    def r(self, precio: float) -> float:
        s = 1 if self.lado == "long" else -1
        r = s * (precio - self.fill) / self.riesgo
        f = self.extra.get("parcial_f", 0.0)       # fracción cobrada en +parcial_r R antes de la salida del resto
        return f * self.extra.get("parcial_r", 0.0) + (1 - f) * r if f else r


def _sintetico(D: Datos, i: int, desde_ms: int) -> tuple[dict, bool]:
    """Mark sintético segundo a segundo del minuto i: last 1 s + base interpolada. Devuelve barras y si reproduce."""
    t0 = int(D.t[i])
    b = D.barras_1s(t0, t0 + MS_MIN)
    if b["ts"].size == 0 or np.isnan(D.mo[i]):
        return b, False
    base0 = D.mo[i] - b["o"][0]
    base1 = D.mc[i] - b["c"][-1]
    f = (b["ts"] - t0) / MS_MIN
    base = base0 + (base1 - base0) * f
    b = {**b, "sh": b["h"] + base, "sl": b["l"] + base}
    tol = TOL_SINT * D.mc[i]
    reproduce = abs(b["sh"].max() - D.mh[i]) <= tol and abs(b["sl"].min() - D.ml[i]) <= tol
    m = b["ts"] >= desde_ms
    b = {k: v[m] for k, v in b.items()}
    return b, reproduce


def resolver_pata_last(D: Datos, p: Pata, P: Params, fin_forzado: int | None = None) -> Pata:
    """SL y TP por last price con barras de 1 s: gana el primer segundo que toca; si los dos caen en el mismo segundo
    es ambiguo (conservador: SL; optimista: TP). Sin mark ni trayectorias sintéticas.
    Manejo opcional (scratch del trader): breakeven al llegar a +be_r R y corte por tiempo a los corte_min minutos si
    no llegó a +corte_r R (sale al cierre de esa vela de 1m)."""
    largo = p.lado == "long"
    sg = 1.0 if largo else -1.0
    i_tope = D.idx(p.fill_ts + TOPE_MS)
    i_fin = min(i_tope, D.t.size - 1)
    motivo_fin = "tope_24h"
    if fin_forzado is not None and D.idx(fin_forzado - MS_MIN) < i_fin:
        i_fin, motivo_fin = D.idx(fin_forzado - MS_MIN), "invalidacion"
    b = D.barras_1s(p.fill_ts, int(D.t[i_fin]) + MS_MIN)
    fav = (b["h"] - p.fill) if largo else (p.fill - b["l"])  # recorrido a favor por segundo
    mfe_acum = np.maximum.accumulate(fav) if fav.size else fav
    # corte por tiempo: la vela de 1m que cierra a los corte_min minutos del fill
    if P.corte_min is not None and fav.size:
        i_c = D.idx(p.fill_ts + P.corte_min * MS_MIN - MS_MIN)
        if int(D.t[i_c]) + MS_MIN < p.fill_ts + P.corte_min * MS_MIN:
            i_c += 1
        if i_c < i_fin:
            k_c = int(np.searchsorted(b["ts"], int(D.t[i_c]) + MS_MIN)) - 1
            if k_c >= 0 and mfe_acum[k_c] < P.corte_r * p.riesgo:
                i_fin, motivo_fin = i_c, "corte_tiempo"
                b = {x: v[:k_c + 1] for x, v in b.items()}
                fav, mfe_acum = fav[:k_c + 1], mfe_acum[:k_c + 1]
    tp_b = (b["h"] >= p.tp) if largo else (b["l"] <= p.tp)
    sl_b = (b["l"] <= p.sl) if largo else (b["h"] >= p.sl)
    motivo_sl, precio_sl = "SL", p.sl
    be_r = P.parcial_r if P.parcial_r is not None else P.be_r
    if be_r is not None and fav.size:
        alcanzo = mfe_acum >= be_r * p.riesgo
        if alcanzo.any():
            k_be = int(np.argmax(alcanzo))
            # después del segundo en que llegó a +be_r R, el stop está en la entrada
            be_b = (b["l"] <= p.fill) if largo else (b["h"] >= p.fill)
            be_b[:k_be + 1] = False
            sl_antes = sl_b.copy()
            sl_antes[k_be + 1:] = False
            k1 = int(np.argmax(sl_antes)) if sl_antes.any() else None
            k2 = int(np.argmax(be_b)) if be_b.any() else None
            if k1 is None and P.parcial_r is not None:      # el parcial se cobró antes de tocar el SL
                p.extra["parcial_f"], p.extra["parcial_r"] = P.parcial_f, P.parcial_r
            if k1 is None and k2 is not None:
                sl_b, motivo_sl, precio_sl = be_b, "breakeven", p.fill
            else:
                sl_b = sl_antes
    k_tp = int(np.argmax(tp_b)) if tp_b.any() else None
    k_sl = int(np.argmax(sl_b)) if sl_b.any() else None
    slip = P.slip_sl_ticks * TICK * (-sg)
    if k_tp is None and k_sl is None:
        p.salida_ts, p.salida, p.motivo = int(D.t[i_fin]) + MS_MIN - 1, float(D.c[i_fin]), motivo_fin
    elif k_sl is None or (k_tp is not None and k_tp < k_sl):
        p.salida_ts, p.salida, p.motivo = int(b["ts"][k_tp]), p.tp, "TP"
    elif k_tp is None or k_sl < k_tp:
        p.salida_ts, p.salida, p.motivo = int(b["ts"][k_sl]), precio_sl + slip, motivo_sl
    else:
        p.salida_ts, p.salida, p.motivo = int(b["ts"][k_sl]), precio_sl + slip, motivo_sl
        p.ambiguo, p.salida_opt, p.motivo_opt = True, p.tp, "TP"
        p.extra["ambiguo_tipo"] = "sl_y_tp_mismo_segundo"
    if not p.ambiguo:
        p.salida_opt, p.motivo_opt = p.salida, p.motivo
    return p


def resolver_pata(D: Datos, p: Pata, P: Params, fin_forzado: int | None = None, _optimista: bool = False) -> Pata:
    """Resuelve la salida de una pata ya llenada. fin_forzado: cierre por invalidación (ms del cierre de la vela)."""
    if P.sl_por == "last":
        return resolver_pata_last(D, p, P, fin_forzado)
    largo = p.lado == "long"
    i0 = D.idx(p.fill_ts // MS_MIN * MS_MIN)
    i_tope = D.idx(p.fill_ts + TOPE_MS)
    i_fin = min(i_tope, D.t.size - 1)
    if fin_forzado is not None:
        i_fin = min(i_fin, D.idx(fin_forzado - MS_MIN))
    # TP: primer segundo con el last en el TP (desde el fill)
    b = D.barras_1s(p.fill_ts, int(D.t[i_fin]) + MS_MIN)
    toca_tp = (b["h"] >= p.tp) if largo else (b["l"] <= p.tp)
    k_tp = int(np.argmax(toca_tp)) if toca_tp.any() else -1
    tp_ts = int(b["ts"][k_tp]) if k_tp >= 0 else None
    i_tp = D.idx(tp_ts // MS_MIN * MS_MIN) if tp_ts is not None else None
    # SL: primer minuto con el mark en el SL
    ml = D.ml[i0:i_fin + 1] if largo else D.mh[i0:i_fin + 1]
    toca_sl = (ml <= p.sl) if largo else (ml >= p.sl)
    i_sl = None
    entrada_dudosa = False
    for k in np.flatnonzero(toca_sl):
        i = i0 + int(k)
        if i == i0:  # minuto de la entrada: solo cuenta lo posterior al fill
            s, rep = _sintetico(D, i, p.fill_ts)
            cruza = (s["sl"] <= p.sl).any() if largo else (s["sh"] >= p.sl).any()
            if rep and not cruza:
                continue
            if not rep:  # no se sabe si el mark tocó el SL antes o después del fill
                entrada_dudosa = True
                if _optimista:
                    continue
        i_sl = i
        break
    slip = P.slip_sl_ticks * TICK * (-1 if largo else 1)

    def salir_sl(i, ts=None):
        p.salida_ts, p.salida, p.motivo = ts or int(D.t[i]) + MS_MIN - 1, p.sl + slip, "SL"
        p.mark_reconstruido = bool(D.mrec[i])

    def salir_tp():
        p.salida_ts, p.salida, p.motivo = tp_ts, p.tp, "TP"

    if i_sl is None and i_tp is None:
        if fin_forzado is not None and i_fin < i_tope:
            p.salida_ts, p.salida, p.motivo = int(D.t[i_fin]) + MS_MIN - 1, float(D.c[i_fin]), "invalidacion"
        else:
            p.salida_ts, p.salida, p.motivo = int(D.t[i_fin]) + MS_MIN - 1, float(D.c[i_fin]), "tope_24h"
    elif i_sl is None or (i_tp is not None and i_tp < i_sl):
        salir_tp()
    elif i_tp is None or i_sl < i_tp:
        salir_sl(i_sl)
    else:  # mismo minuto: mark sintético
        s, rep = _sintetico(D, i_sl, p.fill_ts)
        c_sl = (s["sl"] <= p.sl) if largo else (s["sh"] >= p.sl)
        ts_sl = int(s["ts"][np.argmax(c_sl)]) if c_sl.any() else None
        if rep and ts_sl is not None and ts_sl != tp_ts:
            p.resuelto_sintetico = True
            salir_sl(i_sl, ts_sl) if ts_sl < tp_ts else salir_tp()
        else:
            p.ambiguo = True
            salir_sl(i_sl)
            p.salida_opt, p.motivo_opt = p.tp, "TP"
    if not p.ambiguo:
        p.salida_opt, p.motivo_opt = p.salida, p.motivo
    if entrada_dudosa and not _optimista and p.motivo == "SL" and int(D.t[i_sl]) == int(D.t[i0]):
        # versión optimista: ignorar el toque dudoso del minuto de entrada y seguir
        q = Pata(p.pos_id, p.n, p.lado, p.t_senal, p.fill_ts, p.fill, p.sl, p.tp)
        resolver_pata(D, q, P, fin_forzado, _optimista=True)
        p.ambiguo = True
        p.salida_opt, p.motivo_opt = q.salida_opt, q.motivo_opt
        p.extra["ambiguo_tipo"] = "sl_minuto_entrada"
    elif p.ambiguo:
        p.extra["ambiguo_tipo"] = "sl_y_tp_mismo_minuto"
    return p


def fill_de(D: Datos, t_senal: int) -> tuple[int, float]:
    """Primer tick posterior al cierre de la vela de señal (open_time t_senal)."""
    cierre = t_senal + MS_MIN
    b = D.barras_1s(cierre, cierre + 10 * MS_MIN)
    if b["ts"].size == 0:  # pausa del exchange: no hay fill
        return None, None
    return int(b["ts"][0]), float(b["o"][0])


def simular(D: Datos, senales: pl.DataFrame, P: Params, todas_las_senales: np.ndarray | None = None) -> tuple[list[Pata], list[dict]]:
    """senales: open_time, lado, en_ventana (bool), sl, tp (precios ex ante calculados al cierre de la vela de señal).
    todas_las_senales: open_time de TODAS las señales (para contar en la invalidación)."""
    patas: list[Pata] = []
    ignoradas: list[dict] = []
    abiertas: list[Pata] = []
    pos_id, lado_pos, fin_pos = 0, None, -1
    if todas_las_senales is None:
        todas_las_senales = senales["open_time"].to_numpy()
    for s in senales.sort("open_time").iter_rows(named=True):
        t = s["open_time"]
        cierre = t + MS_MIN
        abiertas = [a for a in abiertas if a.salida_ts > cierre]
        if not abiertas:
            lado_pos = None
        if not s["en_ventana"]:
            continue
        if lado_pos is not None and s["lado"] != lado_pos:
            ignoradas.append({"open_time": t, "lado": s["lado"], "motivo": "contraria_con_posicion"})
            continue
        if lado_pos is not None and len(abiertas) >= P.max_patas:
            ignoradas.append({"open_time": t, "lado": s["lado"], "motivo": "max_patas"})
            continue
        fts, fpx = fill_de(D, t)
        if fts is None:
            ignoradas.append({"open_time": t, "lado": s["lado"], "motivo": "sin_fill"})
            continue
        largo = s["lado"] == "long"
        s = {**s, "sl": (np.floor if largo else np.ceil)(round(s["sl"] / TICK, 6)) * TICK}  # SL en la grilla de 0,1
        if s.get("tp") is not None:  # TP absoluto (p. ej. la media): a la grilla, del lado más lejano al fill
            s = {**s, "tp": (np.floor if largo else np.ceil)(round(s["tp"] / TICK, 6)) * TICK}
        if s.get("tp") is None:  # TP en R fijo desde el fill (orden límite puesta al llenarse la entrada)
            tp = fpx + (1 if largo else -1) * s["tp_r"] * abs(fpx - s["sl"])
            s = {**s, "tp": (np.ceil if largo else np.floor)(round(tp / TICK, 6)) * TICK}  # TP en la grilla
        if (largo and not (s["sl"] < fpx < s["tp"])) or (not largo and not (s["tp"] < fpx < s["sl"])):
            ignoradas.append({"open_time": t, "lado": s["lado"], "motivo": "fill_fuera_de_sl_tp"})
            continue
        if abs(s["tp"] - fpx) / abs(fpx - s["sl"]) < P.r_min - 1e-9:  # tolerancia de punto flotante
            ignoradas.append({"open_time": t, "lado": s["lado"], "motivo": "r_menor_al_minimo"})
            continue
        nueva = lado_pos is None
        if nueva:
            pos_id += 1
            lado_pos = s["lado"]
        p = Pata(pos_id, 1 if nueva else len([x for x in patas if x.pos_id == pos_id]) + 1, s["lado"], t, fts, fpx, s["sl"], s["tp"])
        p.extra = {k: v for k, v in s.items() if k not in ("open_time", "lado", "sl", "tp", "en_ventana")}
        p.extra["close_senal"] = float(D.c[D.idx(t)])
        # invalidación por pata: cada una con su propio fill y su propio reloj de 30 min reales
        resolver_pata(D, p, P, _tiempo_invalidacion(D, p, P) if P.invalidacion else None)
        patas.append(p)
        abiertas.append(p)
    return patas, ignoradas


def _cruces(signo: np.ndarray) -> np.ndarray:
    """Cantidad acumulada de cambios de lado (los ceros arrastran el último lado no nulo)."""
    sg = signo.copy()
    for k in range(1, sg.size):
        if sg[k] == 0:
            sg[k] = sg[k - 1]
    cambia = (sg[1:] != sg[:-1]) & (sg[1:] != 0) & (sg[:-1] != 0)
    return np.concatenate([[0], np.cumsum(cambia)])


def _tiempo_invalidacion(D: Datos, p: Pata, P: Params) -> int | None:
    """Regla de Juan (redefinida 2026-10-01), POR PATA: al cierre de la primera vela de 1m con ≥ 30 min reales desde
    el fill de la pata, |close − fill| ≤ x·R, el precio cruzó el fill ≥ inv_cruces_fill veces y el ASH de 1m cruzó
    ≥ inv_cruces_ash veces desde la entrada. Devuelve el ms del cierre de esa vela."""
    i_e = D.idx(p.fill_ts // MS_MIN * MS_MIN)
    i_a = D.idx(p.fill_ts + P.inv_min * MS_MIN - MS_MIN)  # primera vela cuyo CIERRE cae con 30 min ya cumplidos
    if int(D.t[i_a]) + MS_MIN < p.fill_ts + P.inv_min * MS_MIN:
        i_a += 1
    i_b = min(D.idx(p.fill_ts + TOPE_MS), D.t.size - 1)
    if i_a >= i_b:
        return None
    cf = _cruces(np.sign(D.c[i_e:i_b] - p.fill))
    ca = _cruces(D.ash_signo[i_e:i_b])
    for i in range(i_a, i_b):
        k = i - i_e
        if abs(D.c[i] - p.fill) <= P.inv_x_r * p.riesgo and cf[k] >= P.inv_cruces_fill and ca[k] >= P.inv_cruces_ash:
            return int(D.t[i]) + MS_MIN
    return None


def a_tabla(patas: list[Pata]) -> pl.DataFrame:
    filas = []
    for p in patas:
        filas.append({
            "pos_id": p.pos_id, "pata": p.n, "lado": p.lado, "t_senal": p.t_senal, "fill_ts": p.fill_ts,
            "fill": p.fill, "close_senal": p.extra.get("close_senal"), "sl": p.sl, "tp": p.tp,
            "riesgo": p.riesgo, "salida_ts": p.salida_ts, "salida": p.salida, "motivo": p.motivo,
            "r": p.r(p.salida), "r_opt": p.r(p.salida_opt), "motivo_opt": p.motivo_opt, "ambiguo": p.ambiguo,
            "resuelto_sintetico": p.resuelto_sintetico, "mark_reconstruido": p.mark_reconstruido,
            "nocional_x_equity": 0.01 * p.fill / p.riesgo, "ambiguo_tipo": p.extra.get("ambiguo_tipo", ""),
            "minutos": (p.salida_ts - p.fill_ts) / MS_MIN,
            **{k: v for k, v in p.extra.items() if isinstance(v, (int, float, str, bool)) and k not in ("close_senal", "ambiguo_tipo")},
        })
    return pl.DataFrame(filas)
