# Rectas punteadas de las capturas del trader: pendiente

Pedido de Juan (2026-11-01): calcular la pendiente de las trendlines del trader para ver si hay un grado en común.

## Lo que son en realidad

Las rectas amarillas punteadas de sus capturas **no son trendlines**: son la diagonal de la herramienta Long/Short de TradingView, que une el punto de entrada con el precio en el borde derecho de la caja verde/roja.

- 12 de 28 arrancan a 35 USD o menos del precio de entrada de una tarjeta de la misma captura (ej.: RISE long 79.402,3 → la recta arranca en 79.404; Variational long 82.915,15 → 82.929; Nado long 83.970 → 83.979).
- Quedan dentro de las cajas verde/roja de la herramienta, de la esquina de la entrada al borde derecho.
- Varias terminan exactamente en el mismo punto: 4 rectas de dos capturas terminan el 28-sep a las 13:37 UTC (su lista de órdenes tiene un cierre a las 13:39 UTC); otras 2 el 3-sep a las 13:27–13:33 UTC.

Por eso no hay pendiente de trendline para medir en estas capturas. Lo que miden estas rectas es la velocidad del precio entre su entrada y el final de la caja (su salida o el final del dibujo).

## Pendientes medidas (28 rectas, sin la dudosa)

- Ángulo en pantalla: mediana 34° (p25 24°, p75 42°), de 9° a 67°. 23 de 28 caen entre 20° y 50°, pero eso lo produce el autoescalado de TradingView (ajusta el rango de precio al alto de la ventana), no una regla del trader: el mismo trazo cambia de ángulo al cambiar el zoom.
- Ángulo normalizado (1 ATR de alto = 10 velas de ancho): mediana 32° (p25 21°, p75 45°), de 6° a 62°. Dispersión grande (coeficiente de variación 0,46): no hay un grado en común.
- En ATR(14) de 1m por vela: mediana 0,062 (p25 0,038, p75 0,101).
- En % por hora: mediana 0,19 % (p25 0,13 %, p75 0,25 %).
- Duración entrada → borde de la caja: mediana 8,2 h (p25 3,1 h, p75 11,8 h).

## Por recta

