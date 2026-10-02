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

### Reparaciones (tras aprobación de F0)
- `src/f0_reparar.py`: 192 minutos de klines rotas reemplazados por velas desde aggTrades; 5762 minutos de mark
  reconstruidos (4 días enteros + 2 min). Validación del mark tapando 40 días reales de 2025–2026: error del close
  mediana 2,08 USD, p95 19,3 USD (0,02 %). High/low reconstruidos exceden al real en ~70 % de los minutos
  (mechas del last) → sesgo conservador en el SL. Detalle en `reports/f0/reparaciones.md`.
- 6 tramos sin trades en ninguna fuente (2022-05-01 22:26 29 min, 2022-05-28 16:40 35 min, 2023-09-12 08:34 19 min,
  2024-10-28 16:21 15 min, 2025-08-29 06:19 18 min): pausas del exchange, quedan planos.

## F1 · Réplica de indicadores (2026-09-30)
- `src/indicadores.py` (numba): EMA/RMA/SMA con la semilla de Pine, ASH RSI 16/4 EMA, XO 11/25, RVOL 20, ATR 14,
  VWAP sesión/semana ±σ1/σ2 (hl2, `f_vwap`), perfil diario 24 filas 70 % (dVWAP/dPOC/dVAH/dVAL), rolling 24h
  (rVWAP ± σ), pwVWAP y m/pm (60m), pq e y (diario), 7D/30D/90D/365D (diario, hlc3), DO/WO/MO/YO, PWH/PWL,
  PQH/PQL, MNDAY-H/L, ASH y EMAs de 5m (vivo y cerrada). 2,5 M velas en ~50 s; caché en `data/cache/` (no versionada).
- `tests/test_indicadores.py`: 9 tests contra implementaciones de referencia independientes, todos pasan.
  Prueba de mutación: sacando 60 velas del perfil, 33/33 casos detectados.
- Semilla (§3.2): arrancar la historia en 2022-07 en vez de 2022-01 cambia EMA 25 y ASH en 2023-01-01 < 1e-9.
- Hallazgo del .pine: dVAH/dVAL/dPOC/rVAH/rVAL y todas las etiquetas se calculan SOLO en la última vela
  (`barstate.islast`): en TV no tienen historial en la ventana de datos; para validarlas hay que usar Bar Replay.

### Trades de referencia de otro trader (PDFs de Juan, 2026-09-30)
- 9 reviews (feb–may 2026, BTC 1m, Asia/NYO): estilo **reversión a la media en rango** ("edge to edge": banda
  ±2σ → banda opuesta; "mean to edge": dVWAP → ±1σ/±2σ; "momentum loss"; "first test best test"), con lectura de
  orderflow en Aggr 10s. Niveles que más nombra: dVWAP ("the mean") y sus bandas 1σ/2σ (por lejos), S/R manuales
  (70k, 71.8k…), aVWAP anclados, DO / futures open / NYO / IB (eventos de horario), bandas semanales, dVAL,
  cinta de EMAs. Etiquetas en su gráfico: MDAY-L/H, dVAL, pwVAL, pwVWAP, rVAL, pdVAL, H4 13/34/100 EMA.
- Cruce con nuestra réplica (TW1, 2026-02-20; su gráfico está en UTC+1): entradas long 67 127,32 y 67 135,84 a las
  ~01:26 UTC; nuestro **dVAL = 67 129,0** y VWAP −1σ = 67 121–67 134; salida ~67 311 ≈ dVAH 67 321 / +1σ 67 327.
  Rango 00:30–02:50 UTC entre dVAL y dVAH. Primer control de paridad contra un gráfico de TV: coincide.

## F2 · Calibración de la señal (2026-09-30)
- `src/senales.py`: señal inicial con umbrales amplios → 25 346 señales en la ventana de 2023–2024 (~35/día); solo
  para muestrear. Mediana |gn| del ASH 0,043; mediana |xg| de las XO 0,34 ATR.
