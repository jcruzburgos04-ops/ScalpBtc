"""Estrategia B · página de revisión (misma base visual que las auditorías de F3) con las bandas del VWAP y dVAH/dVAL."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "reports"
plantilla = (R / "f2" / "revision_plantilla.html").read_text()
head = plantilla[:plantilla.index("</style>")] + "[hidden] { display: none !important; }\n</style>"
head = head.replace(
    "<title>Revisión de señales XO·ASH</title>", "<title>Estrategia del trader B1</title>")
c = (R / "f3" / "auditoria_cuerpo.html").read_text()
casos = json.loads((R / "b" / "revision" / "casos.json").read_text())
rep = {
    "<h1>Auditoría del motor F3</h1>": "<h1>Estrategia del trader B1</h1>",
    "0 / 20 revisados": f"0 / {len(casos)} revisados",
    "<legend>¿La salida está bien resuelta?</legend>": "<legend>¿Es el setup del trader y está bien operado?</legend>",
    '<p class="rot">1m · ': '<p class="rot">1m · <span><i style="background:var(--vwap)"></i>VWAP sesión ±1σ ±2σ</span><span><i style="background:var(--lvl)"></i>dVAH / dVAL</span> · ',
}
for a, b in rep.items():
    assert a in c, a
    c = c.replace(a, b)
i = c.index('<p class="sub">'); j = c.index("</p>", i)
c = c[:i] + ('<p class="sub">Reversión desde el extremo, como la describe el trader: empujón con esfuerzo (RVOL ≥ 1,5) hasta dVAL/dVAH '
             'o hasta la banda ±2σ del VWAP de sesión, sin continuación, y entrada cuando una vela vuelve a cerrar adentro. SL más allá '
             'del extremo del empujón (+0,25 ATR) y TP en la media (VWAP de sesión). Los dos primeros son los trades que él publicó el '
             '20-feb-2026. Ventana de calibración feb–may 2026; horas en ART.</p>') + c[j + 4:]
# dibujar las bandas y niveles debajo de las velas
a = '''  const s1 = velasCS(g1);'''
assert a in c
c = c.replace(a, '''  if (c.ov) {
    const est = { "VWAP": [tok("--vwap"), 2, 0], "+1σ": [tok("--vwap"), 1, 2], "−1σ": [tok("--vwap"), 1, 2], "+2σ": [tok("--vwap"), 1, 1], "−2σ": [tok("--vwap"), 1, 1], "dVAH": [tok("--lvl"), 1, 0], "dVAL": [tok("--lvl"), 1, 0] };
    Object.entries(c.ov).forEach(([k, arr]) => { const [col, w, s] = est[k] || [tok("--muted"), 1, 0]; linea(g1, col, w, s).setData(arr.map(x => ({ time: x.t + ART, value: x.v }))); });
  }
  const s1 = velasCS(g1);''')
a = '''const EXPLICA_LAST = {'''
c = c.replace(a, '''const EXPLICA_B = "Short (long espejo): el precio empuja con esfuerzo hasta el nivel extremo y no sigue; la vela de señal no hace un extremo nuevo, cierra de vuelta adentro y es de signo contrario. TP en la media; SL más allá del extremo del empujón.";
const EXPLICA_LAST = {''')
c = c.replace('''(EXPLICA_LAST[c.etiqueta] || "Mismo trade de la auditoría anterior, resuelto con SL por last price (sin mark ni nada sintético).")''',
              '''(EXPLICA_LAST[c.etiqueta] || EXPLICA_B)''')
c = c.replace('''  fila("TP", `${usd(c.tp)} (2R)`);''', '''  fila("TP", `${usd(c.tp)} (${c.etiqueta.startsWith("B1") || c.etiqueta.startsWith("Trade documentado") ? "VWAP de sesión" : "2R"})`);''')
out = R / "b" / "revision" / "revision_b.html"
out.write_text(head + "\n" + c.replace("__CASOS__", json.dumps(casos, separators=(",", ":"))))
print(out)
