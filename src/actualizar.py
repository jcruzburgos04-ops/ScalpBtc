"""Baja los días nuevos del mes en curso (Binance publica cada día al día siguiente), rehace las reparaciones y la
caché de indicadores. Uso: python src/actualizar.py [AAAA-MM]   (default: mes en curso)"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
mes = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
for cmd in (["f0_descarga.py", mes, mes], ["f0_reparar.py"]):
    subprocess.run([sys.executable, str(SRC / cmd[0]), *cmd[1:]], check=True, cwd=SRC)
sys.path.insert(0, str(SRC))
import indicadores  # noqa: E402

indicadores.cargar(recalcular=True)
print("actualizado", mes)
