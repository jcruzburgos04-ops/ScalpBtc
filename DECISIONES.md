# Decisiones

Formato: `[fecha] ESTADO · tema — detalle`. Estados: CONFIRMADA / PENDIENTE.

## Confirmadas (2026-09-30, ver CLAUDE.md §1 y §11)

Entrada al cierre de la vela · la posición corre hasta SL/TP aunque pase la ventana · una posición a la vez con
ampliaciones (máx. 4 patas, 1 % c/u, SL independientes, R ≥ 2 por pata) · 5m en formación · riesgo 1 % ·
SL en el swing más reciente de 1m · apalancamiento solo afecta margen · calibración 2023–2024, investigación
2025–2026 con walk-forward · niveles extra incluidos · invalidación a 30 min, cierra todas las patas, se testea
con y sin · variantes de calendario A–D.

## Pendientes

- [2026-09-30] CONFIRMADA · Tramo de reserva **jul–sep 2026** sin mirar hasta F8 (§6c). `datos.sin_reserva()` y
  `indicadores.cargar()` lo sacan por defecto. Aviso (regla 4): antes de aprobarse la reserva, el control de
  integridad de F0 recorrió esos meses (huecos, duplicados, volumen vs klines; nada de precios, señales ni resultados)
  y la caché de indicadores se calculó sobre todo el historial (necesario para el calentamiento de octubre).
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
- [2026-09-30] CONFIRMADA · Klines oficiales rotas: se usan las velas 1m **reconstruidas desde aggTrades**
  (`datos.leer_velas_1m()`). 192 minutos reemplazados. Otros 116 minutos en 6 tramos no tienen trades en ninguna
  fuente (pausas del exchange): quedan planos.
- [2026-09-30] CONFIRMADA · Días sin mark price: se **reconstruye** el mark (last + base interpolada,
  `datos.leer_mark_1m()`, validación en `reports/f0/reparaciones.md`). Los trades en minutos reconstruidos se marcan.
- [2026-09-30] CONFIRMADA · Liquidaciones: se usa Tardis.dev gratis (1.er día de cada mes, BTCUSDT USD-M) además del
  COIN-M 2023–2024 de Binance. `src/f0_tardis.py` listo; el host todavía está bloqueado en el contenedor.
- [2026-09-30] CONFIRMADA · **F0 aprobada por Juan.**

## F1 · supuestos (a confirmar en la validación de F1)
- [2026-09-30] CONFIRMADA · Se usa la versión **vivo** (datos reales reconstruidos, lo que Juan ve en tiempo real).
  El backtest es sobre historia, no en vivo.
- [2026-09-30] CONFIRMADA · Tolerancias de F1: ±0,1 USD en precios y niveles, ±0,01 ASH, ±0,001 RVOL.
- [2026-09-30] CONFIRMADA · La validación de F1 se hace con velas recientes (TV gratis solo muestra unos días de 1m),
  de 2026-10-01 en adelante (fuera de la reserva), anotadas en vivo por Juan en `tests/paridad_tv.csv`.
- [2026-09-30] (antes SUPUESTO) · Lo que en Pine sale de `request.security(..., lookahead_off)` (7D/30D/90D/365D, pwVWAP,
  m/pm/pq/y, MNDAY, ASH/EMAs de 5m) se calcula en dos versiones: **vivo** (vela mayor en formación, lo que se ve en
  tiempo real, §3.3) e **hist** (última vela mayor cerrada, lo que muestra TV en el historial). Para la estrategia se
  propone usar **vivo**, que es lo que Juan ve al operar.
- [2026-09-30] SUPUESTO · XO 11/25 (confirmado por Juan) aunque el default del .pine es 12/25.
- [2026-09-30] SUPUESTO · Rolling 24h: velas de 1m con open_time > t − 24h, incluida la vela actual (1440 velas),
  como en el .pine (§10). 7D/30D: ventana inclusiva del .pine = vela diaria actual + N anteriores (N+1 velas).
- [2026-09-30] SUPUESTO · El volumen es el de las klines de Binance (base, BTC). Si el feed de TV difiere, las VWAP
  y el RVOL difieren un poco; se ve en la tabla de F1.

## Estudio de etiquetas (F5) · a partir de los trades de referencia
- [2026-09-30] CONFIRMADA · F5 en dos partes: (a) **importancia descriptiva** de cada nivel (reacción vs placebo,
  corrección BH) sobre todo 2025–2026 fuera de la reserva, **sin walk-forward**; (b) walk-forward solo cuando un
  nivel pase a ser una REGLA de la estrategia (filtro de entrada, TP, umbral de tolerancia).
- [2026-09-30] CONFIRMADA · Se catalogan los trades de referencia (fecha, lado, entrada, salida, niveles citados),
  se ubican en nuestros datos y se usan para GENERAR hipótesis. Como salen de feb–may 2026, las hipótesis se miden
  en 2023–2025.
- [2026-09-30] CONFIRMADA · Niveles extra en dos grupos:
  - **Grupo 1 (estudio principal, codificables sin ambigüedad):** EMAs de 4h 13/34/100 (además de la 200 del §8),
    pwVAL (y pwVAH), VWAP anclados a swings, eventos de horario (DO, apertura de futuros, NYO, IB).
  - **Grupo 2 (aparte y con menos peso):** S/R horizontales. Son más visuales que codificables: se prueba solo un
    proxy objetivo (máximos/mínimos de sesiones previas con reacción, números redondos, HVN/LVN) y sus resultados
    se reportan separados, sin mezclarlos con el grupo 1.
