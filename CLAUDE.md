# Backtest scalping BTC 1m · sesión Asia → almuerzo NY

Proyecto de Juan Cruz. Se testea una estrategia discrecional de scalping en BTC 1m (longs y shorts,
sin comisiones) basada en dos indicadores propios de TradingView, más un estudio de la relevancia de
las etiquetas/niveles, de indicadores de volumen/OI/liquidaciones y de los VAH/VAL de años previos.

Los dos `.pine` en `spec/` son la ESPECIFICACIÓN. Ante cualquier duda sobre un cálculo, manda el
código Pine, no la intuición ni la documentación de TradingView.

- `spec/XO_Ribbon_EMA_VWAP_MTF_OHLC.pine` — EMAs XO, VWAP sesión/semana con σ, perfil diario, rolling, etiquetas.
- `spec/ash_rvol_leviathan.pine` — ASH v2 + Relative Volume (Leviathan).

---

## 0 · Reglas de trabajo (no negociables)

1. **Se trabaja por fases con validación.** Cada fase termina en una validación que hace Juan. Al llegar a esa
   validación: mostrar qué se hizo, qué se supuso, un ejemplo verificable a mano y **FRENAR**. No se
   empieza la fase siguiente sin la aprobación explícita de Juan en el chat.
2. **Nada de resultados de golpe.** Antes de cualquier número agregado (win rate, expectativa) se
   muestran casos individuales dibujados, para que Juan pueda detectar un error de definición.
3. **Sin lookahead.** Toda señal usa sólo información disponible en el instante de la decisión.
   En particular: fractales sólo confirmados, velas de 5m en formación reconstruidas desde 1m (§3.3),
   niveles de períodos previos sólo cuando el período cerró.
4. **Separación de períodos (§1).** Las definiciones (señal, swing del SL, invalidación) se calibran SOLO
   en 2023–2024. En 2025–2026 se investiga todo lo demás, siempre con walk-forward (§6c): ninguna regla
   se evalúa en los mismos datos con los que se eligió. Si el tramo final de reserva (§6c) se aprueba,
   ese tramo no se mira, ni se grafica, ni se usa hasta F8. Si por error se consulta, se avisa y se documenta.
5. **Todo supuesto no confirmado** va a `DECISIONES.md` con estado `PENDIENTE` y se consulta a Juan.
   Las decisiones confirmadas se anotan con fecha.
6. **Bitácora.** Cada hallazgo, bug encontrado o cambio de definición va a `BITACORA.md` con fecha.
7. **Unidades.** Resultados de trades siempre en R (riesgo = distancia entrada→SL). Distancias
   a niveles en R, en ticks y en ATR(14) de 1m.
8. **Idioma.** Todo lo que se le muestra a Juan va en español rioplatense, técnico y sin relleno.

---

## 1 · Parámetros confirmados por Juan

