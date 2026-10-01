"""F3 · Arma reports/f3/auditoria/auditoria.html con el estilo de la página de revisión de F2 y los 20 trades."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "reports"
plantilla = (R / "f2" / "revision_plantilla.html").read_text()
head = plantilla[:plantilla.index("</style>") + len("</style>")]  # título, fuentes y tokens compartidos
head = head.replace("<title>Revisión de señales XO·ASH</title>", "<title>Auditoría del motor F3</title>")
cuerpo = (R / "f3" / "auditoria_cuerpo.html").read_text()
casos = json.loads((R / "f3" / "auditoria" / "casos.json").read_text())
(R / "f3" / "auditoria" / "auditoria.html").write_text(head + "\n" + cuerpo.replace("__CASOS__", json.dumps(casos, separators=(",", ":"))))
print(len(casos), "trades")
