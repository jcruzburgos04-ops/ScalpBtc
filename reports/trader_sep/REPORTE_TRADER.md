# Trader de referencia · trades de septiembre 2026 · reporte completo

Generado el 2026-10-28 desde el proyecto de backtest de Juan Cruz (BTC 1m). Todo lo que sigue está medido
sobre datos reales de Binance USD-M `BTCUSDT` perpetuo; no hay datos sintéticos.

## 1. Contexto y convenciones (leer antes de usar los números)

- **Quién**: un trader discrecional de BTC en 1m que Juan sigue. Juan mandó 18 capturas de TradingView (`BTCUSDT.P`,
  1m) del 31-ago al 1-oct-2026, con las tarjetas de PnL de sus posiciones (Variational 25–50x, Nado, TxFlow, RISE),
  listas de órdenes con hora y las herramientas long/short de TV. Las perdidas están marcadas con una calavera.
- **Hora**: el eje de sus capturas está en **UTC+2** (verificado con 11 órdenes con hora del 28-sep contra Binance).
  En este reporte `hora_trader` = UTC+2 y `hora_utc` = UTC. Hora argentina = UTC−3.
- **Precio**: su exchange cotiza ≈ 10–45 USD **arriba** de Binance. Todas las mediciones llevan su precio a Binance
  restando 20 USD.
- **Ubicación al minuto**: las tarjetas dan el precio de entrada, no la hora. La hora sale de dónde dibujó la entrada
  en el gráfico. Juan revisó las 105 ubicaciones (24 bien, 75 corregidas, 6 "no sé") y excluyó 12. Por pedido suyo se
  toma la vela de Binance más próxima a su hora (±15 min) donde pasa su precio. Columna `confianza`: Juan = hora que
  marcó Juan; confirmada = la ubicación original estaba bien; alta/media = ubicación automática.
- **Muestra sesgada**: las tarjetas muestran posiciones abiertas en ganancia. Las pérdidas salen de las calaveras
  (15, con hora y precio aproximados). Win rate aproximado: 93 ganadas vs 15 perdidas ≈ **86 %**.
- **Las entradas vienen agrupadas** (varias tarjetas por jugada, ampliaciones): no son independientes.
- **Fuera del análisis**: las entradas del 1-oct-2026 (caen en el período de reserva del backtest, oct–dic 2026,
  que no se mira) y 4 posiciones swing que aparecen en varias capturas (TxFlow short 81 511,9 y 81 198,2; Nado long
  76 258 y 76 446).

### Su gráfico
- Líneas: VWAP **blanco = sesión** (ancla 00:00 UTC), VWAP **rojo = semanal** (lunes 00:00 UTC), **amarillo = rolling
  VWAP** (24 h). Bandas ±1σ/±2σ.
- Etiquetas que usa: MNDAY-H/L (máximo/mínimo del lunes), dVAH/dVAL/dPOC (perfil del día), pdVAL (día previo),
  pwVAL/pwVWAP (semana previa), rVAH/rVAL (perfil rolling 24 h), EMAs de 4h 13/34/100, DO.
- Volumen: Volume Suite, CVD, ampliación de velas de TV; en sus reviews menciona orderflow en Aggr (10 s).

### Su estilo según 9 reviews en PDF (feb–may 2026)
Reversión a la media en rango: "edge to edge" (banda ±2σ → banda opuesta), "mean to edge" (VWAP de sesión → ±1σ/±2σ),
"momentum loss", "first test best test". Niveles que más nombra: VWAP de sesión ("the mean") y sus bandas, S/R manuales,
VWAP anclados, DO / apertura de futuros / NYO / IB, bandas semanales, dVAL, cinta de EMAs. Lee orderflow (esfuerzo sin
resultado, absorción), elige el contexto ("meta" del día) y maneja el trade (scratch rápido, parciales).

## 2. Qué hace al entrar (93 ganadas, mismo lado, vs un minuto cualquiera de septiembre)

| Rasgo al entrar | Sus entradas (n=93) | Revisadas por Juan (n=87) | Cualquier minuto de sep. | Veces más frecuente |
|---|---|---|---|---|
| Precio del lado barato del VWAP de sesión (long debajo / short arriba) | 72% | 71% | 50% | 1.4× |
| Lejos del VWAP de sesión: más allá de 1σ en contra (long < −1σ / short > +1σ) | 51% | 48% | 21% | 2.4× |
| Más allá de 2σ en contra | 5% | 6% | 2% | 2.5× |
| Del lado de la tendencia: long sobre el rolling VWAP / short debajo | 32% | 33% | 50% | 0.6× |
| Del lado de la semana: long sobre el VWAP semanal / short debajo | 35% | 37% | 46% | 0.8× |
| Un nivel a ≤ 0,25 ATR | 24% | 25% | 27% | 0.9× |
| Un nivel a ≤ 0,5 ATR | 48% | 51% | 45% | 1.1× |
| Venía en contra los últimos 15 min (≥ 1 ATR) | 49% | 47% | 37% | 1.3× |
| Venía a favor los últimos 15 min (≥ 1 ATR) | 23% | 24% | 37% | 0.6× |
| Barrida: extremo en contra de 60 min en las últimas 5 velas | 34% | 31% | 15% | 2.3× |
| ASH 1m ya a favor | 38% | 40% | 50% | 0.7× |
| XO 1m ya cruzadas a favor | 30% | 32% | 50% | 0.6× |
| ASH 5m (en formación) a favor | 23% | 24% | 51% | 0.4× |
| RVOL ≥ 1,5 en alguna de las últimas 5 velas | 61% | 59% | 53% | 1.1× |
| CVD 5 min a favor (más agresión a favor) | 37% | 39% | 49% | 0.8× |
| Dentro de la ventana de Juan (00:00 UTC → 12:00 NY) | 67% | 64% | 67% | 1.0× |

Además (rasgos de volumen, 93 entradas vs señales de precio que no tomó vs minuto cualquiera): volumen de 15 min ≥ 1,5×
lo normal 68 % / 28 % / 31 % (mediana 2,6× / 1,0× / 1,0×); absorción (volumen alto con poco rango) ≥ 2: 32 % / 4 % / 5 %;
≥ 15 órdenes grandes en contra en 15 min 61 % / 24 % / 22 %; delta de la vela de entrada a favor 52 % (mediana +1 %): entra
cuando la agresión en contra se agota. Tendencia: a favor de la EMA 200 de 4h el 78 % (opera ~80% longs en un mes
alcista). Sus entradas casi nunca están pegadas a un nivel (≤ 0,5 ATR: 48 % vs 45 % al azar).

**Resumen**: compra abajo de la media de la sesión (más allá de −1σ), después de una barrida del mínimo de la última hora
y de una caída de ~1 ATR en 15 min, con volumen alto y absorción, ANTES de que giren los osciladores (ASH/XO de 1m y 5m
todavía en contra), a favor de la tendencia de 45m–4h y en contra del rolling VWAP de 24 h.

## 3. Ganadas vs perdidas (93 vs 15 calaveras)

