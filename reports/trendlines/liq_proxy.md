# Proxy de liquidaciones vs liquidaciones reales COIN-M (2023-07..2024-09)

Proxy: orden a mercado que barre ≥ 3 precios, ≥ p90 móvil de 7 días, con el OI de 5m bajando. Real: liquidaciones COIN-M BTCUSD_PERP del mismo lado en el mismo minuto (muestra: Binance manda ≤ 1 por segundo).

| Lado | Minutos con proxy | Con liq. real (proxy sí) | Con liq. real (proxy no) | Lift | Liq. real ≥ 50 k USD (sí / no) |
|---|---|---|---|---|---|
| shorts liquidados (compras forzadas) | 22200 (3.4%) | 19% | 1% | 17.1× | 2% / 0% (22.2×) |
| longs liquidados (ventas forzadas) | 23204 (3.5%) | 27% | 1% | 18.2× | 5% / 0% (32.5×) |