| Captura | # | Lado | Desde (UTC) | Hasta (UTC) | Precio inicio → fin | Horas | % por hora | ATR por vela | Ángulo normalizado | Ángulo en pantalla | Tarjeta que coincide |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lote1_02 | 1 | alcista | 09-29 03:20 | 09-29 11:42 | 82.929 → 84.433 | 8,4 | 0,21 | 0,082 | 39° | 50° | T06 Variational long 82.915,15 |
| lote1_02 | 2 | alcista | 09-28 12:16 | 09-28 13:37 | 83.735 → 83.782 | 1,3 | 0,04 | 0,011 | 6° | 9° | – |
| lote1_02 | 3 | alcista | 09-28 12:00 | 09-28 13:37 | 83.588 → 83.784 | 1,6 | 0,14 | 0,037 | 20° | 27° | – |
| lote1_03 | 1 | alcista | 09-26 22:00 | 09-27 10:10 | 83.979 → 85.046 | 12,2 | 0,10 | 0,093 | 43° | 33° | T07 Nado long 83.970,00 |
| lote1_03 | 2 | alcista | 09-28 04:08 | 09-28 13:37 | 83.449 → 83.799 | 9,5 | 0,04 | 0,014 | 8° | 14° | – |
| lote1_03 | 3 | alcista | 09-28 06:40 | 09-28 13:38 | 83.162 → 83.788 | 7,0 | 0,11 | 0,035 | 19° | 31° | – |
| lote2_01 | 1 | alcista | 09-18 00:15 | 09-18 08:39 | 76.689 → 78.833 | 8,4 | 0,33 | 0,111 | 48° | 34° | – |
| lote2_01 | 2 | alcista | 09-18 01:47 | 09-18 15:13 | 76.498 → 80.948 | 13,4 | 0,42 | 0,134 | 53° | 38° | T36 Variational long 76.521,97 |
| lote2_01 | 3 | bajista | 09-18 03:19 | 09-18 04:12 | 77.638 → 77.257 | 0,9 | -0,55 | -0,138 | -54° | -45° | – |
| lote2_02 | 1 | bajista | 09-16 20:04 | 09-16 22:03 | 76.333 → 75.694 | 2,0 | -0,42 | -0,153 | -57° | -62° | – |
| lote2_02 | 2 | alcista | 09-17 02:08 | 09-17 10:14 | 76.157 → 76.772 | 8,1 | 0,10 | 0,042 | 23° | 25° | T52 Variational long 76.162,07 |
| lote2_04 | 1 | bajista | 09-15 02:47 | 09-15 10:34 | 78.191 → 76.731 | 7,8 | -0,24 | -0,098 | -44° | -46° | – |
| lote2_05 | 1 | alcista | 09-14 00:31 | 09-14 13:47 | 76.451 → 78.264 | 13,3 | 0,18 | 0,059 | 31° | 33° | – |
| lote2_05 | 2 | bajista | 09-14 21:03 | 09-15 13:21 | 79.311 → 76.292 | 16,3 | -0,24 | -0,088 | -41° | -41° | – |
| lote3_01 | 1 | alcista | 09-14 03:57 | 09-14 13:51 | 77.026 → 78.401 | 9,9 | 0,18 | 0,066 | 33° | 36° | – |
| lote3_02 | 1 | alcista | 09-10 14:12 | 09-10 17:30 | 77.019 → 77.484 | 3,3 | 0,18 | 0,047 | 25° | 30° | T74 Variational long 77.027,55 |
| lote3_02 | 2 | alcista | 09-11 13:42 | 09-11 17:36 | 77.176 → 77.616 | 3,9 | 0,15 | 0,017 | 10° | 21° | – |
| lote3_03 | 1 | alcista | 09-08 14:33 | 09-08 15:35 | 78.277 → 78.692 | 1,0 | 0,52 | 0,117 | 50° | 65° | T80 Variational long 78.265,17 |
| lote3_03 | 2 | alcista | 09-09 04:35 | 09-09 05:15 | 78.936 → 79.294 | 0,7 | 0,68 | 0,196 | 63° | 73° | T82 Variational long 78.914,30 (dudosa) |
| lote3_04 | 1 | bajista | 09-07 20:04 | 09-07 22:30 | 79.254 → 78.831 | 2,4 | -0,22 | -0,157 | -57° | -49° | T83 Variational short 79.236,05 |
| lote3_04 | 2 | bajista | 09-08 02:34 | 09-08 12:07 | 79.186 → 77.920 | 9,6 | -0,17 | -0,058 | -30° | -34° | T84 Variational short 79.154,94 |
| lote3_05 | 1 | alcista | 09-03 08:30 | 09-03 21:24 | 79.404 → 81.995 | 12,9 | 0,25 | 0,055 | 29° | 23° | T90 RISE long 79.402,30 |
| lote3_05 | 2 | bajista | 09-03 21:28 | 09-04 11:53 | 81.691 → 79.407 | 14,4 | -0,20 | -0,058 | -30° | -24° | – |
| lote4_01 | 1 | alcista | 09-03 01:50 | 09-03 13:27 | 77.777 → 78.865 | 11,6 | 0,12 | 0,038 | 21° | 21° | – |
| lote4_01 | 2 | alcista | 09-03 05:29 | 09-03 13:33 | 77.167 → 78.868 | 8,1 | 0,27 | 0,084 | 40° | 40° | T92 Variational long 77.195,44 |
| lote4_01 | 3 | alcista | 09-02 13:43 | 09-02 23:34 | 76.701 → 77.587 | 9,9 | 0,12 | 0,035 | 20° | 21° | – |
| lote4_02 | 1 | alcista | 09-01 19:30 | 09-01 23:36 | 76.858 → 77.559 | 4,1 | 0,22 | 0,072 | 36° | 35° | – |
| lote4_02 | 2 | alcista | 09-02 01:53 | 09-02 03:28 | 76.763 → 77.717 | 1,6 | 0,78 | 0,188 | 62° | 67° | T95 Nado long 76.771,00 |
| lote4_03 | 1 | alcista | 08-31 01:00 | 08-31 18:41 | 77.291 → 79.142 | 17,7 | 0,13 | 0,034 | 19° | 40° | T101 Nado long 77.267,00 |

Método: cada recta se marcó a mano y se ajustó sola sobre los píxeles amarillos (residuo mediano 0,5 px). Precio por OCR del eje (recta sobre todas las etiquetas); hora por OCR del eje de tiempo con interpolación entre etiquetas (el eje no es lineal en estas capturas), UTC+2 → UTC. ATR = mediana del ATR(14) de 1m de Binance en el tramo. La captura del 1-oct no se usa (reserva). Capturas marcadas: `reports/trader_sep/trendlines/`.
