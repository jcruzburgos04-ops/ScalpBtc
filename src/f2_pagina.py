"""F2 · Arma reports/f2/revision.html (página de revisión) a partir de la plantilla y de reports/f2/casos.json.
Los campos internos (_gn, _xg, _dist5m_atr) no se publican para no sesgar las respuestas."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "reports" / "f2"
casos = [{k: v for k, v in c.items() if not k.startswith("_")} for c in json.loads((D / "casos.json").read_text())]
html = (D / "revision_plantilla.html").read_text().replace("__CASOS__", json.dumps(casos, separators=(",", ":")))
(D / "revision.html").write_text(html)
print(len(casos), "casos →", D / "revision.html")
