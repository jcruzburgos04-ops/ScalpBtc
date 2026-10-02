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

## Estrategia B · mejoras (2026-10-01)
- [2026-10-01] CONFIRMADA · Juan aprueba probar las tres mejoras (absorción, scratch/manejo, meta del día) con
  selección estática y walk-forward, sin tocar la reserva.
- [2026-10-01] CONFIRMADA · Se adopta **breakeven a +0,5 R** como manejo de B1 (dVAL/dVAH, R ≥ 2): único componente
  que mejora en entrenamiento y en test y que el walk-forward elige solo. Filtros de absorción y de cruces del VWAP: descartados en
  la dirección hipotética; "pocos cruces del VWAP" queda como hipótesis a validar aparte.
- [2026-10-01] CONFIRMADA · Juan pide validar "pocos cruces del VWAP en el día". Chequeo en entrenamiento (2023–2024,
  dVAL/dVAH, R ≥ 2, breakeven 0,5 R): el efecto está confundido con la hora. Los cruces se acumulan durante el día,
  0–4 h UTC rinde +0,141 y el resto ≈ +0,07; dentro de cada tramo de 4 h, pocos vs muchos cruces no tiene un signo consistente.
- [2026-10-01] SUPUESTO (pre-registro, ANTES de mirar 2022) · Validación en un tramo nunca usado por B: **2022**
  (hasta ahora solo calentamiento; B usa solo niveles intradía, así que no necesita calentamiento largo).
  Desvío del §1 documentado. Configuración congelada: B1 dVAL/dVAH, R ≥ 2, 1 pata, breakeven 0,5 R.
  H0: expectativa total de 2022 > 0.
  H1: cruces_vwap_dia ≤ 16 (p40 de 2023–2024) rinde más que > 16, global y dentro de cada tramo de 4 h.
  H2: señales 00:30–04:00 UTC rinden más que el resto de la ventana.
  Se reporta la diferencia con IC 95 % por bootstrap. Ninguna regla se ajusta después de ver 2022.
- [2026-10-01] CONFIRMADA (resultado de la validación) · Filtro de cruces del VWAP DESCARTADO (no se confirma en 2022 y
  en el entrenamiento es un efecto de la hora). El filtro horario de Asia también se descarta. B1 queda: dVAL/dVAH, R ≥ 2,
  1 pata, breakeven 0,5 R, sin filtros de contexto. 2022 ya está usado para B: no sirve más como tramo fresco.

## Trades del trader · septiembre 2026 (2026-10-01)
- [2026-10-01] CONFIRMADA · Juan envía los trades de septiembre 2026 del trader de referencia (camino 1): se **libera
  la reserva jul–sep 2026**. Esos meses pasan a calibrar o estudiar sus trades. La confirmación final de F8 pasa
  a ser **oct–dic 2026** a medida que transcurre (datos que nadie vio). Reemplaza la reserva del §6c.
- [2026-10-01] PENDIENTE · Zona horaria del eje de sus capturas (para ubicar cada entrada en UTC).
- [2026-10-01] CONFIRMADA (por datos) · Capturas del trader en UTC+2. Líneas de su gráfico (Juan): rojo = VWAP semanal,
  blanco = VWAP de sesión, amarillo = rolling VWAP.
- [2026-10-01] SUPUESTO · Se excluyen del estudio la captura del 1-oct (nueva reserva) y las posiciones swing.
  Las entradas se leen con la última vela de 1m cerrada antes del minuto de entrada. PENDIENTE: Juan confirma las
  ubicaciones en la página de revisión.
- [2026-10-01] PENDIENTE · B2 variante V10 (σ ±1 en contra + volumen 15 min ≥ 1,5× + absorción ≥ 1), SL ext10 ± 0,25 ATR,
  TP VWAP de sesión, breakeven 0,5 R. Juan revisa 14 casos dibujados antes de medir resultados en 2023–2025.
  "Volume suite" y las velas ampliadas de TV se aproximan con delta por vela, velas de 1 s/10 s y burbujas de órdenes
  grandes (supuesto: no tenemos la configuración exacta de su indicador).