Ganadas (tarjetas): 93 · perdidas (calaveras): 15 (11 ubicadas por precio). Lado = el del trade; n chico: diferencias de < 25 puntos no son concluyentes.

| Al entrar… | Ganadas | Perdidas |
|---|---|---|
| Más allá de 1σ del VWAP de sesión, en contra | 51% | 20% |
| Contra el rolling VWAP | 68% | 53% |
| Contra el VWAP semanal | 65% | 67% |
| Barrida del extremo de 60 min | 34% | 13% |
| Venía ≥ 1 ATR en contra en 15 min | 49% | 40% |
| ASH 1m a favor | 38% | 53% |
| XO 1m a favor | 30% | 53% |
| ASH 5m a favor | 23% | 27% |
| Nivel a ≤ 0,5 ATR | 48% | 33% |
| Dentro de la ventana de Juan (hora UTC < 16) | 67% | 67% |
| Volumen 15 min ≥ 1,5× | 68% | 53% |
| Absorción ≥ 1 | 55% | 40% |
| Delta de la vela a favor | 52% | 60% |
| CVD 15 min a favor | 27% | 53% |
| ≥ 15 burbujas grandes en contra en 15 min | 61% | 40% |

| Mediana | Ganadas | Perdidas |
|---|---|---|
| z_vwap_d·lado | -1.01 | -0.21 |
| ret15_atr | -0.91 | -0.39 |
| ret60_atr | -3.08 | -2.40 |
| vol15_rel | 2.61 | 1.91 |
| absorcion5 | 1.20 | 0.47 |
| delta1 | 0.01 | 0.05 |
| hora_utc | 13.85 | 13.50 |

Lectura: sus pérdidas son entradas "de confirmación" a mitad de camino (cerca del VWAP, sin barrida, con los osciladores
ya a favor, menos volumen y absorción); sus ganadoras son las de extremo con absorción. n = 15: descriptivo.

## 4. Qué pasa después de entrar (velas de 1m de Binance, 4 h)

- Avanza +1 ATR antes de ir −1 ATR en contra: ganadas 86%, perdidas 20%.
- Avanza +2 ATR antes de −1 ATR (relación 1:2): ganadas 81%, perdidas 20%.
- Recorrido a favor de las ganadas hasta que el precio vuelve a la entrada (o 4 h): mediana
  8.0 ATR (p25 3.8, p75 14.6), en una mediana de
  41 minutos. En contra antes de ese máximo: mediana 0.00 ATR; el 60% nunca fue en contra de su precio (entra muy cerca del extremo).
- Para comparar: las señales automáticas que intentaron copiarlo (B2) dan 50 % en +1/−1 y 34 % en +2/−1 (≈ azar).

## 5. Dónde termina el recorrido a favor (proxy de sus salidas)

No se pudieron leer automáticamente las cajas long/short de TV (muy tenues). Se usa el extremo a favor que alcanzó cada
ganadora antes de volver a la entrada. 40 de 93 terminan a ≤ 0,25 ATR de algún nivel (columna `nivel_fin`).

| Nivel | Finales a ≤ 0,25 ATR | Placebo | Veces más |
|---|---|---|---|
| MNDAY-H | 7 (8%) | 1% | 12.1× |
| VWAP +2σ | 6 (6%) | 1% | 5.5× |
| dVAH | 6 (6%) | 1% | 4.9× |
| VWAP +2σ semanal | 5 (5%) | 0% | 12.5× |
| dVAL | 6 (6%) | 2% | 3.5× |
| pdVAL | 4 (4%) | 1% | 4.7× |
| MNDAY-L | 4 (4%) | 1% | 3.0× |
| VWAP +1σ | 3 (3%) | 1% | 2.9× |
| PWL | 2 (2%) | 1% | 3.7× |
| pdVWAP | 2 (2%) | 1% | 1.6× |
| VWAP −2σ | 2 (2%) | 1% | 1.6× |
| VWAP −2σ semanal | 1 (1%) | 0% | 2.4× |
| pwVAL | 1 (1%) | 1% | 1.9× |
| H4 13EMA | 2 (2%) | 2% | 1.3× |
| mVAL | 1 (1%) | 1% | 1.3× |

Placebo = el mismo nivel desplazado ±0,2–1 % por día; "veces más" = cuánto más frecuente que el placebo.

## 6. Qué se sacó de esto en el backtest (resumen, sin comisiones, en R)

- Copiar sus entradas con reglas (estrategia "B2": más allá de ±1,5σ + volumen + absorción + vela que gira con delta a
  favor) detecta ~45 % de sus entradas, pero el resultado cae al azar: lo que no se pudo codificar es su selección del
  contexto y su manejo del trade. B2 congelada (filtro EMA 200 de 45m, TP VWAP): +0,064 R por trade en test, gana 13 %.
- Lo que sí se trasladó: el **filtro de tendencia EMA 200 de 45m** (el más robusto de 24 filtros) y el **TP en el nivel
  opuesto** (MNDAY-H/L, VWAP ±2σ de sesión y semanal, dVAH/dVAL), que mejoran la estrategia de Juan.
- Estudio de niveles 2025–2026 con placebo y corrección por comparaciones múltiples: MNDAY-L y MNDAY-H son los niveles
  que más rechazan (+8,5 y +7,9 puntos sobre el placebo); el VWAP de sesión, ±1σ, dPOC y DO se atraviesan MÁS que el
  placebo.

## 7. Datos por trade

Columnas (todas medidas con la última vela de 1m cerrada antes de la entrada; "a favor" = en la dirección del trade):
- `entrada`: precio de la tarjeta (su exchange; Binance ≈ −20). `hora_trader` UTC+2, `hora_utc` UTC (minuto de Binance).
- `z_sesion_lado`, `z_semana_lado`: distancia al VWAP de sesión / semanal en σ, con signo del trade (negativo = lado barato:
  long debajo, short arriba). `contra_rvwap`: long debajo / short arriba del rolling VWAP 24 h.
- `nivel1`, `dist1_atr`: nivel más cercano y distancia en ATR(14) de 1m (+ = el nivel queda del lado del soporte).
  `niveles_05atr`: cuántos niveles a ≤ 0,5 ATR.
- `ash1/xo/ash5_a_favor`: ASH 1m (RSI 16/4 EMA), cruce de EMAs 11/25 de 1m y ASH de 5m en formación ya a favor.
- `rvol_max5`: RVOL máximo de las últimas 5 velas. `vol15_rel`: volumen de 15 min / mediana del día. `absorcion5`:
  volumen relativo de 5 velas / rango de 5 velas en ATR. `delta1`: (compras − ventas agresivas) / volumen de la vela.
