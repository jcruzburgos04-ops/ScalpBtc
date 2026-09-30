# Decisiones

Formato: `[fecha] ESTADO · tema — detalle`. Estados: CONFIRMADA / PENDIENTE.

## Confirmadas (2026-09-30, ver CLAUDE.md §1 y §11)

Entrada al cierre de la vela · la posición corre hasta SL/TP aunque pase la ventana · una posición a la vez con
ampliaciones (máx. 4 patas, 1 % c/u, SL independientes, R ≥ 2 por pata) · 5m en formación · riesgo 1 % ·
SL en el swing más reciente de 1m · apalancamiento solo afecta margen · calibración 2023–2024, investigación
2025–2026 con walk-forward · niveles extra incluidos · invalidación a 30 min, cierra todas las patas, se testea
con y sin · variantes de calendario A–D.

## Pendientes

- [2026-09-30] PENDIENTE · Tramo de reserva jul–sep 2026 sin mirar hasta F8 (§6c).
- [2026-09-30] PENDIENTE · Definición del swing del SL y buffer (se resuelve con las marcas, §4.1).
- [2026-09-30] PENDIENTE · Invalidación: x y m (se calibran con las marcas, §5.1).
- [2026-09-30] CONFIRMADA · Liquidaciones: solo fuentes **gratuitas** y con **datos reales** (Juan).
- [2026-09-30] PENDIENTE · Liquidaciones: cuál de las fuentes gratuitas reales se usa y cómo (ver BITACORA 2026-09-30).
  Ninguna fuente gratuita da liquidaciones intradía completas de BTCUSDT USD-M en 2025–2026.
- [2026-09-30] CONFIRMADA · Almacenamiento: "optimizar y guardar donde se pueda" (Juan). Se guarda solo lo
  procesado, comprimido, en el propio repo (`data/proc/`, parquet zstd). Los zips crudos no se guardan (se
  pueden volver a bajar gratis de Binance).
- [2026-09-30] SUPUESTO (a confirmar) · Órdenes grandes: se guardan solo las órdenes reconstruidas (ms, lado) con
  nocional ≥ 100.000 USD (~p95 en mar-2025). El umbral de "grande" (§6b, percentil móvil) tiene que caer por
  encima de ese piso; si hiciera falta uno más bajo, se reprocesa desde Binance.
- [2026-09-30] PENDIENTE · Klines oficiales rotas (308 min en 11 tramos, velas planas con volumen 0). Recomendación:
  usar para indicadores y motor velas 1m **reconstruidas desde aggTrades** en esos minutos (son los trades reales) y
  verificar en F1 qué muestra TradingView en esos tramos (si TV también las muestra planas, sus EMAs/VWAP difieren ahí).
- [2026-09-30] PENDIENTE · Días sin mark price (2022-07-31, 2022-10-02, 2023-02-24, 2026-06-29). Opciones: no operar
  esos días, o reconstruir el mark con last + premium/index cuando existan. 2026-06-29 cae en 2025–2026.
