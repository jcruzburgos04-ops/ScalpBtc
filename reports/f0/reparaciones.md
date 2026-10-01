# F0 · Reparaciones (confirmadas por Juan el 2026-09-30)

## 1. Velas 1m oficiales rotas → reconstruidas desde aggTrades

192 minutos reemplazados (`data/proc/velas_1m_reparadas.parquet`). `datos.leer_velas_1m()` ya los aplica.

| open_time (UTC) | O | H | L | C | V (BTC) | trades |
|---|---|---|---|---|---|---|
| 2023-11-10 15:07 | 37147.6 | 37156.1 | 37116.0 | 37153.0 | 348.960 | 3102 |
| 2023-11-10 15:08 | 37152.9 | 37168.5 | 37140.9 | 37159.7 | 231.697 | 2491 |
| 2023-11-10 15:09 | 37159.8 | 37168.7 | 37142.0 | 37145.6 | 252.859 | 2667 |
| 2023-11-10 15:10 | 37145.6 | 37188.8 | 37140.0 | 37154.5 | 256.126 | 3207 |
| 2023-11-10 15:11 | 37154.4 | 37176.3 | 37124.4 | 37170.6 | 181.494 | 2627 |
| 2023-11-10 15:12 | 37170.6 | 37189.8 | 37165.0 | 37185.8 | 214.754 | 2824 |
| 2023-11-10 15:13 | 37185.8 | 37189.8 | 37148.1 | 37148.1 | 203.972 | 2509 |
| 2023-11-10 15:14 | 37148.2 | 37184.1 | 37148.1 | 37184.0 | 119.029 | 1745 |
| 2023-11-10 15:15 | 37184.1 | 37186.8 | 37162.6 | 37169.9 | 144.910 | 2127 |
| 2023-11-10 15:16 | 37170.0 | 37186.8 | 37096.7 | 37098.9 | 351.746 | 4001 |
| 2023-11-10 15:17 | 37099.0 | 37119.9 | 37080.0 | 37114.3 | 241.376 | 2825 |
| 2023-11-10 15:18 | 37114.5 | 37146.8 | 37106.0 | 37112.5 | 144.026 | 2465 |
| … (180 más) | | | | | | |

## 2. Mark price reconstruido

5762 minutos reconstruidos (`data/proc/mark_1m_reconstruido.parquet`). `datos.leer_mark_1m()` ya los aplica.

Método: mark ≈ last + b(t), b = mark − last interpolada entre la mediana de los 60 min previos y la de los 60 posteriores al hueco.

| Tramo (UTC) | Minutos |
|---|---|
| 2022-07-31 00:00 | 1440 |
| 2022-10-02 00:00 | 1440 |
| 2023-02-24 00:00 | 1440 |
| 2024-08-12 10:02 | 2 |
| 2026-06-29 00:00 | 1440 |

### Validación: 40 días de 2025–2026 con mark real, tapados y reconstruidos (57600 minutos)

| Métrica | Valor |
|---|---|
| Error absoluto del close, mediana | 1.90 USD |
| Error absoluto del close, p95 | 17.72 USD (0.0203 %) |
| Minutos con high reconstruido > high real | 71.9 % |
| Minutos con low reconstruido < low real | 68.9 % |
| Exceso del high, mediana | 0.25 USD |
| Exceso del low, mediana | 2.58 USD |
| Rango H−L del mark real, mediana | 34.30 USD |

Lectura: si high/low reconstruidos superan al real en la mayoría de los minutos, el SL por mark se dispara
más seguido que en la realidad en esos días (sesgo conservador). Los trades que caigan en minutos
reconstruidos se marcan en el motor (F3) para poder excluirlos en la sensibilidad.
