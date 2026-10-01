"""F6 · Elección de filtros de contexto SIN mirar el período de test.

Procedimiento (fijado antes de ver resultados):
  1. Entrenamiento = todas las patas anteriores al período de test. Cortes por quintiles calculados en entrenamiento.
  2. Candidatos: excluir el quintil inferior (Q1) o el superior (Q5) de cada variable.
  3. Selección codiciosa de hasta MAX_FILTROS exclusiones que más suben la expectativa en entrenamiento, cada una
     con mejora ≥ MEJORA_MIN R y conservando ≥ RETENCION_MIN de las patas.
  4. Se mide en el período de test sin tocar nada.
Dos esquemas: (a) estático: entrena 2023–2024, testea 2025–2026; (b) walk-forward trimestral en 2025–2026 con ventana
creciente desde 2023 (cada trimestre se elige con todo lo anterior).
Nota: el filtrado acá es sobre las patas ya simuladas (aproximación); el esquema (a) se confirma corriendo el motor.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parent.parent
VARS = ["z_vwap_d", "z_vwap_w", "cruces_ash30", "cruces_xo60", "rvol", "rvol_max3", "cvd5", "cvd15", "grandes5",
        "n_grandes5_favor", "n_grandes5_contra", "oi15", "oi60", "taker_ratio", "ash5_favor", "dist5m_atr", "atr_rel",
        "obst_2r", "nivel_cerca_r"]
MAX_FILTROS, MEJORA_MIN, RETENCION_MIN = 3, 0.005, 0.40


def cargar() -> pl.DataFrame:
    v = pl.concat([pl.read_parquet(RAIZ / "reports" / "f6" / f"variables_{n}.parquet") for n in ("2023_2024", "2025_2026")],
                  how="diagonal_relaxed")
    v = v.with_columns(pl.col("grandes5").fill_nan(0.0),
                       trim=pl.from_epoch("t_senal", time_unit="ms").dt.strftime("%Y") + "Q"
                       + ((pl.from_epoch("t_senal", time_unit="ms").dt.month() - 1) // 3 + 1).cast(pl.Utf8))
    return v


def mascara(df: pl.DataFrame, filtros: list[dict]) -> np.ndarray:
    ok = np.ones(df.height, dtype=bool)
    for f in filtros:
        x = df[f["var"]].cast(pl.Float64).to_numpy()
        if f["excluye"] == "Q1":
            ok &= ~(x < f["corte"])          # los NaN pasan (no hay dato → no se filtra)
        else:
            ok &= ~(x > f["corte"])
    return ok


def elegir(train: pl.DataFrame) -> list[dict]:
    r = train["r"].to_numpy()
    cand = []
    for var in VARS:
        x = train[var].cast(pl.Float64).to_numpy()
        q1, q4 = np.nanquantile(x, 0.2), np.nanquantile(x, 0.8)
        cand += [{"var": var, "excluye": "Q1", "corte": float(q1)}, {"var": var, "excluye": "Q5", "corte": float(q4)}]
    elegidos: list[dict] = []
    base = r.mean()
    for _ in range(MAX_FILTROS):
        mejor = None
        for c in cand:
            if any(e["var"] == c["var"] for e in elegidos):
                continue
            m = mascara(train, elegidos + [c])
            if m.mean() < RETENCION_MIN or m.sum() < 500:
                continue
            e = r[m].mean()
            if mejor is None or e > mejor[0]:
                mejor = (e, c)
        if mejor is None or mejor[0] - base < MEJORA_MIN:
            break
        elegidos.append(mejor[1])
        base = mejor[0]
    return elegidos


def resumen(df: pl.DataFrame, m: np.ndarray) -> dict:
    r, mfe = df["r"].to_numpy()[m], df["mfe_r"].to_numpy()[m]
    return {"patas": int(m.sum()), "retencion": float(m.mean()), "expectativa_2R": float(r.mean()),
            "win_rate_2R": float((r > 0).mean()), "win_rate_1R": float((mfe >= 1).mean()),
            "expectativa_1R_aprox": float((mfe >= 1).mean() * 1 - (mfe < 1).mean())}


def main() -> None:
    v = cargar()
    tr, te = v.filter(pl.col("trim") < "2025Q1"), v.filter(pl.col("trim") >= "2025Q1")
    f_est = elegir(tr)
    out = {"estatico": {"filtros": f_est, "train_sin": resumen(tr, np.ones(tr.height, bool)), "train_con": resumen(tr, mascara(tr, f_est)),
                        "test_sin": resumen(te, np.ones(te.height, bool)), "test_con": resumen(te, mascara(te, f_est))}}
    # walk-forward trimestral
    wf, oos = [], []
    for q in sorted(te["trim"].unique().to_list()):
        trq, teq = v.filter(pl.col("trim") < q), v.filter(pl.col("trim") == q)
        fq = elegir(trq)
        m = mascara(teq, fq)
        wf.append({"trimestre": q, "filtros": [f"{f['var']} sin {f['excluye']} ({f['corte']:.2f})" for f in fq],
                   "sin": resumen(teq, np.ones(teq.height, bool)), "con": resumen(teq, m)})
        oos.append(teq.filter(pl.Series(m)))
    oos = pl.concat(oos)
    out["walk_forward"] = {"trimestres": wf, "oos_con": resumen(oos, np.ones(oos.height, bool))}
    (RAIZ / "reports" / "f6" / "filtros.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("FILTROS (entrenados en 2023–2024):")
    for f in f_est:
        print(f"  excluir {f['excluye']} de {f['var']} (corte {f['corte']:.3f})")
    for k in ("train_sin", "train_con", "test_sin", "test_con"):
        x = out["estatico"][k]
        print(f"  {k:9s} patas {x['patas']:6d} ({x['retencion']:.0%}) · exp 2R {x['expectativa_2R']:+.3f} · WR 2R {x['win_rate_2R']:.1%} · WR 1R {x['win_rate_1R']:.1%} · exp 1R {x['expectativa_1R_aprox']:+.3f}")
    print("WALK-FORWARD trimestral (fuera de muestra):")
    for w in wf:
        print(f"  {w['trimestre']}: sin {w['sin']['expectativa_2R']:+.3f} → con {w['con']['expectativa_2R']:+.3f} ({w['con']['retencion']:.0%}) · {'; '.join(w['filtros'])}")
    x = out["walk_forward"]["oos_con"]
    print(f"  OOS concatenado: patas {x['patas']} · exp 2R {x['expectativa_2R']:+.3f} · WR 2R {x['win_rate_2R']:.1%} · WR 1R {x['win_rate_1R']:.1%}")


if __name__ == "__main__":
    main()
