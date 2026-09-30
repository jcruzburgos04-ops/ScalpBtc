# F0 · Cobertura de data.binance.vision (BTCUSDT USD-M) — listado del 2026-09-30

Rango pedido: 2022-01-01 → 2026-09-30 (monthly: hasta el último mes cerrado; daily: hasta ayer). Tamaño = zips comprimidos desde 2022-01.

| Dataset | Frec. | Primero | Último | Disponibles/esperados (desde 2022-01) | Faltantes | Sin .CHECKSUM | GB zip |
|---|---|---|---|---|---|---|---|
| klines 1m | monthly | 2020-01 | 2026-08 | 56/56 | — | 0 | 0.10 |
| klines 1m | daily | 2019-12-31 | 2026-09-29 | 1733/1733 | — | 0 | 0.11 |
| aggTrades | monthly | 2020-01 | 2026-08 | 56/56 | — | 0 | 31.08 |
| aggTrades | daily | 2019-12-31 | 2026-09-29 | 1733/1733 | — | 0 | 31.64 |
| markPriceKlines 1m | monthly | 2020-01 | 2026-08 | 56/56 | — | 0 | 0.06 |
| markPriceKlines 1m | daily | 2019-12-23 | 2026-09-29 | 1733/1733 | — | 0 | 0.06 |
| indexPriceKlines 1m | monthly | 2020-01 | 2026-08 | 56/56 | — | 0 | 0.06 |
| indexPriceKlines 1m | daily | 2019-12-23 | 2026-09-29 | 1721/1733 | 2022-10-30, 2022-11-01, 2022-11-06, 2022-11-16, 2023-03-20, 2023-03-23, 2023-03-31, 2023-05-10 … (+2 rangos) | 0 | 0.07 |
| premiumIndexKlines 1m | monthly | 2020-01 | 2026-08 | 56/56 | — | 0 | 0.05 |
| premiumIndexKlines 1m | daily | 2019-12-24 | 2026-09-29 | 1733/1733 | — | 0 | 0.05 |
| metrics | monthly | — | — | 0/56 | 2022-01→2026-08 | 0 | 0.00 |
| metrics | daily | 2020-09-01 | 2026-09-29 | 1733/1733 | — | 0 | 0.02 |
| liquidationSnapshot | monthly | — | — | 0/56 | 2022-01→2026-08 | 0 | 0.00 |
| liquidationSnapshot | daily | — | — | 0/1733 | 2022-01-01→2026-09-29 | 0 | 0.00 |

## Lectura

- **klines 1m, markPriceKlines 1m, premiumIndexKlines 1m, metrics**: cobertura completa 2022-01 → 2026-09-29.
  Los monthly cubren hasta 2026-08; septiembre 2026 sale de los daily.
- **indexPriceKlines 1m**: monthly completo; en daily faltan 12 días sueltos (2022-10 → 2023-05). Se usan los monthly, así que no afecta.
- **aggTrades**: completo. ~31 GB comprimidos desde 2022-01 (el descomprimido es varias veces eso).
- **metrics**: solo existe en daily (no hay monthly), completo desde 2020-09.
- **liquidationSnapshot USD-M: NO EXISTE** para ningún símbolo en `futures/um`. Solo hay en COIN-M:
  `BTCUSD_PERP` (contrato inverso, otro libro), 472 días entre **2023-06-25 y 2024-10-14**. No cubre 2025–2026.
  → Para 2025–2026 hace falta una alternativa (§6b): proveedor pago, agregador o proxy propio. Consultar a Juan.
- Acceso: `data.binance.vision` directo da 403 desde este entorno; el endpoint S3
  (`s3-ap-northeast-1.amazonaws.com/data.binance.vision`) sí funciona para listar y descargar.
