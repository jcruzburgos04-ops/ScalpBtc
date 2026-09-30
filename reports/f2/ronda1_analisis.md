# F2 · Ronda 1: respuestas de Juan a 40 señales (2023–2024)

Respuestas: 25 sí · 8 dudosa · 7 no (`marcas/revision_ronda1.json`). Medidas por caso: `reports/f2/ronda1_medidas.csv`.

| Medida | Sí (25) | Dudosa (8) | No (7) |
|---|---|---|---|
| Brecha ASH 1m, mediana |gn| | 0,050 | 0,054 | 0,094 |
| Brecha XO, mediana |EMA11−EMA25|/ATR | 0,44 | 0,33 | 0,08 |
| Ubicación en el VWAP de sesión a favor del trade (σ), mediana | −0,53 | 0,02 | +1,22 |
| Cruces del ASH 1m en los últimos 30 min, mediana | 2 | 2 | 4 |
| Barrida de mínimos/máximos en las últimas 3 velas | 36 % | 12 % | 14 % |

Filtros candidatos (elegidos sobre estos mismos 40 → resultado optimista, falta validar con casos nuevos):

| Regla | Sí que pasan | No filtrados | Dudosas que pasan |
|---|---|---|---|
| ubicación ≤ +1,0σ | 24/25 | 4/7 | 7/8 |
| cruces ASH 30 min ≤ 3 | 24/25 | 5/7 | 7/8 |
| **las dos juntas** | **23/25** | **7/7** | 6/8 |

Tipo: "continuación si el precio está a ≤ 1 ATR de 5m de las dos EMAs de 5m" coincide con Juan en 34/40.

SL de Juan: riesgo cierre→SL mediana 2,65 ATR(14) de 1m (p25 1,98 · p75 3,28). Casi siempre el extremo de las
últimas 2–5 velas más un margen de 0,3–0,7 ATR. Se calibra formalmente con las candidatas de §4.1.
