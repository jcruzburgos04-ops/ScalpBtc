# F2 · Ronda 2: validación de los filtros con 30 casos nuevos

Respuestas: 16 sí · 9 dudosa · 5 no (`marcas/revision_ronda2.json`).

| | Sí | Dudosa | No |
|---|---|---|---|
| Pasan los filtros (20) | 10 | 7 | 3 |
| No pasan (10: 5 ubicación, 5 rango) | 6 | 2 | 2 |

Los filtros elegidos en la ronda 1 **no se sostienen con casos nuevos**: descartarían 6 de los 16 sí y dejarían pasar
3 de los 5 no. Fallan por ubicación 5 casos → 3 sí (rebotes con barrida y volumen arriba de +1σ); fallan por rango
5 casos → 3 sí.

Las dos rondas juntas (70 casos; `reports/f2/rondas_1y2_medidas.csv`), capacidad de cada variable para separar los
sí del resto (AUC; 0,5 = azar, 1 = perfecto): ubicación en el VWAP 0,60 · cruces del ASH 0,63 · RVOL máx. 3 velas 0,61 ·
barrida 0,55 · distancia a las EMAs de 5m 0,43 · ASH de 5m en contra 0,43. Ninguna variable objetiva sola reproduce
el criterio; las decisiones combinan lecturas discrecionales (barrida con volumen, rechazo de niveles, calidad de vela).

Tipo continuación/rebote: coincide 30/30 en la ronda 2 (34/40 en la ronda 1). Ojo: la página precargaba el tipo
del código.
