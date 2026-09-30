# Decisiones

Formato: `[fecha] ESTADO · tema — detalle`. Estados: CONFIRMADA / PENDIENTE.

## Confirmadas (2026-09-30, ver CLAUDE.md §1 y §11)

Entrada al cierre de la vela · la posición corre hasta SL/TP aunque pase la ventana · una posición a la vez con
ampliaciones (máx. 4 patas, 1 % c/u, SL independientes, R ≥ 2 por pata) · 5m en formación · riesgo 1 % ·
SL en el swing más reciente de 1m · apalancamiento solo afecta margen · calibración 2023–2024, investigación
2025–2026 con walk-forward · niveles extra incluidos · invalidación a 30 min, cierra todas las patas, se testea
con y sin · variantes de calendario A–D.

## Pendientes

- [2026-09-30] PENDIENTE · Tramo de reserva jul–sep 2026 sin mirar hasta F8 (§6c).
- [2026-09-30] PENDIENTE · Definición del swing del SL y buffer (se resuelve con las marcas, §4.1).
- [2026-09-30] PENDIENTE · Invalidación: x y m (se calibran con las marcas, §5.1).
- [2026-09-30] PENDIENTE · Liquidaciones 2025–2026: el archivo público de Binance no tiene liquidationSnapshot
  para USD-M; solo COIN-M BTCUSD_PERP 2023-06-25 → 2024-10-14. Opciones: (1) proveedor pago (Tardis.dev),
  (2) agregador (Coinalyze), (3) proxy propio desde aggTrades + OI, validado contra BTCUSD_PERP 2023–2024
  (ojo: es otro contrato, la validación sería indirecta).
- [2026-09-30] PENDIENTE · Almacenamiento de aggTrades: ~31 GB en zip 2022-01 → hoy. El contenedor de trabajo es
  efímero y tiene ~30 GB libres; `data/` no se versiona en git. Hace falta definir dónde viven las barras de 1s
  (estimado: pocos GB en parquet) para no rehacer la descarga en cada sesión.
