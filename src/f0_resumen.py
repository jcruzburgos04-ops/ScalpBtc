"""F0 · Resume reports/f0/integridad/*.json en reports/f0/integridad.md."""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INTEG = RAIZ / "reports" / "f0" / "integridad"


def faltan(d: dict) -> str:
    f = d.get("faltantes_por_dia", {})
    if not f:
        return "0"
    tot = sum(f.values())
    peor = sorted(f.items(), key=lambda x: -x[1])[:3]
    return f"{tot} ({', '.join(f'{k}: {v}' for k, v in peor)})"


def main() -> None:
    meses = sorted(INTEG.glob("*.json"))
    l = ["# F0 · Integridad por mes", "",
         "Minutos faltantes (klines / mark / index / premium) · duplicados · desacople mark vs last · "
         "velas 1m reconstruidas desde aggTrades vs oficiales · metrics 5m.", "",
         "| Mes | klines falt. | mark falt. | index falt. | premium falt. | dup. | mark−last máx % | min >0,5 % | "
         "H/L/C distinto | rachas borde | rachas resid. | resid. BTC | aggTrades fuente | filas dup. descartadas | "
         "agg_id faltantes (mes / vs mes ant.) | saltos trade_id | metrics saltos≠5m | liq COIN-M días |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    resid_top, huecos, max_prev = [], [], None
    for f in meses:
        d = json.loads(f.read_text())
        r = d.get("reconstruccion_1m", {})
        dup = sum(d.get(k, {}).get("duplicados", 0) for k in ("klines_1m", "mark_1m", "index_1m", "premium_1m"))
        des = d.get("mark_1m", {}).get("desacople", {})
        i = d.get("ids", {})
        vs_ant = i["min_id"] - max_prev - 1 if max_prev is not None and "min_id" in i else ""
        max_prev = i.get("max_id")
        # ids faltantes dentro del mes = rango de ids − ids distintos presentes
        falt_mes = i.get("ids_faltantes", i["max_id"] - i["min_id"] + 1 - (i["n"] - i.get("ids_duplicados", 0))) if i else ""
        huecos += [(h["ids"], h) for h in i.get("huecos", [])]
        l.append(f"| {f.stem} | {faltan(d.get('klines_1m', {}))} | {faltan(d.get('mark_1m', {}))} | "
                 f"{faltan(d.get('index_1m', {}))} | {faltan(d.get('premium_1m', {}))} | {dup} | "
                 f"{des.get('max_pct', '')} | {des.get('min_>0.5%', '')} | {r.get('minutos_high_low_close_distinto', '')} | "
                 f"{r.get('rachas_corrimiento_borde', '')} | {r.get('rachas_residuales', '')} | "
                 f"{r.get('residual_total_btc', 0):.3f} | {i.get('fuente', 'monthly')} | "
                 f"{i.get('filas_duplicadas_descartadas', i.get('ids_duplicados', ''))} | {falt_mes} / {vs_ant} | "
                 f"{i.get('saltos_trade_id', '')} | "
                 f"{d.get('metrics_5m', {}).get('saltos_distintos_de_5m', '')} | {d.get('liq_coinm', {}).get('dias', '')} |")
        for x in r.get("residuales", []):
            x["dv_btc"], x["dn"] = float(x["dv_btc"]), int(x["dn"])
            resid_top.append((abs(x["dv_btc"]), x))
    l += ["", "## Residuales más grandes (volumen que no se explica por corrimiento de borde)", "",
          "| Desde (UTC) | Minutos | Δ volumen aggTrades − kline (BTC) | Δ trades |", "|---|---|---|---|"]
    for _, x in sorted(resid_top, key=lambda t: -t[0])[:25]:
        l.append(f"| {x['desde_utc']} | {x['minutos']} | {x['dv_btc']:+.3f} | {x['dn']:+d} |")
    l += ["", "## Huecos de agg_trade_id más grandes (trades que no están en el archivo de Binance)", "",
          "| ids faltantes | último trade antes (UTC) | primer trade después (UTC) |", "|---|---|---|"]
    for _, h in sorted(huecos, key=lambda t: -t[0])[:15]:
        l.append(f"| {h['ids']} | {h['desde_utc']} | {h['hasta_utc']} |")
    (RAIZ / "reports" / "f0" / "integridad.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l[:8 + len(meses)]))


if __name__ == "__main__":
    main()