## B2 final (2026-10-02)
- [2026-10-02] CONFIRMADA · Juan aprueba congelar B2 + EMA 200 de 45m (`src/b2_final.py`). Salida elegida en calibración
  (jul–sep 2026) con filtro R ≥ 2: SL extremo de 10 velas ± 0,25 ATR, TP VWAP de sesión, breakeven a +1R, una pata,
  sin comisiones (Variational). Test 2023–2025: 2 619 trades, gana 13 %, +0,064 R [IC 95 % −0,011, +0,148].
  No se modifica más; se mide en la reserva oct–dic 2026 a medida que se publiquen los datos.
- [2026-10-02] CONFIRMADA · Juan: win rate mínimo operable 50 %.
- [2026-10-02] CONFIRMADA (congelada) · Estrategia A + EMA 200 de 45m + salida TP 3R con 50 % cobrado en +1R y breakeven del resto
  (elegida en calibración 2023–24 con gana ≥ 50 %): test 2025-01..2026-06 +0,080 R [+0,052, +0,113], gana 52 %.
  Advertencia: la dirección de la señal A no supera al azar en el control; la ventaja es del SL en el swing, la
  tendencia de 45m y el manejo.
- [2026-10-02] CONFIRMADA · Los recordatorios de oct/nov/dic (5-nov, 5-dic, 6-ene) miden B2 final y A congelada.
- [2026-10-02] SUPUESTO · Liquidation Bands de Leviathan (código protegido): banda = base × (1 ± 1/L), L = 100/75/50/25
  (1 %, 1,33 %, 2 %, 4 %), base VWAP de sesión o EMA 200 de 1m. PENDIENTE: Juan confirma base, largo de la EMA y si
  descuenta margen de mantenimiento leyendo la configuración en su TradingView.
- [2026-10-02] CONFIRMADA · Se suma a la medición de la reserva (oct–dic 2026) la variante A + EMA 45m + TP en el nivel
  opuesto SIN parcial (`python src/a_tp_nivel.py AAAA-MM AAAA-MM`; test 2025–jun 2026 +0,136 R, gana 23 %). Solo para
  medir; no es la versión operable (gana < 50 %).
- [2026-10-02] PENDIENTE · Trendlines v2 ("aceitadas", `rupturas_v2` en `src/trendlines.py`): misma línea (dos últimos
  pivots confirmados, una por lado) más (1) línea limpia: si un cierre ya la cruzó entre el pivot 1 y la confirmación
  del pivot 2, no da señal; (2) vence a 2× la distancia entre pivots después del pivot 2; (3) toques = episodios con la
  mecha a ≤ 0,15 ATR de la línea (informativo). Ejemplos en `reports/trendlines/ejemplos_v2.png`. Juan valida el trazado.
- [2026-10-02] PENDIENTE · Trendlines con volumen (Juan: "cuando rompe debe ser con volumen"): la vela de 1m que cierra
  del otro lado de la línea tiene RVOL (volumen / SMA 20, el del ASH) ≥ 1,5. Variantes a calibrar: 1,5 / 2,5 y
  además delta taker de la vela a favor. Ejemplos con panel de volumen en `reports/trendlines/ejemplos_v2.png`.
- [2026-10-02] CONFIRMADA · Trazado de trendlines v2 aprobado por Juan (pivots de 10). RVOL 2,5 descartado ("no lo
  uses"). Confirmaciones de volumen a probar: delta a favor (compras/ventas agresivas a favor) o liquidación de los
  contrarios (proxy de `src/liq_proxy.py`). SUPUESTO: delta a favor = ≥ 0,2 en la vela que rompe; liquidación contraria
  = proxy encendido en la vela de ruptura o las 2 anteriores.