| Tema | Valor |
|---|---|
| Activo | BTC únicamente |
| Exchange | El que permita bajar todo el historial necesario → **Binance USD-M `BTCUSDT` perpetuo** (ver §2). Validación visual en TradingView contra `BINANCE:BTCUSDT.P` |
| Datos | desde **2022-01-01** hasta hoy (2022 = solo calentamiento: rolling 365D y niveles del año previo de 2023) |
| 2023–2024 | **calibración** de las definiciones: señal (§7), swing del SL (§4.1), cierre por invalidación (§5.1). Las marcas manuales de Juan van en este período |
| 2025–2026 | **investigación y test**: importancia de las etiquetas, TP, volumen/OI/liquidaciones, niveles de años previos, resultados de la estrategia. Con walk-forward (§6c) |
| Ventana operativa | desde la apertura de Asia hasta el almuerzo de NY: **00:00 UTC → 12:00 America/New_York**. En hora argentina: 21:00 → 13:00 ART con horario de verano en EE. UU. (EDT) y 21:00 → 14:00 ART sin él (EST). Convertir SIEMPRE con la zona `America/New_York`, nunca con offset fijo |
| ASH | Modo RSI · Length **16** · Smooth **4** · MA **EMA** · fuente close |
| XO | EMA rápida **11** · lenta **25** · fuente close |
| RVOL | volume / SMA(volume, 20) · umbrales 1.5 / 2.5 / 3.5 |
| VWAP | fuente **hl2** · curva 1 = sesión (ancla diaria 00:00 UTC) · curva 2 = semana (lunes 00:00 UTC) · bandas ±1σ y ±2σ |
| Perfil diario | velas de 1m · 24 filas · área de valor 70 % (dVAH/dVAL/dPOC) |
| Comisiones | ninguna |
| Stop loss | apenas más allá del **mínimo (long) / máximo (short) más reciente del swing en 1m**. NO es un número fijo de velas (ver §4.1). También puede venir marcado por un indicador de volumen/posiciones. **Se dispara por MARK PRICE** |
| Riesgo | **1 % del capital por operación** (1R = 1 % del equity) |
| Entrada | **al cierre de la vela de señal** de 1m |
| Take profit | NO es fijo: es objeto de investigación (§5). Filtro duro: **no se entra si el R hasta el objetivo es < 2** |
| Gestión | una posición a la vez; la posición abierta **corre hasta el SL o el TP**, salvo el cierre por invalidación (§5.1). Se puede **ampliar** con patas de 1 % cada una, **máximo 4 patas abiertas = 4 % de riesgo** (§4.3) |
| Duración | sin tope de tiempo definido |
| Calendario | se testea operar y no operar en **feriados de EE. UU.** y en **fines de semana** (§6d) |
| Setups | se estudian las dos cosas: continuación (5m alineado y cerca del precio) y rebote (5m lejos) |

---

## 2 · Datos

### 2.1 Fuente: `data.binance.vision` (archivo público, zips diarios/mensuales con `.CHECKSUM`)

Ruta base: `https://data.binance.vision/data/futures/um/{daily|monthly}/<dataset>/BTCUSDT/`

| Dataset | Uso |
|---|---|
| `klines/BTCUSDT/1m` | velas oficiales de 1m (last price). Incluye `taker_buy_volume` → CVD a 1m sin ticks |
| `aggTrades` | ticks con timestamp en ms y lado agresor (`is_buyer_maker`). Resolución intravela exacta del TP y CVD fino |
| `markPriceKlines/BTCUSDT/1m` | **disparo del SL** (mark price). Sólo existe a 1m → ver §4.2 |
| `indexPriceKlines/BTCUSDT/1m` | auxiliar para reconstruir la trayectoria del mark |
| `premiumIndexKlines/BTCUSDT/1m` | auxiliar (base mark−index) |
| `metrics` (diario) | open interest cada 5m (`sum_open_interest`, `sum_open_interest_value`) y ratios taker/long-short |
| `liquidationSnapshot` | **COBERTURA A VERIFICAR** en F0. Si no cubre 2025–2026, evaluar alternativas (§6b) y consultar a Juan antes de prometer el test |

Nota: los klines de **1s** existen sólo en spot, no en futuros. La resolución intravela en futuros sale de `aggTrades`.

Antes de bajar nada en F0: listar el bucket y **confirmar que cada dataset existe y cubre 2022-01 → hoy**.
Reportar la cobertura real a Juan.

### 2.2 Procesamiento y almacenamiento

- Verificar el `.CHECKSUM` de cada zip.
- `aggTrades` → barras de **1 segundo** (O, H, L, C, volumen, volumen taker buy, n.º de trades, timestamp
  del primer y último trade) en parquet particionado por mes. Borrar el zip crudo después de validar
  (el crudo de 2022–2026 ocupa decenas de GB; las barras de 1s son un orden de magnitud menos).
  Guardar los ticks crudos sólo de los días que haga falta auditar.
- Motor: Polars / DuckDB sobre parquet.
- Todo timestamp interno en **UTC, ms, int64**. La conversión a ART/NY es sólo para mostrar y para la ventana.

### 2.3 Controles de integridad (entran en la validación de F0)

- Minutos faltantes y duplicados por día; días incompletos.
- Velas de 1m reconstruidas desde aggTrades vs `klines` oficiales: OHLC exacto y volumen con
  diferencia relativa < 1e-6. Listar cualquier discrepancia.
- Mark 1m: huecos, y minutos donde |mark − last| supere un umbral (eventos de desacople para revisar).

