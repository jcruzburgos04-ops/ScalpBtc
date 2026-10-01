"""B2 · casos dibujados de septiembre (regla 2: antes de cualquier resultado agregado).
Tres grupos con la variante elegida por coincidencia: entradas del trader que B2 detecta, entradas que B2 no detecta y
señales de B2 en sus horas que él no tomó. Salida: reports/b2/pagina/b2_revision.html"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parent.parent
B2 = RAIZ / "reports" / "b2"
VAR = sys.argv[1] if len(sys.argv) > 1 else "V10"
ANTES, DESPUES = 150, 60
LINEAS = {"vwap": "vwap_d", "p1": "vwap_d_p1", "m1": "vwap_d_m1", "p2": "vwap_d_p2", "m2": "vwap_d_m2",
          "vw": "vwap_w", "rv": "rVWAP", "vah": "dVAH", "val": "dVAL", "e11": "ema11", "e25": "ema25"}


def r1(x):
    return None if x is None or x != x else round(float(x), 1)


def main(semilla: int = 3) -> None:
    rnd = random.Random(semilla)
    m = pl.read_parquet(B2 / "minutos_sep.parquet").sort("open_time")
    t = m["open_time"].to_list()
    idx = {v: i for i, v in enumerate(t)}
    s = pl.read_parquet(B2 / f"senales_sep_{VAR}.parquet")
    tr = pl.read_parquet(RAIZ / "reports" / "trader_sep" / "entradas.parquet").filter(pl.col("t_entrada").is_not_null())
    ent = [(int(a), b, c, float(d)) for a, b, c, d in tr.select("t_entrada", "lado", "id", "entrada").iter_rows()]
    sen = [(int(a), b) for a, b in s.iter_rows()]
    dias = {}
    for te, *_ in ent:
        d = te // 86_400_000
        a, b = dias.get(d, (te, te))
        dias[d] = (min(a, te), max(b, te))
    en_horas = lambda x: any(a - 3_600_000 <= x <= b + 3_600_000 for a, b in dias.values())  # noqa: E731
    detect = [e for e in ent if any(l == e[1] and e[0] - 15 * 60_000 <= ts <= e[0] + 5 * 60_000 for ts, l in sen)]
    no_det = [e for e in ent if e not in detect]
    no_tom = [x for x in sen if en_horas(x[0]) and not any(l == x[1] and x[0] - 5 * 60_000 <= te <= x[0] + 15 * 60_000 for te, l, *_ in ent)]
    grupos = [("Entrada del trader que B2 detecta", [(e[0], e[1]) for e in rnd.sample(detect, min(5, len(detect)))]),
              ("Entrada del trader que B2 NO detecta", [(e[0], e[1]) for e in rnd.sample(no_det, min(4, len(no_det)))]),
              ("Señal de B2 que el trader no tomó", rnd.sample(no_tom, min(5, len(no_tom))))]
    casos = []
    for etiqueta, lista in grupos:
        for centro, lado in sorted(lista):
            i = idx[centro]
            x = m.slice(max(0, i - ANTES), ANTES + DESPUES + 1)
            a, b = int(x["open_time"][0]), int(x["open_time"][-1])
            k = m.row(i - 1, named=True)   # última vela cerrada antes del centro
            sg = 1 if lado == "long" else -1
            casos.append({
                "id": f"C{len(casos) + 1:02d}", "etiqueta": etiqueta, "lado": lado, "t": centro,
                "velas": [[int(r[0]) // 1000, r1(r[1]), r1(r[2]), r1(r[3]), r1(r[4])] for r in x.select("open_time", "open", "high", "low", "close").iter_rows()],
                "lineas": {kk: [r1(v) for v in x[c].to_list()] for kk, c in LINEAS.items()},
                "trader": [{"t": te, "lado": l, "id": i_, "p": p} for te, l, i_, p in ent if a <= te <= b],
                "b2": [{"t": ts, "lado": l} for ts, l in sen if a <= ts <= b],
                "lect": {"Volumen 15 min": f"{k['vol15_rel']:.1f}× lo normal", "Absorción 5 velas": f"{k['absorcion5']:.1f}",
                         "Delta de la vela": f"{sg * k['delta1'] * 100:+.0f} % a favor", "Delta últimos 10 s": f"{sg * (k['delta10s'] or 0) * 100:+.0f} % a favor",
                         "Burbujas 15 min": f"{k['ns15'] if sg > 0 else k['nb15']} en contra · {k['nb15'] if sg > 0 else k['ns15']} a favor",
                         "CVD 15 min": f"{sg * k['cvd15'] * 100:+.0f} % a favor",
                         "VWAP sesión": f"{(k['close'] - k['vwap_d']) / (k['vwap_d_p1'] - k['vwap_d']):+.1f}σ"},
            })
    out = B2 / "pagina"
    out.mkdir(parents=True, exist_ok=True)
    html = (RAIZ / "src" / "plantillas" / "b2_revision.html").read_text()
    html = html.replace("__CASOS__", json.dumps(casos, separators=(",", ":"), ensure_ascii=False)).replace("__VAR__", VAR)
    (out / "b2_revision.html").write_text(html)
    print(out / "b2_revision.html", len(casos), "casos;", len(detect), "detectadas,", len(no_det), "no detectadas,", len(no_tom), "no tomadas")


if __name__ == "__main__":
    main()
