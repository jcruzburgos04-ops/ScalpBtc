"""F3 · Arma reports/f3/auditoria/auditoria.html con el estilo de la página de revisión de F2 y los 20 trades."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "reports"
plantilla = (R / "f2" / "revision_plantilla.html").read_text()
head = plantilla[:plantilla.index("</style>") + len("</style>")]  # título, fuentes y tokens compartidos
head = head.replace("<title>Revisión de señales XO·ASH</title>", "<title>Auditoría del motor F3</title>")
cuerpo = (R / "f3" / "auditoria_cuerpo.html").read_text()
import sys
mini = "--mini" in sys.argv
carpeta = R / "f3" / ("auditoria2" if mini else "auditoria")
casos = json.loads((carpeta / "casos.json").read_text())
if mini:
    head = head.replace("<title>Auditoría del motor F3</title>", "<title>Reauditoría del motor F3</title>")
    cuerpo = cuerpo.replace("<h1>Auditoría del motor F3</h1>", "<h1>Reauditoría del motor F3</h1>")
    cuerpo = cuerpo.replace("0 / 20 revisados", f"0 / {len(casos)} revisados")
    i = cuerpo.index('<p class="sub">'); j = cuerpo.index("</p>", i)
    cuerpo = cuerpo[:i] + '<p class="sub">Los cambios que pediste, aplicados: SL por last price resuelto al segundo (sin mark ni nada sintético) y cierre por invalidación por pata, con 30 minutos reales, el precio a menos de 0,5 R del fill, al menos 7 cruces del fill y al menos 3 cruces del ASH. Incluye t06 y t08 de la auditoría anterior. El TP sigue provisorio en 2R. Horas en ART.</p>' + cuerpo[j + 4:]
(carpeta / ("reauditoria.html" if mini else "auditoria.html")).write_text(head + "\n" + cuerpo.replace("__CASOS__", json.dumps(casos, separators=(",", ":"))))
print(len(casos), "trades")
