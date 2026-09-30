# Bitácora

## 2026-09-30

- Repo inicializado con la estructura de CLAUDE.md §10. `spec/` con los dos .pine originales.
- F0 · cobertura: `src/f0_cobertura.py` lista el bucket (sin descargar). Resultado en `reports/f0/cobertura.md`.
  Hallazgos: todo completo desde 2022-01 salvo **liquidationSnapshot, que no existe para USD-M**
  (solo COIN-M BTCUSD_PERP, 2023-06-25 → 2024-10-14). indexPriceKlines daily con 12 días faltantes; los monthly están completos.
- `data.binance.vision` directo devuelve 403 desde el entorno cloud; se usa el endpoint S3 equivalente.

### F0 · descarga y almacenamiento
- `src/f0_descarga.py`: baja por mes, verifica sha256 contra `.CHECKSUM`, convierte a parquet y borra el crudo.
  `src/datos.py` lee y decodifica.
- Barras de 1s con codificación delta (precios en ticks enteros, cantidades en 0,001 BTC): 43 → 27 MB/mes sin
  pérdida. Esquema en `data/proc/LEEME_bars_1s.txt`.
- **Hallazgo (mar-2025): velas 1m reconstruidas desde aggTrades vs klines oficiales.** Los high/low/close
  coinciden salvo en 214 de 44.640 minutos. Las diferencias de volumen vienen casi todas en **pares de minutos
  contiguos con ±el mismo volumen**: trades en el borde del minuto que aggTrades fecha en el minuto anterior y la
  kline en el siguiente (corrimiento de borde, el total no cambia). Aparte hay un residual real: el
  **2025-03-10 08:21 UTC** tiene +67,4 BTC / +814 trades en aggTrades que la kline oficial no tiene. El resto de los
  residuales son centésimas de BTC. El criterio §2.3 ("OHLC exacto, volumen < 1e-6") no se cumple minuto a minuto
  por el corrimiento de borde; se reporta clasificado (corrimiento vs residual) en `reports/f0/integridad/`.
- aggTrades mar-2025: 0 saltos en agg_trade_id, pero 20.457 saltos en trade_id (trades que no aparecen en
  aggTrades). A investigar si importan.

### Liquidaciones: fuentes gratuitas con datos reales
- Binance público: USD-M no tiene liquidationSnapshot. Solo COIN-M `BTCUSD_PERP`, 2023-06-25 → 2024-10-14
  (se baja a `data/proc/liq_coinm/`).
- Tardis.dev: CSV gratis sin API key **solo el 1.er día de cada mes** (binance-futures, incluye liquidaciones de
  BTCUSDT). Unos 21 días en 2025–2026. El host `datasets.tardis.dev` está bloqueado en este entorno.
- Coinalyze: API gratuita, pero guarda solo 1500–2000 puntos intradía (a 1m, ~1 día). A 1m no sirve para el pasado;
  en diario guarda toda la historia. Host bloqueado en este entorno.
- Ojo: el stream `forceOrder` de Binance (de donde sale todo lo anterior) manda como mucho una liquidación por
  símbolo cada 1000 ms; ninguna fuente pública tiene el total exacto, son muestras reales.
