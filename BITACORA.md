# Bitácora

## 2026-09-30

- Repo inicializado con la estructura de CLAUDE.md §10. `spec/` con los dos .pine originales.
- F0 · cobertura: `src/f0_cobertura.py` lista el bucket (sin descargar). Resultado en `reports/f0/cobertura.md`.
  Hallazgos: todo completo desde 2022-01 salvo **liquidationSnapshot, que no existe para USD-M**
  (solo COIN-M BTCUSD_PERP, 2023-06-25 → 2024-10-14). indexPriceKlines daily con 12 días faltantes; los monthly están completos.
- `data.binance.vision` directo devuelve 403 desde el entorno cloud; se usa el endpoint S3 equivalente.