---

## 3 · Réplica de indicadores (F1)

### 3.1 Qué replicar

- **ASH** (`ashCalc` del .pine): Bulls/Bears en modo RSI, `ma(EMA, ·, 16)` y suavizado `ma(EMA, ·, 4)`.
  Ojo: el default del archivo es 9/3 WMA; se usa 16/4 EMA.
- **XO**: EMA 11 y EMA 25 sobre close; cruce = `crossover/crossunder` simple.
- **VWAP de sesión y semanal** con σ (`f_vwap`: acumulación centrada en el primer precio del período,
  varianza ponderada por volumen). Reset en el cambio de día UTC / semana (lunes UTC).
- **Perfil diario** (§10 del .pine): reparto proporcional del volumen de cada vela de 1m entre las filas
  que toca, POC, expansión hacia la fila vecina de más volumen hasta el 70 %.
- **Rolling 24h** y **rVAH/rVAL**, **7D/30D/90D/365D** (ventana por tiempo calendario sobre velas
  diarias, hlc3), **DO/WO/MO/YO**, **PWH/PWL**, **MNDAY-H/L**, **pwVWAP**, **m/pm/pq/y VWAP·VAH·VAL**.
  Leer §10–§12 del .pine para las definiciones exactas de cada etiqueta y en qué visión aparece.
- **RVOL** del ASH.

### 3.2 Calentamiento

Las `ta.ema` de Pine se siembran con una SMA de la primera ventana: el valor depende de dónde empieza la
historia. Arrancar el cálculo desde 2022-01-01 y verificar que en 2023 la diferencia por semilla
es despreciable.

### 3.3 Timeframe de 5m (condición de "5m cerca del precio")

El cuadro MTF del ASH usa `request.security(..., lookahead_off)`: **en vivo muestra la vela de 5m EN
FORMACIÓN, en el historial de TradingView muestra la cerrada.** Lo que Juan ve al operar es la vela en
formación. Por eso: reconstruir en cada minuto la vela de 5m parcial a partir de los 1m cerrados y
calcular ASH/EMAs de 5m con ese valor provisional (estado de las EMAs = el de la última vela de 5m
cerrada + la actualización con la parcial). Implementar también la versión con vela cerrada y
comparar los resultados de las dos.

### 3.4 Validación de F1

Tabla con **10 timestamps** elegidos al azar dentro de la ventana operativa de 2023–2026 (distintos días y
horas, al menos uno lunes 00:0x UTC y uno en cambio de horario de EE. UU.) con: close, EMA11, EMA25,
ASH Bulls/Bears, RVOL, VWAP sesión ±σ1 ±σ2, VWAP semana ±σ1 ±σ2, dVAH, dVAL, dPOC, rVAH, rVAL, 7D, 30D,
DO, WO, PWH, PWL, MNDAY-H/L. Juan los compara con la ventana de datos de TradingView
(`BINANCE:BTCUSDT.P`, 1m). Tolerancias a acordar; toda discrepancia se explica antes de seguir.

---

## 4 · Motor de ejecución (F3)

### 4.1 Entradas, SL y R

- **Entrada (confirmado)**: al cierre de la vela de señal de 1m. El fill es a mercado, al precio del primer
  tick posterior al cierre (no al close de la vela). Reportar la diferencia promedio entre ese fill y el close.
- **SL (confirmado en espíritu, a operacionalizar)**: apenas más allá del mínimo (long) / máximo (short)
  **más reciente del swing en 1m**. No es un fractal de n velas fijo. Definiciones candidatas, todas
  sin lookahead (el extremo tiene que estar formado y superado en el momento de la entrada):
  1. **Extremo del retroceso**: el mínimo más bajo desde el último máximo de swing (lógica ZigZag),
     siempre que al cierre de la vela de señal ya exista al menos una vela con mínimo más alto.
  2. **Fractal de Williams** con n = 1, 2 y 3 velas por lado (solo los confirmados).
  3. **Mínimo desde el evento de la señal**: el mínimo más bajo desde que el ASH o las XO empezaron a girar.
  4. **Extremo marcado por volumen/posiciones**: el mínimo de la vela con un print grande de volumen
     agresivo, una liquidación o un salto de OI (burbujas tipo "big trades", §6), si está cerca del swing.
  El buffer se prueba en ticks, en % del precio y como fracción del ATR(14) de 1m. La definición que se
  queda se elige por **coincidencia con los SL que pondría Juan** en sus marcas (§7), no por el PnL.