- `ret15_atr`, `ret60_atr`: movimiento de 15 / 60 min en ATR, con signo del trade (negativo = venía en contra).
- `barrida60`: el extremo en contra de las últimas 5 velas es el más extremo de los últimos 60 min.
- `burb_contra15`: órdenes a mercado ≥ 100 k USD en contra en los últimos 15 min.
- `ema200_45m_a_favor`, `ema200_4h_a_favor`: precio del lado del trade respecto de esas EMAs.
- `pos_rango_dia`: posición en el rango del día UTC hasta ese momento (0 = mínimo, 1 = máximo).
- `mfe_atr`: recorrido a favor hasta que vuelve a la entrada (o 4 h); `mae_antes_mfe_atr`: lo máximo en contra antes de
  ese extremo; `min_hasta_mfe`: minutos hasta el extremo; `nivel_fin`: niveles a ≤ 0,25 ATR del extremo.
- `r1_1`, `r2_1`: qué llega primero en 4 h: +1 ATR / −1 ATR y +2 ATR / −1 ATR (TP, SL o nada).
- `revision`: control de Juan de la ubicación automática original (bien / mal → corregida / nose).

### 7.1 Ganadas (tarjetas, 93)

```csv
id,captura,plataforma,lado,entrada,hora_trader,hora_utc,confianza,revision,z_sesion_lado,z_semana_lado,contra_rvwap,nivel1,dist1_atr,niveles_05atr,ash1_a_favor,xo_a_favor,ash5_a_favor,rvol_max5,vol15_rel,absorcion5,delta1,ret15_atr,ret60_atr,barrida60,burb_contra15,ema200_45m_a_favor,ema200_4h_a_favor,pos_rango_dia,atr14,mfe_atr,mae_antes_mfe_atr,min_hasta_mfe,nivel_fin,r1_1,r2_1,comentario_juan
T101,lote4_03,Nado,long,77267.00,08-31 01:49,08-30 23:49,Juan,mal,-2.48,-1.76,true,pwVAH,0.90,0,false,false,false,2.82,13.23,5.20,0.03,-3.72,-8.23,true,74,false,true,0.12,145.40,6.32,0.00,46,MNDAY-H,TP,TP,Es en la vela de las 01:49
T102,lote4_03,Variational,long,78081.14,08-31 16:35,08-31 14:35,Juan,mal,0.14,0.14,true,H4 34EMA,-0.02,3,true,true,false,1.98,1.89,1.10,-0.27,-0.35,-0.56,false,11,false,true,0.50,92.70,10.25,0.00,224,MNDAY-H,TP,TP,"Es en la vela de las 16:35, igual hay varios trades en esa foto, capaz que me estoy confundiendo"
T103,lote4_03,Variational,long,78380.94,08-31 17:21,08-31 15:21,Juan,mal,0.90,0.90,false,dVAH,0.02,3,false,false,true,1.13,1.71,0.73,0.37,-1.29,4.26,false,13,true,true,0.71,86.00,1.69,1.11,7,"",SL,SL,Vela de 17:21
T104,lote4_03,Nado,long,77421.00,09-01 15:43,09-01 13:43,Juan,mal,-1.95,-1.95,true,VWAP −2σ,0.22,1,false,false,false,2.57,3.33,2.25,0.40,-1.57,-3.08,false,22,false,true,0.02,93.60,9.12,0.00,26,rolling VWAP / H4 13EMA,TP,TP,vela de 15:43
T94,lote4_02,Nado,long,76953.00,09-01 20:51,09-01 18:51,Juan,mal,-1.58,-2.04,true,VWAP −2σ,2.42,0,true,false,false,1.60,6.93,1.49,0.14,0.13,-4.96,false,82,false,true,0.20,107.60,5.36,0.79,130,"",TP,TP,vela 20:49
T95,lote4_02,Nado,long,76771.00,09-02 03:55,09-02 01:55,confirmada,bien,-1.61,-2.04,true,VWAP −2σ,1.28,0,false,false,false,2.78,2.61,1.41,-0.28,-2.62,-5.93,true,36,false,true,0.09,63.60,14.82,0.00,91,"",TP,TP,
T97,lote4_02,Variational,long,76783.10,09-02 03:55,09-02 01:55,confirmada,bien,-1.56,-2.02,true,VWAP −2σ,1.47,0,false,false,false,2.78,2.61,1.41,-0.28,-2.62,-5.93,true,36,false,true,0.10,63.60,14.64,0.00,91,"",TP,TP,
T96,lote4_02,Variational,long,77073.96,09-02 04:19,09-02 02:19,confirmada,bien,-0.10,-1.52,true,VWAP sesión,-0.33,1,true,true,false,0.96,1.39,0.42,-0.15,2.53,-3.18,false,10,false,true,0.46,59.70,12.01,0.00,67,"",TP,TP,
T98,lote4_02,Variational,short,77469.68,09-02 10:11,09-02 08:11,Juan,mal,-0.34,0.82,false,DO,1.55,0,false,true,true,1.24,0.73,0.31,0.41,0.77,5.24,false,3,true,false,0.71,31.90,36.44,0.00,160,"",TP,TP,es en ese precio pero en la vela de las 10:11
T100,lote4_02,Nado,long,76750.00,09-02 15:02,09-02 13:02,Juan,mal,-0.66,-1.53,true,rVAL,-0.29,1,false,false,false,1.55,1.33,0.53,0.61,-1.50,-2.52,true,20,false,true,0.36,40.50,2.88,0.35,5,"",TP,TP,es en la vela de las 15:01
T99,lote4_02,Variational,long,76807.41,09-02 15:04,09-02 13:04,Juan,mal,-0.52,-1.45,true,rVAL,1.12,0,true,false,false,1.55,1.37,0.35,0.09,0.29,-0.04,true,18,false,true,0.39,42.10,1.49,0.85,3,"",TP,SL,es en la vela de las 15:02
T91,lote4_01,Variational,long,77056.45,09-02 19:30,09-02 17:30,Juan,mal,-0.03,-1.00,true,wVWAP −1σ,0.04,2,true,false,false,0.98,1.14,0.37,0.37,-0.46,-8.15,false,13,false,true,0.55,44.20,10.24,0.00,48,"",TP,TP,"es en la vela de las 19:30, hay varios trades ahi, pero por la hora considero que es ese"
T92,lote4_01,Variational,long,77195.44,09-03 04:09,09-03 02:09,Juan,mal,-0.23,-0.76,false,VWAP sesión,-0.81,0,false,false,false,1.54,0.61,0.32,-0.67,-4.18,-1.03,false,7,false,true,0.42,44.00,16.32,0.00,26,"",TP,TP,"en ese horario no hay ningun trade, es a las 04:09"
T93,lote4_01,Variational,long,77198.60,09-03 07:29,09-03 05:29,Juan,mal,-1.08,-0.76,false,VWAP −1σ,-0.35,1,false,false,false,2.12,2.91,0.99,-0.07,-7.56,-6.39,true,21,false,true,0.26,62.60,15.33,0.71,96,"",TP,TP,es en la vela de las 07:29
T85,lote3_05,Variational,long,78967.57,09-03 16:09,09-03 14:09,Juan,mal,2.10,1.84,false,pwVWAP,0.43,1,true,true,true,1.19,2.03,1.72,-0.23,1.67,4.82,false,16,true,true,0.99,78.00,30.16,2.35,110,"",SL,SL,vela de 16:04 o por ahi
T86,lote3_05,Variational,short,81820.43,09-03 23:35,09-03 21:35,Juan,mal,-1.44,-2.51,true,PWH,2.93,0,false,false,false,6.70,5.80,2.67,-0.24,-5.06,-6.16,true,113,false,false,0.91,102.60,9.48,0.79,229,"",TP,TP,es en la vela de 23:35
T87,lote3_05,RISE,long,79664.00,09-04 14:37,09-04 12:37,Juan,mal,-2.26,0.57,true,H4 13EMA,-0.34,2,false,false,false,2.95,14.84,9.74,-0.29,-7.86,-8.25,false,281,true,true,0.02,191.70,2.20,0.45,5,"",TP,TP,vela de 14:37
T88,lote3_05,Variational,long,79628.18,09-04 14:38,09-04 12:38,Juan,mal,-2.28,0.55,true,pdVWAP,-0.55,0,false,false,false,2.30,16.76,6.34,-0.24,-7.52,-8.24,true,330,true,true,0.12,199.70,2.40,0.00,4,"",TP,TP,vela de 14:38
T89,lote3_05,Variational,long,79330.64,09-04 15:37,09-04 13:37,Juan,mal,-1.63,0.35,true,H4 21EMA,0.60,0,false,false,false,3.93,3.25,1.37,-0.32,-3.53,-5.47,true,55,true,true,0.16,123.20,0.70,0.57,8,"",TP,TP,vela de 15:37
T90,lote3_05,RISE,long,79402.30,09-04 15:37,09-04 13:37,Juan,mal,-1.53,0.39,true,H4 21EMA,1.18,0,false,false,false,3.93,3.25,1.37,-0.32,-3.53,-5.47,true,55,true,true,0.19,123.20,0.18,1.07,5,"",SL,SL,vela de 15:37
T83,lote3_04,Variational,short,79236.05,09-07 22:05,09-07 20:05,confirmada,bien,0.48,0.48,false,dPOC,-5.98,0,true,false,false,1.30,0.92,0.15,0.53,1.95,-7.18,false,12,false,false,0.33,20.50,2.04,1.38,7,"",SL,SL,
T84,lote3_04,Variational,short,79154.94,09-08 04:34,09-08 02:34,confirmada,bien,0.71,0.59,false,pdPOC,0.44,1,true,true,true,2.00,1.85,1.30,-0.21,1.60,3.16,false,15,true,false,0.37,41.80,19.85,1.28,228,"",SL,SL,
T79,lote3_03,Variational,long,77946.64,09-08 15:55,09-08 13:55,Juan,mal,-1.44,-1.75,true,VWAP −1σ,-1.79,0,false,false,false,0.94,7.45,2.42,0.03,-0.51,-6.60,true,61,false,true,0.17,96.90,1.39,0.08,2,VWAP −1σ,TP,SL,vela de 15:55
T80,lote3_03,Variational,long,78265.17,09-08 16:40,09-08 14:40,Juan,mal,-0.55,-1.12,true,rVAL,0.92,0,true,true,true,0.92,1.94,0.93,-0.64,0.17,7.07,false,12,false,true,0.34,65.30,11.03,0.00,120,"",TP,TP,vela 16:41
T81,lote3_03,Variational,long,78827.83,09-09 06:22,09-09 04:22,Juan,mal,0.95,-0.08,false,VWAP +1σ,-0.14,1,true,true,true,0.71,0.65,0.27,0.06,-1.92,6.72,false,3,false,true,0.78,35.70,14.35,0.00,54,dVAH / VWAP +2σ,TP,TP,vela 06:22
T73,lote3_02,Nado,long,76950.00,09-10 15:35,09-10 13:35,Juan,mal,-1.38,-2.41,true,VWAP −1σ,-2.48,0,true,false,false,1.32,2.86,1.59,0.09,2.09,-5.28,false,20,false,true,0.15,85.60,1.66,0.35,2,"",TP,TP,vela de 15:35
T74,lote3_02,Variational,long,77027.55,09-10 18:45,09-10 16:45,confirmada,bien,-1.03,-2.03,true,VWAP −1σ,-0.28,2,true,true,false,1.33,1.39,0.56,0.55,2.16,-3.45,false,22,false,true,0.20,51.90,9.75,0.00,50,"",TP,TP,
T75,lote3_02,Variational,long,76497.51,09-11 14:32,09-11 12:32,Juan,mal,-1.49,-1.98,true,pdVAL,-0.08,2,false,false,false,13.36,23.11,8.90,-0.12,-3.18,-2.35,true,213,false,true,0.32,173.30,17.86,0.00,91,"",TP,TP,vela 14:32
T76,lote3_02,lista,long,76438.91,09-11 14:32,09-11 12:32,Juan,bien,-1.70,-2.04,true,pdVAL,-0.42,2,false,false,false,13.36,23.11,8.90,-0.12,-3.18,-2.35,true,213,false,true,0.28,173.30,18.17,0.00,91,"",TP,TP,vela 14:34
T77,lote3_02,Nado,long,76973.00,09-11 14:34,09-11 12:34,Juan,mal,0.27,-1.45,true,rolling VWAP,-0.01,2,false,false,true,13.36,26.92,12.16,0.31,-0.25,0.76,true,224,false,true,0.65,202.60,13.92,0.00,89,"",TP,TP,vela 14:34
T78,lote3_02,Variational,short,77538.99,09-11 19:47,09-11 17:47,Juan,mal,0.23,0.86,false,pdVWAP,0.91,0,true,true,true,1.70,1.24,0.62,0.01,5.09,6.41,false,7,true,false,0.39,47.00,1.49,1.71,8,"",SL,SL,vela 19:47
T66,lote3_01,Variational,long,76878.41,09-13 16:07,09-13 14:07,confirmada,bien,-0.16,-1.38,true,VWAP sesión,-2.00,0,true,true,true,1.92,1.98,0.70,0.69,2.89,11.20,false,0,false,true,0.46,18.90,26.61,0.00,185,H4 21EMA,TP,TP,
T67,lote3_01,Variational,short,77204.60,09-14 00:00,09-13 22:00,confirmada,bien,-0.73,1.00,true,wVWAP −1σ,0.20,2,true,true,true,4.27,0.66,0.41,0.61,5.26,2.52,false,0,true,false,0.75,13.80,36.50,0.00,148,MNDAY-L / VWAP −2σ / VWAP −2σ semanal,TP,TP,
T68,lote3_01,Variational,short,76969.69,09-14 00:08,09-13 22:08,Juan,mal,0.22,1.25,false,VWAP sesión,-0.86,0,true,true,true,7.57,7.09,2.94,-0.38,4.48,4.28,false,6,true,false,0.51,61.00,5.12,0.39,72,"",TP,TP,vela 00:08
T72,lote3_01,Variational,short,78206.60,09-14 15:51,09-14 13:51,Juan,mal,-1.33,-1.33,true,dVAH,0.59,0,false,false,false,2.54,5.83,3.96,0.05,-2.11,-5.75,true,31,false,false,0.86,106.40,1.61,0.90,7,"",TP,SL,vela 15:51
T65,lote2_05,Variational,short,79217.09,09-14 22:49,09-14 20:49,confirmada,bien,-1.60,-1.60,true,pwVAH,3.87,0,true,true,false,0.82,0.81,0.41,0.81,2.36,-4.14,false,3,false,false,0.88,47.90,26.52,0.83,233,VWAP −2σ,TP,TP,
T58,lote2_04,Variational,long,76279.86,09-15 15:55,09-15 13:55,Juan,mal,-1.76,-1.95,true,MNDAY-L,-0.82,0,false,false,false,0.89,4.45,2.66,-0.35,-0.82,-8.16,false,42,false,true,0.09,109.70,3.79,0.00,5,dVAL,TP,TP,vela 15:55
T59,lote2_04,Nado,long,76281.00,09-15 15:56,09-15 13:56,Juan,mal,-1.75,-1.94,true,MNDAY-L,-0.82,0,false,false,false,0.75,3.72,2.75,0.08,-1.83,-6.89,false,35,false,true,0.09,108.30,3.76,0.00,4,dVAL,TP,TP,vela 15:56
T60,lote2_04,Variational,long,75793.30,09-15 16:53,09-15 14:53,Juan,mal,-1.79,-2.09,true,VWAP −2σ,1.32,0,false,false,false,1.55,6.71,3.40,-0.08,-3.85,-4.87,true,101,false,true,0.08,105.40,13.81,0.17,162,"",TP,TP,vela 16:53
T61,lote2_04,Nado,long,75847.00,09-15 17:01,09-15 15:01,confirmada,bien,-1.64,-1.98,true,PWL,-1.57,0,true,false,false,0.70,5.05,1.89,-0.29,0.11,-6.68,false,68,false,true,0.10,110.20,13.35,0.00,154,"",TP,TP,
T63,lote2_04,Variational,long,75430.69,09-16 00:26,09-15 22:26,Juan,mal,-1.50,-1.67,true,H4 200EMA,1.65,0,false,false,false,2.64,1.92,0.67,0.19,-1.64,-5.82,true,30,false,true,0.15,73.60,6.72,0.00,179,"",TP,TP,es en la vela 00:26
T62,lote2_04,Nado,long,75476.00,09-16 00:27,09-15 22:27,Juan,mal,-1.44,-1.63,true,dVAL,-1.83,0,true,false,false,1.04,2.01,0.32,0.52,0.14,-3.40,false,30,false,true,0.16,78.80,6.20,0.37,178,"",TP,TP,vela 00:27
T64,lote2_04,Nado,long,75507.00,09-16 10:45,09-16 08:45,confirmada,bien,-1.50,-1.43,true,pdVAL,0.65,0,true,true,false,0.69,0.55,0.34,0.35,3.18,-6.81,false,2,false,true,0.23,38.90,21.26,0.00,199,"",TP,TP,
T39,lote2_02,Nado,long,75509.00,09-16 19:54,09-16 17:54,Juan,mal,-1.42,-1.30,true,pdVAL,0.46,1,false,false,false,2.43,2.59,1.20,0.60,-0.20,-5.36,true,30,false,true,0.19,59.90,7.21,1.43,6,VWAP +1σ,TP,TP,vela 19:54
T42,lote2_02,Variational,long,75453.72,09-16 19:54,09-16 17:54,Juan,mal,-1.71,-1.35,true,rVAL,-0.22,2,false,false,false,2.43,2.59,1.20,0.60,-0.20,-5.36,true,30,false,true,0.13,59.90,8.07,0.58,6,VWAP +1σ,TP,TP,vela 19:54
T44,lote2_02,Nado,long,75518.00,09-16 20:02,09-16 18:02,Juan,mal,-1.33,-1.26,true,pdVAL,0.27,4,true,true,false,9.22,8.41,5.08,-0.23,-0.32,-2.44,false,59,false,true,0.20,132.50,6.96,0.00,6,pdVWAP,TP,TP,vela 20:02
T41,lote2_02,Variational,long,75533.68,09-16 20:03,09-16 18:03,Juan,mal,-1.25,-1.25,true,dVAL,-0.28,4,true,true,false,9.22,9.36,5.53,0.01,0.99,-0.95,true,67,false,true,0.25,149.60,6.28,0.00,5,pdVWAP,TP,TP,vela 20:03
T50,lote2_02,Variational,short,76195.07,09-16 20:10,09-16 18:10,confirmada,bien,-1.59,0.65,true,rVAH,0.04,2,false,false,false,2.79,18.66,7.79,0.44,-3.51,-2.67,true,179,true,false,0.72,201.20,5.66,0.00,26,"",TP,TP,
T43,lote2_02,Nado,long,75842.00,09-16 20:29,09-16 18:29,Juan,mal,0.07,-0.95,false,VWAP sesión,0.09,4,false,true,true,1.45,5.38,1.77,-0.11,-0.91,0.52,false,39,false,true,0.44,165.70,1.07,0.09,1,dVAH / PWL / VWAP +1σ,TP,SL,vela 20:29
T46,lote2_02,Nado,long,75218.00,09-16 20:37,09-16 18:37,confirmada,bien,-2.32,-1.49,true,VWAP −2σ,-0.42,1,false,false,false,5.14,7.14,3.74,-0.20,-4.52,-2.23,true,57,false,false,0.11,192.80,5.85,0.00,89,H4 13EMA,TP,TP,
T48,lote2_02,Variational,short,76182.52,09-16 20:44,09-16 18:44,Juan,mal,-1.48,0.62,true,VWAP +1σ,0.54,0,false,false,false,2.72,12.74,5.11,0.22,-1.89,-3.67,false,102,true,false,0.75,223.90,4.16,0.00,43,"",TP,TP,vela 20:44
T45,lote2_02,Nado,long,75496.00,09-16 20:58,09-16 18:58,Juan,mal,-1.24,-1.22,true,dVAL,0.05,4,false,false,false,0.72,5.39,4.32,-0.04,-4.47,-0.58,false,46,false,true,0.30,174.20,3.88,0.00,6,"",TP,TP,vela 20:58
T49,lote2_02,Variational,short,75920.39,09-16 21:15,09-16 19:15,Juan,mal,-0.44,0.84,true,PWL,-0.70,0,true,false,false,1.25,4.62,2.36,-0.57,-2.23,-0.99,false,38,true,false,0.58,143.60,4.72,0.03,12,"",TP,TP,vela 21:15
T51,lote2_02,Variational,short,75841.62,09-16 22:35,09-16 20:35,Juan,mal,-0.10,0.88,true,VWAP sesión,0.40,1,true,true,false,1.08,1.19,0.43,-0.35,2.22,-6.71,false,5,true,false,0.53,62.00,-2.71,5.23,7,PWL,SL,SL,vela 22:35
T52,lote2_02,Variational,long,76162.07,09-17 03:06,09-17 01:06,Juan,mal,-2.67,-0.58,false,DO,-0.97,0,false,false,false,1.81,0.74,0.62,-0.16,-5.29,0.39,false,6,false,true,-0.02,33.50,14.93,0.00,26,"",TP,TP,vela 03:06
T53,lote2_02,Nado,long,76223.00,09-17 03:17,09-17 01:17,Juan,mal,-1.69,-0.53,false,VWAP −2σ,0.57,0,false,false,false,2.34,0.65,0.40,-0.44,0.24,-4.78,false,7,false,true,0.17,43.60,12.34,0.00,15,"",TP,TP,vela 3:17
T54,lote2_02,Variational,long,76111.13,09-17 04:25,09-17 02:25,Juan,mal,-1.70,-0.63,false,pdVAH,-0.16,1,false,false,false,2.75,1.68,1.20,0.45,-0.63,-8.53,true,13,false,true,0.10,44.40,11.43,0.00,156,dVAH / mVAL,TP,TP,vela 04:25
T55,lote2_02,Nado,long,76205.00,09-17 04:34,09-17 02:34,Juan,mal,-1.11,-0.54,false,DO,0.26,4,true,false,false,1.52,1.42,0.50,0.37,1.76,-11.54,false,12,false,true,0.23,40.30,7.94,0.00,59,"",TP,TP,ese trade se habia abierto a las 04:34 pero duro bastante tiempo
T57,lote2_02,Variational,long,76250.45,09-17 15:47,09-17 13:47,confirmada,bien,-1.04,-0.50,false,VWAP −1σ,-0.12,1,false,false,false,0.78,5.92,1.85,0.37,-2.92,-7.92,false,56,false,true,0.22,85.50,9.64,0.00,41,"",TP,TP,
T56,lote2_02,Variational,long,76429.16,09-17 16:05,09-17 14:05,Juan,mal,-0.32,-0.33,false,H4 13EMA,0.04,2,false,true,false,1.28,3.28,0.99,-0.40,0.70,-4.33,false,29,false,true,0.37,99.00,6.77,0.00,23,"",TP,TP,vela 16:05
T35,lote2_01,Variational,long,76272.64,09-17 17:15,09-17 15:15,confirmada,bien,-1.07,-0.48,false,dVAL,-0.23,2,false,false,false,1.21,2.30,1.07,0.01,-2.16,-8.89,true,12,false,true,0.24,69.80,9.73,0.00,140,"",TP,TP,es ahi pero un poco mas arriba
T36,lote2_01,Variational,long,76521.97,09-18 00:34,09-17 22:34,Juan,mal,-0.16,-0.24,true,dPOC,0.49,1,true,false,false,0.58,0.80,0.24,-0.01,1.30,-9.93,false,2,false,true,0.45,26.50,-3.49,9.17,6,"",SL,SL,vela 00:34
T37,lote2_01,Variational,long,76932.35,09-18 04:50,09-18 02:50,Juan,mal,1.18,0.16,false,7D rVWAP,0.33,1,false,true,true,0.81,1.66,0.85,0.83,-2.79,7.31,false,11,true,true,0.87,27.30,24.48,0.00,168,dVAH,TP,TP,vela 04:50
T38,lote2_01,Variational,long,77437.13,09-18 06:56,09-18 04:56,Juan,mal,1.05,0.65,false,VWAP +1σ,0.49,1,true,true,true,2.94,1.02,0.46,0.89,5.72,2.23,false,5,true,true,0.88,33.10,6.40,0.00,5,dVAH,TP,TP,vela 06:56
T23,lote1_05,Variational,long,81138.54,09-21 01:37,09-20 23:37,Juan,mal,1.08,1.58,false,rVAH,0.70,0,false,false,true,1.51,0.86,0.28,0.37,-2.58,-0.13,false,1,true,true,0.74,33.50,30.28,0.00,105,MNDAY-H,TP,TP,vela 01:37
T27,lote1_05,Variational,short,81743.19,09-21 02:48,09-21 00:48,Juan,mal,-0.78,-0.78,true,dPOC,0.09,3,false,false,false,6.04,4.54,2.32,0.05,-1.07,-7.64,false,36,false,false,0.86,80.10,2.97,0.00,14,"",TP,TP,vela 02:48
T24,lote1_05,Variational,long,81789.02,09-21 03:10,09-21 01:10,Juan,mal,1.14,1.14,false,dVAH,-0.29,3,true,true,true,1.39,1.76,0.69,0.45,1.62,4.50,false,8,true,true,0.93,63.00,0.21,1.06,3,dVAH,SL,SL,"vela 03:05, malos precios no coinciden con las velas del trader."
T29,lote1_05,TxFlow,short,81763.50,09-21 03:24,09-21 01:24,confirmada,bien,-0.41,-0.41,true,dPOC,-0.18,1,false,false,false,6.48,5.21,2.39,0.23,-2.41,-2.58,true,46,false,false,0.63,82.30,10.57,2.16,32,MNDAY-L,SL,SL,
T28,lote1_05,Variational,short,81580.05,09-21 03:31,09-21 01:31,confirmada,bien,0.59,0.59,true,VWAP −1σ,0.67,0,true,true,false,2.26,8.06,1.99,-0.40,1.29,0.89,false,67,false,false,0.44,107.70,6.70,0.00,25,MNDAY-L,TP,TP,
T30,lote1_05,Variational,short,81412.22,09-21 04:30,09-21 02:30,confirmada,bien,0.27,0.27,true,rVAH,0.08,1,false,false,false,1.25,2.07,0.87,0.61,-0.91,2.81,false,16,false,false,0.45,58.70,4.86,0.00,5,pdVAH,TP,TP,
T25,lote1_05,Variational,long,81015.48,09-21 04:48,09-21 02:48,Juan,mal,-1.57,-1.57,false,rolling VWAP,1.17,0,false,false,false,0.81,1.47,0.55,-0.39,0.11,-2.64,false,17,true,true,0.14,56.00,15.83,0.00,220,"",TP,TP,"vela 04:48, la grafica de ese trade es ahi."
T31,lote1_05,Variational,short,81391.89,09-21 06:03,09-21 04:03,Juan,mal,0.28,0.28,true,VWAP sesión,-2.48,0,false,true,false,1.10,0.52,0.21,0.32,0.71,-1.96,false,3,false,false,0.43,32.50,4.98,0.06,28,dVAL,TP,TP,vela 06:03
T26,lote1_05,Variational,long,81639.22,09-21 09:54,09-21 07:54,Juan,mal,0.56,0.56,false,dPOC,0.62,0,true,true,false,1.42,1.03,0.40,-0.29,0.79,0.70,false,0,true,true,0.62,42.40,83.28,0.00,104,MNDAY-H,TP,TP,vela 09:54
T32,lote1_05,Variational,long,85039.97,09-21 15:44,09-21 13:44,Juan,mal,1.13,1.13,false,dPOC,0.42,1,true,false,false,0.77,4.66,1.50,0.12,0.95,-0.26,false,46,true,true,0.91,125.50,6.15,0.20,8,MNDAY-H,TP,TP,vela 15:44
T34,lote1_05,Variational,long,85369.03,09-21 15:49,09-21 13:49,Juan,mal,1.32,1.32,false,MNDAY-H,-1.31,0,true,true,true,2.82,5.44,2.22,-0.24,2.33,0.87,false,32,true,true,0.96,151.70,3.02,0.00,3,MNDAY-H,TP,TP,vela 15:49
T33,lote1_05,Variational,long,85350.79,09-21 16:21,09-21 14:21,confirmada,bien,1.18,1.18,false,dPOC,2.02,0,true,true,true,1.53,4.03,2.78,-0.03,2.02,1.45,false,51,true,true,0.91,126.20,8.12,0.00,47,MNDAY-H,TP,TP,
T18,lote1_04,Variational,long,85654.98,09-22 16:35,09-22 14:35,Juan,bien,-0.41,0.51,true,rVAL,1.09,0,false,false,false,2.42,1.85,1.34,-0.07,-3.85,-3.61,false,41,true,true,0.37,95.20,9.63,1.84,71,"",SL,SL,"vela 16:36, mas abajo"
T08,lote1_03,TxFlow,long,83943.10,09-26 22:53,09-26 20:53,Juan,mal,-0.71,-0.61,true,VWAP −1σ,0.81,0,false,false,false,1.39,4.17,0.80,0.44,-2.96,-0.61,false,15,true,true,0.32,36.20,14.99,0.00,186,"",TP,TP,vela 22:53
T07,lote1_03,Nado,long,83970.00,09-26 22:57,09-26 20:57,Juan,mal,-0.45,-0.59,true,pdPOC,-0.28,1,true,false,false,0.56,3.02,0.55,-0.51,4.02,0.44,false,7,true,true,0.37,32.50,15.92,0.00,182,"",TP,TP,vela 22:58
T09,lote1_03,Variational,long,84360.01,09-27 19:15,09-27 17:15,confirmada,bien,-1.43,-0.29,true,dVAL,0.31,1,false,false,false,2.06,3.12,1.19,-0.21,-1.48,-5.76,false,23,true,true,0.13,29.40,15.44,0.00,105,"",TP,TP,
T10,lote1_03,lista 25x,long,83275.60,09-28 05:34,09-28 03:34,alta,nose,-1.37,-1.37,true,dVAL,-1.10,0,false,false,false,3.34,4.56,3.05,-0.17,-4.20,-4.88,true,48,false,true,0.05,55.30,3.62,0.91,9,pwVAL,TP,TP,
T11,lote1_03,lista 25x,short,83512.00,09-28 07:00,09-28 05:00,alta,nose,0.69,0.69,false,pwVAL,0.93,0,false,false,false,2.26,0.67,0.44,0.53,0.49,-6.10,false,7,true,false,0.18,23.50,34.52,0.00,38,MNDAY-L,TP,TP,
T12,lote1_03,lista 25x,long,83086.50,09-28 07:24,09-28 05:24,alta,nose,-1.36,-1.36,true,dVAL,-0.69,0,false,false,false,10.20,5.12,2.09,-0.37,-5.18,-7.45,true,76,false,true,0.06,55.90,0.58,1.83,4,dVAL,SL,SL,
T15,lote1_03,Variational,long,83045.51,09-28 07:25,09-28 05:25,media,nose,-1.42,-1.42,true,dVAL,-1.43,0,false,false,false,10.20,5.29,2.15,-0.12,-5.41,-7.86,true,78,false,true,0.04,56.00,1.27,0.97,3,dVAL,TP,SL,
T13,lote1_03,lista 25x,long,83096.50,09-28 07:27,09-28 05:27,alta,nose,-1.30,-1.30,true,dVAL,-0.49,1,false,false,false,10.20,5.93,3.04,0.19,-4.36,-6.79,true,87,false,true,0.07,59.30,0.39,0.19,1,dVAL,SL,SL,estos ultimos estan todos en cruces muy distintos y tiene otras capturas de trades abiertos pero no graficados.
T14,lote1_03,lista 25x,long,82779.90,09-28 07:39,09-28 05:39,alta,nose,-1.63,-1.63,true,dVAL,-0.80,0,false,false,false,4.04,5.67,2.61,-0.61,-5.59,-11.56,true,83,false,true,0.06,67.40,7.00,0.52,34,"",TP,TP,
T17,lote1_03,Variational,long,82836.19,09-28 17:23,09-28 15:23,Juan,mal,-1.01,-1.01,true,VWAP −1σ,-0.05,2,false,false,false,1.58,2.62,1.77,-0.24,-1.17,-6.81,false,21,false,true,0.13,104.20,14.41,0.04,113,VWAP +2σ / VWAP +2σ semanal / pdVAL,TP,TP,vela 17:23
T01,lote1_02,Variational,long,83462.69,09-28 18:16,09-28 16:16,Juan,mal,0.29,0.29,true,mVAH,-0.19,2,true,true,true,1.77,1.23,0.74,-0.53,0.24,7.15,false,11,false,true,0.38,61.90,12.81,0.00,60,VWAP +2σ / VWAP +2σ semanal / pdVAL,TP,TP,vela 18:16
T02,lote1_02,Variational,long,83651.94,09-28 19:11,09-28 17:11,confirmada,bien,0.57,0.57,false,dVAH,-1.54,0,false,false,true,1.04,1.40,0.53,0.35,-1.77,1.93,false,8,false,true,0.46,66.00,7.96,0.00,5,VWAP +2σ / VWAP +2σ semanal / pdVAL,TP,TP,
T03,lote1_02,Nado,long,83658.00,09-28 19:11,09-28 17:11,confirmada,bien,0.58,0.58,false,dVAH,-1.45,0,false,false,true,1.04,1.40,0.53,0.35,-1.77,1.93,false,8,false,true,0.46,66.00,7.89,0.00,5,VWAP +2σ / VWAP +2σ semanal / pdVAL,TP,TP,
T06,lote1_02,Variational,long,82915.15,09-29 05:18,09-29 03:18,Juan,mal,-0.75,-1.02,true,wVWAP −1σ,-0.21,2,false,false,false,1.81,0.54,0.35,0.16,-1.63,-2.60,true,5,false,true,0.20,37.90,30.63,0.00,239,"",TP,TP,vela 05:18
T04,lote1_02,Nado,long,83030.00,09-29 06:09,09-29 04:09,Juan,mal,-0.24,-0.77,true,dPOC,0.43,1,false,false,false,1.82,0.47,0.19,-0.70,-3.16,2.81,false,5,false,true,0.33,35.70,8.43,0.00,76,"",TP,TP,vela 06:09
T05,lote1_02,TxFlow,long,83135.40,09-29 07:42,09-29 05:42,Juan,mal,0.24,-0.54,true,VWAP sesión,0.88,0,false,false,false,1.96,0.98,0.24,0.44,-2.37,0.26,true,4,false,true,0.45,50.30,25.03,0.00,160,VWAP +2σ / VWAP +2σ semanal,TP,TP,vela 07:42
```