- `src/f2_muestra.py`: 40 casos estratificados (3 tramos de |gn| × 3 de |xg|, long/short, continuación/rebote, días
  distintos, 12 de fin de semana). Cada caso se dibuja SOLO hasta la vela de la señal (sin ver el resultado).
- Página de revisión publicada (https://claude.ai/artifact/B1PLzfg9X72ZzoXCAs6ZCt); las respuestas quedan en su
  base (colección `respuestas`). Lightweight-charts necesitó formateadores propios de hora/precio: con el idioma del
  entorno ("en-US@posix") el formateo nativo fallaba y los gráficos quedaban vacíos.

### Ronda 1 de revisión (40 casos respondidos)
- 25 sí / 8 dudosa / 7 no. Las brechas del ASH y de las XO casi no separan los sí de los no; lo que separa es
  (a) la **ubicación respecto del VWAP de sesión** (no compra por encima de +1σ ni vende por debajo de −1σ) y
  (b) el **rango oscilante** (≥ 4 cruces del ASH de 1m en 30 min). Las dos juntas: 23/25 sí pasan, 7/7 no filtrados.
  Elegidas sobre los mismos 40 → hace falta una ronda nueva para validarlas. Detalle: `reports/f2/ronda1_analisis.md`.
- Sus comentarios mencionan mucho la "toma de lows/highs" (barrida de liquidez) y los rebotes en −2σ, dVAL, DO, rVAH:
  la barrida aparece en 36 % de los sí contra 12–14 % del resto; se deja para el estudio de niveles/volumen (F5–F6).
- Tipo continuación/rebote con d ≤ 1 ATR de 5m: coincide 34/40.
- SL: riesgo mediana 2,65 ATR; extremo de las últimas 2–5 velas + 0,3–0,7 ATR.
- Filtros sumados a `senales.py`. Con ellos pasan 16 288 de 25 346 señales amplias de 2023–2024. Verificado que el
  código reproduce las medidas de la ronda 1 caso por caso (40/40) y el resultado 23/25 sí · 0/7 no · 6/8 dudosas.
- Ronda 2 publicada (https://claude.ai/artifact/WpAyVTCgDANQB8Bpfhrpav): 30 casos de días nuevos, 20 que pasan los
  filtros y 10 que no (5 por ubicación, 5 por rango), orden mezclado; qué grupo es cada uno queda solo en
  `reports/f2/ronda2/casos.json`.

### Ronda 2 (2026-10-01)
- 16 sí / 9 dudosa / 5 no. Los filtros de la ronda 1 no generalizan (ver `reports/f2/ronda2_analisis.md`): era el
  sobreajuste esperable de elegir reglas con 40 casos. Con 70 casos, ninguna variable objetiva separa sus sí del
  resto con AUC > 0,63. Tipo continuación/rebote: 30/30.

## F3 · Motor de ejecución (2026-10-01)
- F2 cerrada (Juan): señal base congelada (ASH + XO, A = 0,5, B = 1,0; tipo por d ≤ 1 ATR de 5m), sin filtros duros.
- SL elegido por coincidencia con los 49 SL de Juan (`src/sl.py`, `reports/f3_sl_candidatos.csv`):
  **extremo de las últimas 10 velas ± 0,25 ATR(14)** → error mediano 0,20 ATR, 61 % a ≤ 0,25 ATR, 76 % a ≤ 0,5 ATR.
  ext_5, zigzag y "desde el giro del ASH" con 0,25 ATR quedan casi iguales.
- `src/motor.py`: fill en el primer tick (barra de 1 s) tras el cierre; TP por el primer segundo del last; SL por mark
  1m; mark sintético (last 1 s + base interpolada) para el minuto de entrada y para SL/TP en el mismo minuto; patas
  (máx. 4 abiertas); invalidación opcional (30 min, 0,5 R, ≥ 2 señales); tope 24 h. TP provisorio 2R desde el fill.
- Chequeo independiente segundo a segundo en 150 patas: coincide (la única diferencia era un error del chequeo).
- 2023–2024: 16 006 patas / 8 621 posiciones sin invalidación; 17 873 / 13 054 con invalidación. Ambiguas: 23
  (0,14 %); todas en minutos violentos (rango del mark 70–900 USD) donde el sintético no reproduce. Fill − close
  medio 0,08 USD. Riesgo mediano 63,5 USD = 2,63 ATR (igual al de Juan, 2,65). 2–3 patas con nocional > 125×.
- Señales en contra con posición abierta: 9 077 ignoradas (registradas). Patas acumuladas por posición: hasta 29
  (con máx. 4 abiertas a la vez, se liberan lugares al cerrar).
- Mark sintético: en minutos normales reproduce el high/low del mark con error mediano 3–4 USD (76 % dentro de 2e-4).
- Auditoría publicada: https://claude.ai/artifact/8oR6e7PW8aVESFw6wisk14 (respuestas en la colección `auditoria`).

### Auditoría F3 (Juan, 2026-10-01): 13 sí · 4 no · 3 no sé
- t04 / t19: el precio quedó a 0,0–0,7 USD del SL (t04) y a 0,4 USD del TP (t19) sin tocarlos; el motor estaba bien.
  Hallazgo: SL y TP no estaban redondeados al tick → corregido (SL y TP siempre en la grilla de 0,1).
- t06 / t08: el last tocó el SL antes que el mark (correcto según la regla "SL por mark"); Juan no quiere trayectorias
  sintéticas y evalúa usar SL por last (su exchange lo permite). Se agregó `sl_por="last"`: SL y TP por last con
  barras de 1 s, sin sintético. 2023–2024: 0 casos ambiguos (nunca SL y TP en el mismo segundo).
- t11 / t12 / t13: el cierre por invalidación dispara sin oscilación real: "≥ 2 señales desde la entrada" se cumple
  casi siempre (~22 señales por sesión). Además la pata 2 de t11 se cerró 1 min después de su entrada porque el
  reloj de 30 min es el de la pata 1. Hay que redefinir la regla.
- Cambios de Juan aplicados: SL por last (por defecto) e invalidación por pata (30 min reales, ≤ 0,5 R, ≥ 7 cruces
  del fill, ≥ 3 cruces del ASH). 2023–2024 con invalidación: 1 674 cierres por invalidación (antes 4 896), mínimo
  30,0 min, mediana 44. Verificados 3 a mano (cruces contados aparte).
- **Bug corregido:** con el SL y el TP redondeados al tick, el chequeo R ≥ 2 fallaba por punto flotante (1,9999999 <
  2) y descartaba ~3 000 señales en la corrida por last (16 en la de mark). Se agregó tolerancia 1e-9. Corrida final
  por last: 16 125 patas / 8 864 posiciones (sin invalidación); 16 875 / 10 614 (con invalidación).
- Reauditoría publicada: 12 trades (incluye t06 y t08 con la regla nueva).
- Reauditoría 12/12 correcta → **F3 cerrada** (2026-10-01).
- Primer reporte §9 (`reports/f3/reporte_base_tp2.md`), señal base + SL ext10 + TP provisorio 2R, sin comisiones:
  2023–2024 +0,053 R/pata (IC [+0,024, +0,082]); 2025–2026 (sin reserva) +0,044 R (IC [+0,009, +0,078]), win rate
  ~35 % (el empate con 2R es 33,3 %). Con invalidación: +0,045 y +0,042. Máx. DD 104 y 154 R. Short > long; continuación
  > rebote (rebote ≈ 0). Slippage del SL irrelevante (0–5 ticks). Con comisión taker 0,05 % costaría ≈ 0,7 R/trade.
- **Bug corregido:** en el reporte, `hour()` de polars es Int8 y `hora × 60` desbordaba: la subsesión NY quedaba
  vacía (todo caía en Londres). Se castea a Int32.

## F6 (adelantada a pedido de Juan, 2026-10-01): ¿qué mejora el win rate / la expectativa?
- `src/f6_variables.py`: 20 variables por pata al cierre de la vela de señal (ubicación VWAP día/semana, cruces ASH y
  XO, RVOL, CVD 5/15 min, órdenes grandes a mercado, OI 15/60 min, ratio taker, ASH y distancia de 5m, régimen ATR,
  niveles cercanos) + recorrido a favor antes del SL (MFE).
- **TP vs win rate:** con cualquier TP la señal queda 1–2 puntos sobre el empate (TP 1R: WR 51 % vs 50 % de empate;
  2R: 35 % vs 33,3 %; 3R: 26 % vs 25 %). Cambiar el TP mueve el win rate pero no la ventaja.
- **Variables consistentes en los dos períodos (descriptivo):** pocas o ninguna rotación de las XO en 60 min → pierde;
  ASH de 5m en contra → pierde; OI subiendo fuerte en 60 min → peor; ≥ 5 órdenes grandes a favor en 5 min → peor
  (perseguir). Efectos de ±0,05–0,10 R por quintil.
- **Prueba fuera de muestra (`src/f6_filtros.py`):** filtros elegidos solo con 2023–2024 (excluir ASH 5m en contra,
  ≥ 5 órdenes grandes a favor, precio pegado a las EMAs de 5m) → entrenamiento +0,053 → +0,095 R; **test 2025–2026
  +0,044 → +0,045 R (sin mejora)**. Walk-forward trimestral: OOS +0,056 R. El único filtro que el walk-forward elige
  en todos los trimestres es "ASH de 5m en contra". Conclusión: los indicadores de volumen/OI no arreglan esta señal
  de forma robusta; la señal base ASH/XO en 1m tiene una ventaja muy chica.

## Estrategia B · trader de referencia (2026-10-01)
- `src/estrategia_b.py` (B1, reversión desde el extremo, TP en la media). Chequeo contra su trade documentado del
  20-feb-2026: las variantes dVAL/dVAH y ±1σ encuentran sus entradas long de 01:27 y 02:26 UTC (él: ~67 127 y ~67 136;
  nuestro fill 67 149,9 → TP en la media 67 226,4, +1,7 R). ±2σ no las encuentra (ese día no se tocó la banda).
- Corrida en la ventana de calibración feb–may 2026 (`reports/b/`); página de revisión con 12 trades (los 2 suyos +
  5 dVAL/dVAH + 5 ±2σ) antes de mostrar números agregados (regla 2).
- Revisión de B1 por Juan: 12/12 correcto (el código opera el setup del trader).
- **Test de B1** (calibración feb–may 2026 → test 2023–2025 + jun 2026, reserva cerrada), TP en la media, 1 pata:
  | variante | R mín | calib. | test | IC 95 % test |
  |---|---|---|---|---|
  | dVAL/dVAH | 1 | +0,025 | +0,010 | [−0,025, +0,044] |
  | dVAL/dVAH | 2 | +0,085 | +0,038 | [−0,016, +0,088] |
  | ±1σ | 1 | +0,018 | −0,046 | [−0,077, −0,016] |
  | ±1σ | 2 | +0,069 | −0,014 | [−0,062, +0,037] |
  | ±2σ | 1 | −0,036 | +0,008 | [−0,033, +0,049] |
  | ±2σ | 2 | −0,001 | +0,011 | [−0,040, +0,063] |
  La mejor en calibración (dVAL/dVAH, R ≥ 2) cae a la mitad en el test y su IC incluye 0. Recorrido a favor antes
  del SL: mediana 0,98 R; con cualquier TP más cerca la expectativa queda ≈ 0. Asia algo mejor (+0,042, IC incluye 0).
  Conclusión: la parte mecánica del setup (nivel + rechazo + TP en la media) no tiene ventaja robusta en BTC 1m
  2023–2025. Lo que el trader agrega y no está codificado: lectura de orderflow (Aggr 10 s: esfuerzo sin resultado,
  absorción), selección del contexto ("meta" del día) y manejo del trade (scratch rápido, parciales).

## Estrategia B · tres mejoras: absorción, scratch y meta del día (2026-10-01)
- `src/b_variables.py` (esfuerzo, resultado, absorción, delta del empujón, cruces del VWAP en el día, rango del día)
  y manejo opcional en `motor.resolver_pata_last` (breakeven al llegar a +be_r R; corte por tiempo). Selección en
  `src/b_seleccion.py` → `reports/b/seleccion.txt`. Período 2023-01 → 2026-06 (sin la reserva).
- Bug: `pl.col("mes").is_between("2026-02", "2026-05")` toma los strings como nombres de columna → `pl.lit(...)`.
- **Estático** (elige con 2023–2024): dVAL/dVAH · R ≥ 2 · breakeven 1R · absorción ≥ p40 · cruces VWAP ≥ p60,
  +0,104 R en entrenamiento → **−0,006 R en 2025–2026** [−0,088, +0,080] (sin filtros ni manejo: +0,062).
  Sobreajuste: la combinación de filtros no sobrevive.
- **Walk-forward trimestral** 2025Q1–2026Q2: OOS **+0,108 R** [+0,049, +0,170], 2984 trades, WR 12,6 %; sin
  feb–may 2026 (usados para calibrar B1): +0,091 [+0,017, +0,167]. Desde 2025Q2 el walk-forward elige siempre
  **breakeven 0,5 R**; los filtros entran y salen.
- Por componente (dVAL/dVAH, R ≥ 1, entrenamiento / test): sin manejo +0,005 / +0,024 · **breakeven 0,5R +0,053 /
  +0,079** · breakeven 1R +0,037 / +0,066 · corte 10 min +0,016 / +0,035 · corte 20 min +0,010 / +0,022.
  Con R ≥ 2: sin manejo +0,037 / +0,062 → breakeven 0,5R +0,087 / +0,123 (52 % de los trades salen en 0).
- Absorción ("high effort, unrewarded"): la hipótesis va AL REVÉS en entrenamiento (quintil bajo +0,054, alto −0,019)
  y en el test no es monótona. No sirve como filtro.
- Cruces del VWAP en el día (meta rotacional): también al revés de la hipótesis. Los días con POCOS cruces dan más
  (Q1 +0,086 entrenamiento / +0,182 test; Q5 −0,021 / −0,032). Sólo se probó la dirección "≥" (fijada antes), así que
  la dirección contraria es una hipótesis nueva vista en el test: no se adopta sin otra validación.
- Riesgo mediano 63 USD (~630 ticks): el slippage de pocos ticks en el stop de breakeven no cambia nada. Con
  comisión taker 0,05 % por lado (~0,7 R por lado con ese riesgo) todo esto sería negativo; el proyecto es sin comisiones.

## Estrategia B · breakeven adoptado y validación de "pocos cruces del VWAP" (2026-10-01)
- Juan adopta breakeven a +0,5 R (`b_correr.py` lo trae por defecto; `--be 0` lo apaga).
- Chequeo de confusión en entrenamiento (2023–2024): "pocos cruces" ≈ "temprano en la sesión" (0–4 h UTC +0,141 vs
  ≈ +0,07 el resto). Dentro de cada tramo de 4 h, pocos vs muchos cruces: +0,156/+0,123, +0,016/+0,133,
  +0,053/+0,078, +0,083/+0,070 → sin un signo consistente.
- Validación pre-registrada en **2022** (`src/b_validacion_2022.py` → `reports/b/validacion_2022.txt`), un tramo
  nunca usado por B:
  - H0, B1 dVAL/dVAH R ≥ 2 con breakeven 0,5 R: **+0,116 R [+0,059, +0,174]**, 2455 trades, WR 12,1 %.
    Positivo en los 4 trimestres (Q2 ≈ 0: +0,012). Sin breakeven (comparación no pre-registrada): +0,082, WR 24,7 %.
  - H1, cruces ≤ 16 vs > 16: dif +0,028 [−0,085, +0,146] → **no se confirma**; dentro de los tramos de 0–8 h, dif ≈ 0.
  - H2, 00:30–04:00 UTC vs resto: dif −0,020 [−0,152, +0,114] → **no se confirma** (en 2022 Asia no rinde más).
- Conclusión: el filtro de cruces del VWAP se descarta. Lo que se sostiene en 4 años (2022 fresco, 2023–2024,
  2025–2026 walk-forward) es B1 dVAL/dVAH, R ≥ 2, breakeven 0,5 R: entre +0,09 y +0,12 R por trade, sin comisiones.

## Trades del trader · septiembre 2026 (2026-10-01)
- Juan mandó 18 capturas (31-ago → 1-oct). Se transcribieron 105 entradas de las tarjetas (Variational 50x, Nado,
  TxFlow, RISE) y de las listas de órdenes con hora (`marcas/trader_sep2026/trades.csv`). Su exchange cotiza ≈ 10–45 USD
  arriba de Binance. Zona horaria de las capturas: UTC+2, verificada con 11 órdenes con hora del 28-sep.
- Fuera: lote1_01 (1-oct, nueva reserva) y 4 posiciones swing que aparecen en varias capturas.
- Ubicación al minuto (`src/trader_sep.py`): minuto de Binance donde pasó su precio, el más cercano a donde lo dibujó.
  Confianza: 29 alta, 38 media, 38 baja (la zona de precio es segura; el minuto exacto no siempre).
- `f0_descarga.py`: si el zip mensual todavía no está publicado (404), usa los diarios; un 404 ya no se reintenta.
- Reserva movida: `datos.RESERVA = 2026-10 → 2026-12` (jul–sep liberados).
- Lectura descriptiva vs un minuto cualquiera de septiembre (mismo lado):
  - del lado barato del VWAP de sesión 73 % (vs 50 %); más allá de 1σ en contra 51 % (vs 21 %, 2,5×);
  - contra el rolling VWAP 69 % y contra el VWAP semanal 67 % (de tendencia: 31 % vs 50 %);
  - barrida del extremo de 60 min en las últimas 5 velas 27 % (vs 15 %, 1,8×);
  - ASH 1m a favor 50 % (= azar); XO 1m cruzadas a favor 33 % y ASH 5m a favor 32 % (vs 50 %): entra ANTES de que
    giren los osciladores;
  - RVOL, CVD, cercanía a un nivel (≤ 0,5 ATR: 48 % vs 45 %) y horario: sin diferencia.
  - Entradas agrupadas (varias por jugada): no son independientes; los porcentajes son descriptivos.
- Página de revisión de las ubicaciones: https://claude.ai/artifact/CcvQAupyC3KseTdnTdtrYg (colección `ubicacion`).
- Revisión de Juan de las 105 ubicaciones (2026-10-01): 24 bien, 75 mal (casi todas con la hora correcta de la vela),
  6 "no sé". 12 excluidas (no encontró el trade en el gráfico, duplicada o lado incorrecto). Por pedido de Juan no se
  exige la vela exacta: se toma la vela más próxima a su hora (±15 min) donde pasa su precio; si no pasa, su vela.
  Resultado: 60/65 tocan su precio a 0,3 min de media de su hora. `marcas/trader_sep2026/revision_juan.csv`;
  `trades_v1.csv` = ubicación original.
- Con las ubicaciones corregidas (93 entradas) el patrón se refuerza: más allá de 1σ del VWAP de sesión en contra 51 %
  (vs 21 %), barrida del extremo de 60 min 34 % (vs 15 %, 2,3×), venía en contra 15 min 49 % (vs 37 %), y los
  osciladores en contra al entrar: ASH 5m a favor 23 % (vs 51 %), XO 1m 30 % (vs 50 %), ASH 1m 38 % (vs 50 %).
  Contra el rolling VWAP 68 %. RVOL, CVD, cercanía a niveles y horario: sin diferencia.

## Estrategia B2 · calibración con las entradas del trader de septiembre (2026-10-01)
- `src/volumen.py`: rasgos de volumen por minuto (delta de la vela, delta de los últimos 10 s con las velas de 1 s,
  CVD 5/15 min, volumen 15 min relativo, pico en velas de 10 s, absorción esfuerzo/resultado de 5 velas, burbujas de
  órdenes grandes en 15 min, OI 15/60 min).
- `src/b2.py`: 12 variantes de la señal, calibradas por coincidencia con sus 93 entradas (no por PnL). Las de precio
  solo (σ, rolling VWAP, barrida) detectan ~35 % de sus entradas con ~12 % de precisión.
- Volumen: sus entradas vs señales de precio (V2) que no tomó vs minuto cualquiera:
  volumen 15 min ≥ 1,5× normal 68 % / 28 % / 31 % (mediana 2,6× / 1,0× / 1,0×); absorción ≥ 2 32 % / 4 % / 5 %;
  delta de la vela de entrada a favor 52 % / 28 % / 50 % (mediana +1 % / −26 % / 0 %): entra cuando la agresión en
  contra se agota, no mientras sigue; ≥ 15 burbujas grandes en contra en 15 min 61 % / 24 % / 22 % (mediana 22 / 7 / 6);
  divergencia del CVD 15 min, pico en velas de 10 s y OI: no distinguen.
- Variante elegida por coincidencia: V10 = σ + volumen 15 min ≥ 1,5× + absorción ≥ 1 (detecta 41 % de sus entradas,
  16 % de precisión, ~14 señales/día). Página con 14 casos: https://claude.ai/artifact/3RCjPq8Fi8tnaAfSoeJMui
- Revisión de Juan de B2 ronda 1 (14 casos): 12 sí, 1 no, 1 sin responder. Comentario repetido: B2 entra antes y más
  arriba que el trader ("se toma más abajo") y dispara varias veces antes del punto óptimo (riesgo de SL). C08: el
  trader amplía longs por testeo de EMAs. `marcas/revision_b2_ronda1.json`.
- Recalibración del disparo (`src/b2_timing.py`, mismo setup V10): mediana del precio de B2 vs el suyo +0,17 ATR (peor)
  con el disparo base. Mejor: "hondo_ag" = más allá de ±1,5σ + primera vela sin extremo nuevo de 5 velas, que cierra a
  favor y con delta a favor (agresión agotada): detecta 45 % de sus entradas, 22 % de precisión, precio −0,06 ATR (igual
  al suyo), 12 señales/día. Ronda 2 (mismos 14 momentos): https://claude.ai/artifact/3t9jmiVuWsfE5xUn5i1Mo4
- Ronda 2 de B2 (Juan): 12 sí, 2 no sé. Observación central: tras la 1.ª señal B2 una mecha barre el low/high → SL.
- Diagnóstico (`src/b2_barrida.py`, `b2_sl.py`, `b2_primera.py`; jul–sep 2026, velas de 1m, sin BE): 1147 señales en
  400 jugadas (61 % con más de una señal). Al 80 % le barren el extremo de 10 velas antes de llegar al VWAP; la 1.ª
  señal 77 %, las siguientes 82 %; ignorar la 1.ª y entrar tras la barrida de su extremo: 78 % (no lo arregla).
  Entre las que llegan al VWAP, el precio pasa el extremo una mediana de 2,9 ATR antes (solo 8 % son mechas ≤ 1 ATR):
  no es una mecha, es que el movimiento sigue. Ampliar el SL (0,25 → 1,5 ATR) no mejora el R medio (−0,05 a −0,09).
  Al momento de la 1.ª señal, las jugadas sin barrida tienen algo más de volumen (3,8× vs 2,9×), absorción, ATR
  expandido (1,9× vs 1,6×) y menos recorrido en 4 h, pero ningún cuartil baja la barrida de 67 %.
  Ojo: "1.ª señal de jugadas con una sola señal" (+1,23 R) usa información futura (que no hubo más señales).
- ¿Por qué el trader "gana 75 %"? (`src/b2_vs_trader.py`, 4 h, velas de 1m): +1 ATR antes de −1 ATR: sus 93 entradas
  86 %, señales B2 50 %; +0,5/−3 ATR: 97 % vs 81 %. Sus capturas son tarjetas de PnL de posiciones ganadoras: la
  muestra está sesgada a ganadores (no hay ninguna tarjeta en pérdida), así que su win rate real no es observable.
- B2 escalonada (`src/b2_escalonada.py`, jul–sep 2026, 1m, sin BE ni comisiones): SL común detrás del extremo
  (0,25–3 ATR), 1–3 patas (por nueva señal B2 o por órdenes límite cada 0,5/1 ATR), TP VWAP / mitad / +1 ATR.
  60 combinaciones: win rate entre 22 % y 88 % (SL ancho + TP chico = 80–88 %, como el trader), pero R medio entre
  −0,09 y +0,02 en todas: el escalonado cambia el win rate, no la ventaja. La mejor (+0,022) es ruido de 60 pruebas
  en muestra. Ampliar por señal casi no ocurre (1,1–1,4 patas de media).
- Test fuera de muestra B2 escalonada 2023–2025 (config. fijada antes: SL extremo − 2 ATR, 3 patas cada 1 ATR,
  TP +1 ATR; velas de 1m, sin BE ni comisiones): 12 657 posiciones, gana 84 %, R medio +0,018 [IC 95 % +0,010,
  +0,026]; 2023 +0,012, 2024 +0,022, 2025 +0,019. Ganancia media +0,19 R, pérdida media −0,88 R. Positivo y estable,
  pero muy chico: con riesgo ≈ 3 ATR (≈ 0,3 % del precio) la comisión taker ida y vuelta cuesta ≈ 0,3 R por pata.
- Pérdidas del trader (Juan: calaveras sobre las herramientas long/short de TV): detección por plantilla + revisión
  visual → 16 calaveras, 15 únicas (K10 ≈ K08), en `marcas/trader_sep2026/calaveras.csv` (hora y precio aproximados,
  lado sin confirmar). Con ~93 entradas ganadoras de las tarjetas, su win rate ronda 85 %, coherente con el 86 % de
  "+1 ATR antes de −1 ATR" medido en sus entradas. Corrige lo dicho antes: no es solo sesgo de selección.
- B2 con filtro R ≥ 2 y distintos TP (`src/b2_tp.py`, una pata, sin comisiones — Variational no cobra): 36 variantes
  (SL 0,25/0,5/1 ATR × TP 2R/2,5R/3R/VWAP/+1σ/primer nivel a ≥ 2R × BE no/+1R). Elegida en calibración (jul–sep 2026):
  SL 1 ATR, TP 2,5R, sin BE: +0,052 → test 2023–2025 −0,022 [IC −0,057, +0,012]. Todo el test entre −0,027 y +0,036;
  la familia SL 0,25 ATR da positivo en test en las 12 variantes (+0,007 a +0,036; TP "nivel" +0,036), pero no fue la
  elegida en calibración. Win rate 10–35 %. Sin ventaja robusta con 1:2.
- Relación 1:2 (b2_vs_trader.py): +2 ATR antes de −1 ATR: sus entradas 81 %, señales B2 34 % (azar ≈ 33 %). Con sus entradas el 1:2 conserva el win rate; con B2 cae al azar.
- Pérdidas del trader (15 calaveras, lado confirmado por Juan 2026-10-02; `src/trader_perdidas.py`, ubicación
  aproximada, 11/15 por precio) vs 93 ganadas: las perdidas NO están en el extremo (z mediana −0,21σ vs −1,01σ; más
  allá de −1σ 20 % vs 51 %), casi sin barrida (13 % vs 34 %), con los osciladores ya a favor (XO 1m 53 % vs 30 %,
  ASH 1m 53 % vs 38 %), menos volumen (1,9× vs 2,6×) y menos absorción (0,47 vs 1,20), CVD a favor 53 % vs 27 %.
  O sea: sus pérdidas son entradas "de confirmación" a mitad de camino; sus ganadoras, las de extremo con absorción.
  n = 15: descriptivo.