- **Tamaño**: qty = (1 % × equity) / |fill − SL|. Resultados en R. La curva de equity se reporta con
  riesgo fijo sobre el capital inicial y con interés compuesto (1 % del equity vigente).
- **Apalancamiento (confirmado por Juan)**: el riesgo es siempre el 1 % de la cuenta. El apalancamiento solo
  cambia el margen inmovilizado, NO el riesgo. No se usa como filtro ni como variable de resultado.
  Único control de **factibilidad**: el nocional total abierto (todas las patas) = Σ(1 % × equity / distancia
  al SL en %) tiene que caber en equity × apalancamiento máximo del contrato. Se registra en cada trade
  el nocional requerido como múltiplo del equity y se marcan (sin descartarlos) los casos que no caben.
  El precio de liquidación no se modela: se asume margen suficiente para que el SL por mark llegue antes.
- **Distancia al SL**: registrar su distribución (ticks, %, ATR). Con swings a muy pocos ticks el fill a
  mercado y el slippage pesan más en R; eso se ve en la sensibilidad de §4.2, no se filtra.
- Una posición a la vez (confirmado), con ampliaciones (§4.3).
- **Entradas sólo dentro de la ventana** (confirmado). Una posición abierta corre hasta el SL o el TP
  aunque pase de las 12:00 NY. Como no hay tope de tiempo, se usa un tope técnico de 24 h solo para
  el cómputo y se reporta cuántos trades lo alcanzan (deberían ser casi cero).

### 4.2 Resolución intravela (lo que pidió Juan: que las liquidaciones/mechas dentro de la vela no distorsionen)

- **TP (last price, orden límite):** hora exacta = primer tick de aggTrades que alcanza el precio.
- **SL (mark price):** el mark histórico existe sólo a 1m. Para un minuto donde el mark 1m toca el SL:
  1. Si en ese minuto no se tocó el TP → SL, sin ambigüedad.
  2. Si en el mismo minuto también se tocó el TP → reconstruir una trayectoria sintética del mark con las
     barras de 1s de last + la base (mark − last) interpolada entre la apertura y el cierre del minuto;
     verificar que el sintético reproduce el high/low del mark 1m. Si el sintético ordena los eventos sin
     ambigüedad, se usa ese orden. Si no, **se cuenta como pérdida** (criterio conservador).
  3. Reportar SIEMPRE cuántos trades cayeron en el caso 2 y el resultado con los dos criterios
     (conservador y optimista), para ver cuánto depende la conclusión de esto.
- Mechas de last que no llegan al mark NO disparan el SL (es la razón de usar el mark).
- Si en el mismo minuto de la entrada se tocan el SL o el TP, sólo cuentan los ticks posteriores al fill.
- Sensibilidad: slippage del SL (orden de mercado) de 0, 1, 2 y 5 ticks, más un escenario con
  slippage proporcional al RVOL.

### 4.3 Ampliaciones (pyramiding)

Juan puede ampliar la posición abierta con una pata nueva cuando los indicadores vuelven a dar la señal
a favor. **Reglas confirmadas (2026-09-30):**
- Cada pata arriesga **1 % de la cuenta** contra **su propio SL** (el swing reciente de 1m al momento de
  esa entrada, con la misma definición de §4.1).
- Los SL **no se comparten ni se mueven**: la pata 1 cierra sus contratos en el SL 1, la pata 2 en el SL 2, etc.
  Cada pata es un trade independiente, con su fill, su SL, su TP y su resolución intravela.
- Cada pata tiene que cumplir **R ≥ 2 hasta su objetivo**, calculado desde su propio fill y su propio SL.
- **Máximo 4 patas abiertas a la vez** → el riesgo abierto nunca pasa del **4 %** de la cuenta. Con 4 patas
  abiertas, una nueva señal a favor se ignora (y se registra). Si una pata cierra (por TP o SL), se libera
  su lugar y se puede volver a ampliar.
