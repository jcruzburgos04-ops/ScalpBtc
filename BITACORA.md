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
- Barras de 1s con codificación delta (precios enteros en 0,01 USDT, cantidades en 0,001 BTC): ~30 MB/mes sin
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

### Bug corregido (mismo día)
- **Tick de BTCUSDT**: en 2022 era **0,01**, no 0,1. La primera versión codificaba en 0,1 y redondeaba los precios
  de 2022 (se vio como 5.234 minutos con H/L/C distinto en 2022-01). Se pasó la grilla a 0,01 para todo el
  período y el control de "fuera de grilla" ahora aborta el proceso en vez de solo registrarlo. Se rehízo todo.
- Polars divide un entero por un escalar multiplicando por el recíproco (error de 1 ulp: 4628920/100 ≠ 46289.2).
  `datos.py` decodifica con la división de pyarrow (IEEE exacta) para que las comparaciones exactas funcionen.

### Descarga completa 2022-01 → 2026-09 (57 meses, 2,0 GB en `data/proc/`)
- **Archivos mensuales de aggTrades rotos en Binance**: 2022-08, 2022-09, 2022-10, 2022-11 y 2023-05 vienen con
  días enteros faltantes (p. ej. 2022-09 no tiene el 09-01 ni el 09-10) y 2022-09 además trae 4,3 M de filas
  duplicadas exactas. Los archivos diarios de esos meses están completos. El pipeline ahora descarta
  duplicados exactos siempre y, si el mensual tiene huecos o duplicados, lo rehace con los diarios.
- Hueco real (también en los diarios): 2022-09-06 17:14–17:20 UTC, ~31,6 k aggTrades que no están en el archivo.
- **Klines oficiales rotas**: 308 minutos en 11 tramos con velas planas (O=H=L=C, volumen 0, count 0) mientras
  aggTrades tiene los trades reales. Los más largos: 2023-11-10 15:07 (99 min), 2024-10-28 20:00 (74 min),
  2022-05-28 16:40 (35 min), 2022-05-01 22:26 (29 min), 2023-09-12 08:34 (19 min). Ver DECISIONES.
- Mark/index/premium: días enteros faltantes sueltos (mark: 2022-07-31, 2022-10-02, 2023-02-24, 2026-06-29;
  index: además 2022-04-27, varios de 2022-07, 2023-02-13, 2023-04-07/08). Afecta el disparo del SL por mark en esos días.
- Desde 2025-08 los saltos de trade_id pasan de ~10–20 k/mes a 130–340 k/mes (trades que no están en aggTrades,
  probablemente un tipo de orden nuevo de Binance). Los volúmenes siguen cerrando contra las klines. A vigilar.
- Incidentes de la descarga (reintentos de red, un `quote_volume` "0.00000000" que rompía la inferencia de tipos,
  archivo temporal de DuckDB corrupto con dos procesos en paralelo) corregidos en el código.
