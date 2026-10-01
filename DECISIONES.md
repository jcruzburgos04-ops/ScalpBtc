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

## Calibración de la señal (F2)
- [2026-09-30] CONFIRMADA (Juan: "avancemos con la propuesta simple") · Juan no operó en 2023–2024 y no puede ver
  ese período en TV gratis, así que no hay marcas propias. Método: en vez de marcar desde cero, Juan revisa ~40 señales generadas por el código en 2023–2024,
  dibujadas con sus indicadores, y responde "la tomaría / no la tomaría" (y dónde pondría el SL). Con eso se
  ajustan los umbrales de "próximo a ponerse verde" / "por cruzarse". Alternativa sin Juan: fijar a priori 3–4
  variantes objetivas de la señal y elegir entre ellas solo con 2023–2024.
- [2026-09-30] AVISO · F2 arrancó con F1 todavía sin validar contra TV (Juan pidió avanzar). Si la paridad de F1 muestra
  diferencias, se corrigen los indicadores, se regeneran las señales y se revisan las respuestas afectadas.
- [2026-09-30] SUPUESTO · Señal inicial para la revisión (senales.py): ASH 1m rojo con brecha normalizada |gn| ≤ 0,5 y
  cerrándose; precio sobre las dos XO con EMA11 < EMA25, |EMA11−EMA25|/ATR ≤ 1,0 y cerrándose; primera vela en que se
  cumplen ambas; solo en la ventana. Umbrales amplios a propósito: los definitivos salen de las respuestas de Juan.
- [2026-09-30] CONFIRMADA · Filtros de la ronda 1 sumados a la señal (senales.py): ubicación ≤ +1σ del VWAP de sesión
  a favor del trade (Z_MAX = 1,0) y ≤ 3 cruces del ASH de 1m en las últimas 30 velas (CRUCES_MAX = 3).
- [2026-10-01] RESULTADO · La ronda 2 NO valida los filtros (descartarían 6 de 16 sí, dejarían pasar 3 de 5 no).
- [2026-10-01] CONFIRMADA (Juan) · **F2 cerrada.** Se sacan ubicación y rango como filtros duros; congelar la señal base (ASH + XO,
  A = 0,5, B = 1,0) y el tipo (d ≤ 1 ATR 5m); registrar ubicación en el VWAP, cruces del ASH, RVOL, barrida,
  alineación de 5m y niveles cercanos como variables de contexto de cada trade, y medir con resultados (F4–F6,
  walk-forward en 2025–2026) cuáles mejoran la expectativa.
- [2026-10-01] CONFIRMADA · No hay tope de trades por sesión (Juan busca hasta ~7 por sesión cuando el mercado lo da).
  La cantidad de trades por sesión es un RESULTADO a reportar (§9), no una regla. Con los filtros hay ~22 señales por
  sesión (mediana 2023–2024); los trades efectivos salen de aplicar R ≥ 2, una posición a la vez y máx. 4 patas.

## Trader de referencia como guía (2026-10-01)
- [2026-10-01] CONFIRMADA · Juan pide guiarse más por los trades del trader de referencia (quiere aprender de un
  trader mejor). Sus setups (reversión edge-to-edge y mean-to-edge sobre las bandas del dVWAP, momentum loss,
  reclaim/failed reclaim, barrida con volumen) entran como **estrategia B**, al lado de la señal de Juan (estrategia A).
- [2026-10-01] CONFIRMADA · Estrategia B: calibración con los trades del trader (feb–may 2026); test en 2023–2025 y
  jun 2026 (fuera de muestra); reserva jul–sep 2026 cerrada.
- [2026-10-01] SUPUESTO · B1 (reversión desde el extremo): empujón con RVOL ≥ 1,5 hasta el nivel (variantes ±2σ,
  ±1σ, dVAH/dVAL), sin continuación en ≤ 10 velas, vela de señal que cierra adentro y de signo contrario; SL extremo
  ± 0,25 ATR; TP = VWAP de sesión; una pata; sin los primeros 30 min del día. R mínimo 1 (y 2 como variante).

## Auditoría F3 (2026-10-01)
- [2026-10-01] CONFIRMADA · SL por **last price**, resuelto al segundo con aggTrades, sin mark ni trayectorias
  sintéticas (reemplaza "se dispara por MARK PRICE" del §1). El mark queda solo como variante de sensibilidad.
- [2026-10-01] CONFIRMADA · Cierre por invalidación redefinido, POR PATA: al cierre de la primera vela con 30 min
  reales desde el fill de esa pata, si |close − fill| ≤ 0,5 R, el precio cruzó el fill ≥ 7 veces y el ASH de 1m
  cruzó ≥ 3 veces desde la entrada → se cierra esa pata. Las demás patas siguen hasta su SL/TP (reemplaza "cierra
  todas las patas" del §5.1).
- [2026-10-01] CONFIRMADA · **F3 cerrada**: reauditoría 12/12 correcta (Juan).