- **SL escalonados**: con x patas abiertas hay x SL parciales; cada SL cierra solo los contratos de su pata.
  En un long, la pata más nueva suele tener el SL más alto (su swing es más reciente), así que en una
  reversión las patas se cierran de la más nueva a la más vieja.
- Solo se amplía en la dirección de la posición abierta. Una señal contraria con patas abiertas se
  ignora (una posición a la vez), pero se registra para medir cuántas se pierden por esto.

Consecuencias a medir y reportar:
- **Riesgo abierto simultáneo** (1 % a 4 %): distribución, tiempo pasado con 2, 3 y 4 patas, y frecuencia
  del peor escenario (las 4 patas tocan su SL en la misma reversión = −4 %).
- Rachas de pérdida medidas en % de la cuenta, no solo en R, porque una posición de 4 patas puede perder
  4R de golpe.
- Correlación entre patas de la misma posición: no son trades independientes para la estadística. Los
  IC por bootstrap se calculan **por bloques de posición**, no por pata.
- Contabilidad: id de posición + n.º de pata. Métricas por pata, por posición y de la estrategia con y
  sin ampliaciones.

### 4.4 Validación de F3

20 trades elegidos al azar (incluidos todos los tipos de ambigüedad), cada uno dibujado con velas de 1m,
el mark, las barras de 1s alrededor de la salida, la entrada, el SL, el TP y la anotación del motivo de salida.
Juan los audita.

---

## 5 · Take profit (objeto de investigación)

Para cada entrada candidata se guarda la trayectoria completa hacia adelante (hasta el SL o un horizonte máximo):
el MFE en R antes del SL, el tiempo hasta 1R/2R/3R/…, y la lista de niveles/etiquetas en la dirección
del trade con su distancia en R.

Familias de TP a comparar (todas deben poder definirse **ex ante**, porque el filtro R ≥ 2 se aplica
sobre el objetivo elegido en el momento de entrar):

- R fijo (2, 2.5, 3, 4…).
- Próximo nivel en la dirección del trade: VWAP de sesión, sus σ1/σ2, VWAP semanal y sus σ,
  dVAH/dVAL/dPOC, rVAH/rVAL, DO/WO, PWH/PWL, MNDAY-H/L, 7D/30D, yVAH/yVAL.
- Banda opuesta del VWAP según en qué zona se entró (debajo de −σ2, entre −σ1 y VWAP, etc.).
- Salidas dinámicas: trailing por fractal, cruce contrario de las XO, giro del ASH; parciales.
- Condicionamiento: zona del VWAP de entrada, criterio de entrada (continuación/rebote), RVOL de la
  vela de señal, estado de 5m.

Contra el sobreajuste: pocas reglas, definidas antes de mirar los resultados, y selección con walk-forward (§6c).

### 5.1 Cierre por invalidación (oscilación sobre la entrada)

**Regla de Juan (confirmada 2026-09-30):** se cierra cuando, **30 minutos** después de la entrada, el precio
sigue **cerca del precio de entrada** y en ese lapso los indicadores cambiaron varias veces, **mostrando
varias señales de apertura de posición**.

Operacionalización:
- K = 30 minutos desde el fill de la pata 1 (se evalúa al cierre de cada vela de 1m a partir del minuto 30).
- "Cerca de la entrada": |precio − fill| ≤ x R. x se calibra con las marcas de 2023–2024 (probar 0,25 / 0,5 / 0,75 R).
- "Varias señales": en la ventana desde la entrada hubo ≥ m señales de apertura (las de §7), con m ≥ 2.
  Variantes a comparar: contar señales en cualquier dirección, solo contrarias, o alternancia long/short.
- Al dispararse, se cierran **todas las patas** a mercado al cierre de esa vela (confirmado).
- **Se testean las dos versiones de la estrategia completa: con cierre por oscilación y sin él** (dejando
  correr hasta el SL/TP). Se reportan lado a lado en todas las tablas de resultados.
- Ojo con la interacción: si en esa oscilación aparece una señal a favor, puede abrir una ampliación
  (cumple R ≥ 2 cerca de la entrada). Registrar cuántas ampliaciones se abren en posiciones que después
  terminan cerradas por invalidación.