### 7.2 Perdidas (calaveras, 15; hora y precio aproximados, `toca` = el precio pasó por ahí en ±30 min; con `toca` = false la ubicación no es confiable y sus columnas tampoco: K07, K13 y K16, por ejemplo)

```csv
id,captura,lado,precio_aprox_trader,hora_aprox_trader,hora_utc,toca,z_sesion_lado,z_semana_lado,contra_rvwap,nivel1,dist1_atr,niveles_05atr,ash1_a_favor,xo_a_favor,ash5_a_favor,rvol_max5,vol15_rel,absorcion5,delta1,ret15_atr,ret60_atr,barrida60,burb_contra15,ema200_45m_a_favor,ema200_4h_a_favor,pos_rango_dia,atr14,mfe_atr,mae_antes_mfe_atr,min_hasta_mfe,nivel_fin,r1_1,r2_1
K16,lote4_03,long,78350.00,08-31 15:30,08-31 13:30,false,0.89,0.89,false,VWAP +1σ,-0.55,0,true,true,false,3.35,1.39,0.81,0.16,-0.40,-0.53,false,11,true,true,0.69,65.80,-1.71,3.29,1,H4 13EMA,SL,SL
K15,lote4_02,long,77020.00,09-02 04:00,09-02 02:00,true,-0.39,-1.62,true,pdVAL,0.66,0,true,false,false,1.05,2.22,0.44,0.66,1.95,-3.01,false,26,false,true,0.40,65.30,12.02,1.36,86,"",SL,SL
K14,lote4_02,long,77720.00,09-02 07:45,09-02 05:45,true,1.50,-0.42,false,dVAH,-0.74,0,true,true,true,1.52,0.68,0.34,-0.75,-1.22,3.58,false,10,false,true,0.94,30.70,0.83,0.66,4,dVAH,SL,SL
K12,lote3_05,long,81320.00,09-04 00:30,09-03 22:24,true,1.06,2.06,false,VWAP +1σ,1.38,0,false,false,false,3.77,1.91,1.37,-0.31,-2.51,-3.04,true,13,true,true,0.82,67.90,-0.71,1.78,1,"",SL,SL
K13,lote3_05,long,80220.00,09-04 13:45,09-04 11:45,false,-4.21,0.96,true,wVWAP +1σ,-1.57,0,false,true,true,1.18,0.53,0.18,0.31,-2.22,4.67,false,7,true,true,-0.28,37.50,29.26,0.00,44,"",TP,TP
K11,lote3_03,long,78620.00,09-09 17:10,09-09 15:10,true,-1.71,-0.65,true,rVAL,-0.06,2,false,false,false,3.76,8.18,3.33,0.01,-1.93,-2.40,true,75,false,true,0.14,152.40,-0.02,2.54,7,rVAL,SL,SL
K09,lote3_01,long,76970.00,09-14 00:15,09-13 22:14,true,-0.21,-1.25,true,VWAP sesión,-0.78,0,false,false,false,0.64,8.85,2.65,0.33,-5.29,-5.68,false,25,false,true,0.51,66.20,-0.78,2.10,1,"",SL,SL
K08,lote2_05,short,77520.00,09-14 06:15,09-14 04:15,true,-0.60,-0.60,true,H4 100EMA,1.38,0,false,true,false,2.07,0.91,0.45,-0.62,0.55,8.01,false,3,true,false,0.77,27.50,-0.03,2.36,4,"",SL,SL
K07,lote2_04,long,76070.00,09-15 04:00,09-15 02:00,false,-18.66,-3.17,true,PWL,1.30,0,false,false,false,1.32,1.31,0.43,-0.37,-2.30,-1.05,false,13,true,true,-3.23,38.30,51.35,0.00,27,"",TP,TP
K06,lote2_02,long,75670.00,09-16 20:30,09-16 18:31,true,-0.69,-1.11,true,DO,0.29,2,false,true,true,1.45,4.49,2.21,-0.23,0.08,1.10,false,27,false,true,0.31,173.60,0.80,0.41,1,rolling VWAP / wVWAP −1σ / VWAP sesión,SL,SL
K04,lote2_02,long,75940.00,09-17 00:15,09-16 22:16,true,0.47,-0.79,false,PWL,-1.80,0,true,false,false,1.00,1.94,0.27,0.32,-0.39,-4.79,false,19,false,true,0.59,44.70,-1.86,2.39,1,"",SL,SL
K05,lote2_02,long,76290.00,09-17 04:30,09-17 02:36,true,-0.62,-0.47,false,VWAP −1σ,1.70,0,true,false,false,1.52,1.07,0.47,-0.31,4.40,-8.65,false,6,false,true,0.35,39.50,6.05,0.08,57,"",TP,TP
K03,lote2_01,long,76570.00,09-18 00:45,09-17 22:45,false,0.05,-0.20,false,mVAL,0.08,1,true,true,false,2.20,0.58,0.32,0.48,6.75,-4.56,false,2,false,true,0.49,22.50,-7.08,9.06,3,"",SL,SL
K02,lote1_05,short,81470.00,09-21 03:00,09-21 01:02,true,1.02,1.02,true,VWAP −1σ,-0.05,2,true,true,false,0.69,2.88,1.25,0.05,4.07,-3.01,false,11,false,false,0.46,68.40,-0.90,1.61,1,"",SL,SL
K01,lote1_05,long,85970.00,09-21 16:35,09-21 14:35,true,1.51,1.51,false,dVAH,-0.26,2,true,true,true,3.58,4.86,2.19,0.10,4.94,7.09,false,39,true,true,1.00,117.40,0.13,0.57,1,dVAH / MNDAY-H,SL,SL
```