Para cada variante se reporta: trades cerrados antes, cuántos habrían terminado en SL y cuántos en TP
(costo de oportunidad), el R promedio al cierre y la expectativa neta frente a dejar correr hasta el SL/TP.

---

## 6 · Fases y validaciones

| Fase | Contenido | Validación de Juan |
|---|---|---|
| F0 | Cobertura del bucket, descarga, barras de 1s, integridad | Informe de cobertura + integridad |
| F1 | Réplica de indicadores y etiquetas | Tabla de 10 timestamps vs TradingView |
| F2 | Operacionalizar las señales (§7) | Coincidencia con las marcas manuales de Juan |
| F3 | Motor de ejecución (§4) | Auditoría de 20 trades dibujados |
| F4 | Continuación vs rebote: estadísticas separadas | Revisión de los casos límite de la clasificación |
| F5 | Estudio de etiquetas (§8) | Revisión de la metodología antes de los resultados |
| F6 | RVOL, CVD, OI, liquidaciones, burbujas de trades grandes como filtros y como marcadores del SL | Ídem |
| F7 | VAH/VAL/VWAP de años previos | Ídem (advertir el tamaño muestral) |
| F8 | Robustez: walk-forward completo, sensibilidades, tramo de reserva si se aprueba | Informe final |

---

## 6b · Indicadores de volumen y posiciones (F6)

- **RVOL** (el del ASH), **CVD** exacto desde aggTrades (lado agresor), **delta por vela**.
- **Burbujas de trades grandes** (como las del gráfico de referencia): reconstruir las órdenes a mercado
  desde aggTrades. Un aggTrade agrupa solo los fills al mismo precio; una orden que barre varios precios
  queda partida en varios aggTrades con el mismo timestamp y el mismo lado. Agrupar por (ms, lado) para
  recuperar la orden completa. El umbral de "grande" se define por percentil móvil del tamaño, no por un valor fijo.
- **OI**: variación cada 5m (desde `metrics`). Clasificación precio↑/OI↑, precio↑/OI↓, etc.
- **Liquidaciones**: Binance publica las liquidaciones en tiempo real, pero el archivo histórico público es
  parcial. En F0 se verifica qué hay para 2023–2026. Si no alcanza, alternativas en orden de preferencia
  (consultar a Juan antes de usar una paga):
  1. Proveedores de datos históricos de derivados (p. ej., Tardis.dev tiene liquidaciones de Binance
     futuros; verificar costo y si el primer día de cada mes es gratuito, que sirve como muestra).
  2. APIs de agregadores (p. ej., Coinalyze): verificar cuánta historia intradía entregan.
  3. **Proxy propio**: detectar cascadas de liquidación desde aggTrades + OI (órdenes a mercado grandes
     en ráfaga, en la dirección del movimiento, con caída simultánea del OI de 5m). Validar el proxy
     contra el tramo donde haya datos reales de liquidaciones.
- Dos usos: (a) **filtro**: si, dada una señal, separan a las ganadoras de las perdedoras; (b) **marcador
  del SL**: si el extremo con una burbuja grande o una liquidación funciona mejor como referencia del SL
  que el swing a secas.

## 6c · Esquema temporal y control de sobreajuste

- **2022**: solo calentamiento.
- **2023–2024 — calibración**: se fijan las definiciones de la señal, del swing del SL y del cierre por
  invalidación contra las marcas de Juan. Una vez aprobadas en F2, **se congelan**: en 2025–2026 no se
  vuelven a tocar.
- **2025–2026 — investigación y test**. Todo lo que implique ELEGIR (importancia de etiquetas, reglas de TP,
  filtros de volumen/OI, umbrales) se hace con **walk-forward trimestral**: la regla se elige con los
  trimestres anteriores y se mide en el siguiente. El resultado que vale es la concatenación de los
  trimestres medidos fuera de muestra, no el ajuste sobre todo el período.
- Los estudios puramente descriptivos (p. ej., qué pasa en el 1.er toque de dVAH) se pueden reportar sobre
  todo 2025–2026, pero cualquier regla que salga de ahí vuelve a pasar por el walk-forward.
- **Recomendación pendiente**: reservar el último tramo (p. ej., jul–sep 2026) sin mirar hasta F8, como
  confirmación final de la estrategia completa.

## 6d · Variantes de calendario (feriados de EE. UU. y fines de semana)

Cripto opera 24/7; lo que cambia en feriados y fines de semana es la participación (sin rueda de acciones
en NY, sin CME, menos volumen). Eso afecta al RVOL, al VWAP y a la reacción en los niveles.

**Clasificación de cada sesión** (la sesión = la ventana de 00:00 UTC a 12:00 NY de una fecha UTC):
- **Fin de semana**: sesiones que empiezan el sábado 00:00 UTC y el domingo 00:00 UTC (viernes 21:00 y
  sábado 21:00 en hora argentina). La sesión del lunes (domingo 21:00 ART) es día hábil. Tener en cuenta
  que el VWAP semanal se resetea el lunes 00:00 UTC y que el CME reabre el domingo a la tarde de NY.
- **Feriado de EE. UU.**: la fecha es feriado de la **NYSE** (bolsa cerrada), con el calendario oficial de
  2022–2026 (librería `holidays`, calendario NYSE, verificado contra la lista publicada por la NYSE).
  Categorías aparte:
  - **media rueda de la NYSE** (cierre 13:00 ET: día después de Thanksgiving, víspera de Navidad, etc.);
  - **feriado bancario federal con la bolsa abierta** (Columbus Day, Veterans Day), como variante secundaria.
- **Día hábil normal**: todo lo demás.

**Variantes a testear** (el filtro aplica a las ENTRADAS; una posición abierta el viernes puede seguir
corriendo durante el fin de semana hasta su SL/TP, y eso se reporta):

| Variante | Hábiles | Feriados EE. UU. | Fines de semana |
|---|---|---|---|
| A (base) | sí | no | no |
| B | sí | sí | no |
| C | sí | no | sí |
| D | sí | sí | sí |

Cada una se cruza con las dos versiones de invalidación (con y sin cierre por oscilación): 8 combinaciones.
Además, estadísticas descriptivas **por tipo de día** (hábil / feriado / media rueda / sábado / domingo):
cantidad de señales, win rate, expectativa, RVOL medio, rango de la sesión y comportamiento de las
etiquetas (§8) por tipo de día.

Aviso de muestra: entre 2025 y 2026 hay pocos feriados de la NYSE (~15). Sus estadísticas van a tener
intervalos de confianza muy anchos; se dice con los números y no se sacan conclusiones fuertes de ahí.

Para la calibración (§7): si Juan opera fines de semana, conviene que algunas de sus marcas caigan en
sábado o domingo, para verificar que las definiciones también funcionan con poco volumen.

---

## 7 · Operacionalización de las señales (F2)

Regla de Juan, long (short = espejo):
1. En 1m, el ASH está **próximo a ponerse verde**.
2. El precio está **por encima de las XO** y las XO están **por cruzarse al alza**.
3. En 5m, el ASH y las EMAs están **próximos al precio** (continuación). Si no lo están, es un rebote:
   también se registra y se estudia por separado.

Definiciones candidatas (se calibran contra las marcas de Juan, no contra el PnL):
- ASH: brecha `g = Bulls − Bears` normalizada (por `Bulls + Bears` o por ATR); pendiente de g;
  velas proyectadas hasta el cruce; umbrales sobre la brecha.
- XO: `(EMA11 − EMA25) / ATR` negativo y en contracción; velas proyectadas hasta el cruce; precio > ambas.
- 5m cerca: `|precio − EMA 5m| / ATR5m`, brecha del ASH 5m, con la vela de 5m en formación (§3.3).

**Calibración**: Juan marca 30–50 entradas que habría tomado en `marcas/marcas.csv`
(`timestamp_utc, lado, tipo(continuacion|rebote), sl, tp_objetivo, motivo_tp, ampliaciones, cierre_invalidacion(si|no), comentario`),
**dentro de 2023–2024** (período de calibración). Con el SL y el TP que pondría él se
calibran también la definición del swing (§4.1) y la elección del objetivo (§5). Se ajustan las definiciones hasta maximizar la coincidencia (precisión y recall,
con tolerancia de ±N minutos) y se muestran los falsos positivos/negativos dibujados.