### 7.3 Excluidas por Juan (no se encontró el trade en el gráfico, duplicadas o lado dudoso)

```csv
id,captura,plataforma,lado,entrada,aprox,comentario_juan
T16,lote1_03,Variational,long,82908.09,09-28 07:40,no es ese tiempo ni precios. estos ultimos estan todos muy confusos porque grafico menos de las graficas que aparecen
T19,lote1_04,RISE,long,84160.3,09-23 18:00,esta la captura pero no el trade en el tv
T20,lote1_04,Variational,long,84212.67,09-23 18:00,esta la captura pero no el trade en el tv
T21,lote1_04,Variational,long,83659.56,09-24 11:30,esta la captura pero no el trade en el tv
T22,lote1_04,Variational,long,83723.82,09-24 11:15,esta la captura pero no el trade en el tv
T40,lote2_02,Nado,long,75748.0,09-16 20:00,"no hay mas ahi, son los 4 de antes"
T47,lote2_02,Variational,short,76043.79,09-16 20:05,no hay ahi
T69,lote3_01,Variational,short,76673.14,09-14 01:30,"no hubo nada ahi, era un long"
T70,lote3_01,Variational,long,77856.9,09-14 10:00,el long ese se dio en velas que no estan en el grafico
T71,lote3_01,Variational,short,78046.37,09-14 12:00,se dio en velas que no estan en el grafico
T82,lote3_03,Variational,long,78914.3,09-09 12:00,No hay ningun trade ahi.
T105,lote4_03,Variational,long,77896.54,09-01 16:15,"vela de 15:43, es el mismo trade que el t104"
```