---

## 8 · Estudio de etiquetas (F5–F7)

- **Toque**: el precio entra en una tolerancia alrededor del nivel (en ticks y en ATR; se prueban varias).
- **Resultado del toque**: rechazo vs ruptura en los próximos N minutos, MFE/MAE, tiempo en la zona.
- **Placebo obligatorio**: niveles aleatorios con la misma distribución de distancia al precio. Con
  unos 20 niveles en un rango chico el precio siempre está cerca de alguno; sin placebo cualquier nivel "funciona".
- **Condicionar por** (hipótesis de Juan: importan al principio y dejan de importar cuando el precio oscila):
  número de toque (1.º, 2.º, n-ésimo), minutos desde que nació el nivel, cantidad de cruces previos,
  subsesión (Asia / Londres / NY), confluencia con otros niveles dentro de la tolerancia, distancia al VWAP de sesión.
- **Advertencia**: el VWAP de sesión se resetea a las 00:00 UTC, que es justo el inicio de la ventana.
  En los primeros minutos el dVWAP y sus σ son degenerados (pocas velas). Estudiar ese tramo por separado.
- **Valor marginal**: ¿estar cerca del nivel X mejora la expectativa de la estrategia base?
- **Comparaciones múltiples**: con tantas etiquetas y condiciones, corregir con Benjamini-Hochberg y
  reportar intervalos de confianza por bootstrap.
- **F7**: yVAH/yVAL/yVWAP (y PYH/PYL) de 2022, 2023, 2024 y 2025. BTC los visita poco → la muestra es chica; decirlo con los números.
- **Niveles extra, fuera del indicador de Juan** (vistos en un gráfico de referencia de otro trader).
  **Confirmado: entran al estudio**, con la misma metodología: **pdVWAP, pdVAH, pdVAL** (perfil del día previo),
  **PYH/PYL** (máximo y mínimo del año previo), **EMA 200 de 4h**, **nPOC** (POCs diarios todavía no revisitados).

---

## 9 · Reporte estándar de cada test

n, win rate, expectativa en R con IC 95 % por bootstrap, profit factor, R medio ganador/perdedor,
drawdown máximo en R, racha perdedora máxima, trades/día, desglose por subsesión, día de la semana,
mes y régimen (volatilidad por ATR diario), cantidad de trades con ambigüedad intravela y su efecto.

---

## 10 · Estructura del repo

```
spec/           .pine originales (no editar)
data/raw/       zips temporales
data/proc/      parquet: bars_1s/, klines_1m/, mark_1m/, index_1m/, metrics_5m/
src/            descarga, indicadores, señales, motor, estudios
tests/          tests de paridad con valores de TradingView (se alimentan de la tabla de F1)
marcas/         marcas manuales de Juan
reports/        gráficos y tablas por fase
DECISIONES.md   decisiones confirmadas y pendientes
BITACORA.md     hallazgos y cambios fechados
```

---

## 11 · Pendientes a confirmar con Juan

Confirmado el 2026-09-30: entrada al cierre de la vela · la posición corre hasta el SL/TP aunque pase
de la ventana · una posición a la vez, con ampliaciones · 5m en formación · riesgo del 1 % · SL en el
swing más reciente de 1m (no un fractal de n fijo) · sin tope de tiempo, con cierre discrecional por oscilación ·
ampliaciones: cada pata 1 % contra su propio SL, SL independientes, R ≥ 2 por pata ·
el apalancamiento no afecta el riesgo (solo el margen) · máximo 4 patas (4 % de riesgo) · calibración en
2023–2024 e investigación en 2025–2026 · niveles extra incluidos · invalidación a los 30 minutos cerca de la
entrada con varias señales de apertura; cierra todas las patas; se testea con y sin ese cierre ·
variantes de calendario: con/sin feriados de EE. UU. y con/sin fines de semana.

- [ ] Reservar jul–sep 2026 como confirmación final sin mirar (§6c).
- [ ] Definición del swing del SL y del buffer (se resuelve con las marcas, §4.1).
- [ ] Cierre por invalidación: x y m (se calibran con las marcas, §5.1).
- [ ] Cobertura de liquidaciones (se resuelve en F0).
