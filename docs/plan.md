# RSI Divergence Scanner — Análisis del Blueprint y Plan de Construcción

## Contexto

El usuario generó un blueprint completo (16 secciones) con "The Architect" para un scanner personal de divergencias RSI/precio, con alertas por Telegram y un dashboard de revisión/backtest. Pidió: (1) análisis de pros/contras del documento, (2) ajustes recomendados, (3) las preguntas necesarias antes de construir, y (4) un plan de construcción. Tras una primera ronda de preguntas, el usuario pidió varios cambios sustanciales de alcance que se incorporan aquí como la versión final del plan.

### Decisiones confirmadas con el usuario (dos rondas de preguntas)

- **Ubicación**: dentro de este mismo repo (Axelrod), en carpetas `scanner/` y `dashboard/` junto al blueprint existente.
- **Alcance de esta sesión**: solo dejar el plan afinado, sin escribir código todavía.
- **Fuente de datos de mercado**: se **descarta Schwab Trader API** y se cambia a un **proveedor de datos puro (no-broker)** — decisión tomada porque la investigación mostró que el scope OAuth de Schwab para apps retail incluye capacidad de trading junto con market data (no hay tier "solo lectura" nativo), lo cual el usuario no quiere aceptar ni como riesgo teórico sobre su cuenta real. **Recomendación: Alpaca** (`alpaca-py`), usando una cuenta de Alpaca separada (paper/data-only, sin fondos, sin ligar la cuenta Schwab real) — elimina por completo la posibilidad de que el scanner toque su cuenta de trading real, y de paso simplifica el manejo de credenciales: Alpaca usa API key + secret de larga duración, **no** el ciclo de refresh-token-que-vence-cada-7-días de Schwab, así que toda la complejidad de `oauth_tokens`/rotación desaparece.
  - Caveat a validar en la fase de verificación: el feed gratuito de Alpaca es IEX (no el consolidado SIP que usa ThinkorSwim), así que puede haber pequeñas diferencias de precio/RSI vs. lo que el usuario ve en ThinkorSwim. Si la discrepancia importa, evaluar el feed SIP de pago de Alpaca más adelante.
  - Cobertura de pre/post-market en el feed gratuito IEX también debe confirmarse en la práctica (IEX como exchange opera en horario regular; la cobertura extendida puede ser parcial).
- **Universo de símbolos**: se abandona el S&P 500 completo + sector SPDRs. Universo fijo inicial de **15 símbolos**, confirmado tal cual:
  - Acciones (Magnificent 7): `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA`
  - ETFs de índice: `SPY, QQQ, IWM, DIA`
  - Commodities (vía ETFs líquidos/optionables): `GLD, SLV, USO, UNG`
  - Como el universo ahora es una lista fija y conocida (todos son líquidos y optionable de sobra), **se elimina la necesidad de scraping de Wikipedia y de verificación de `has_options` vía API** — `universe.py` se simplifica a una lista estática en `config.py`, sin lógica de descubrimiento.
- **Timeframes**: se **elimina weekly**. El escaneo de divergencias corre en `30m, 1h, 4h, 1d` (el usuario confirmó que también quiere detección — no solo visualización — en 30m). Motivo de eliminar weekly: con confirmación fractal N=2 uniforme, weekly implicaba ~2 semanas de retraso en confirmar un pivote — quitar weekly resuelve el problema de raíz en vez de parchear la lógica de confirmación. N=2 en 30m implica solo ~1 hora de retraso de confirmación, muy razonable.
- **Sesiones pre-market y after-hours**: se incluyen en las temporalidades intradía donde aplica (`1h`, `4h`) — pre-market ~4:00–9:30 ET y after-hours ~16:00–20:00 ET. `1d` sigue siendo solo sesión regular (estándar de mercado). Esto también implica ampliar la ventana del cron de escaneo más allá de 9:30–16:00 ET.
- **Ajuste técnico — fetch incremental**: pedir solo barras nuevas desde el último `ts` guardado por `(ticker, timeframe)` en vez de re-descargar historial completo cada corrida. Con el universo reducido a 15 símbolos × 3 timeframes esto ya no es crítico por volumen, pero sigue siendo más eficiente y además hace el sistema tolerante a atrasos del cron (ver abajo).
- **Health-check de scan**: **sí se incluye** (el usuario lo pidió explícitamente en la segunda ronda, revirtiendo la decisión inicial de dejarlo fuera). Se fusiona con el aviso de "token por vencer" en un solo mecanismo: como Alpaca no tiene el problema de expiración de refresh token a 7 días de Schwab, ya no hace falta un aviso de renovación de token — el health-check único que queda es: **si no hay un scan exitoso en más de ~3 horas durante horario de mercado extendido, mandar un Telegram de alerta** (cubre caídas del workflow, errores de API, cron completamente detenido).
- **Cron de GitHub Actions**: confirmado por búsqueda que los retrasos son reales y empeoraron desde febrero 2026 (5–30 min común, sin SLA). Mitigación (ver también "tercera ronda" abajo, donde se decide agregar cron-job.org):
  1. Programar el cron nativo de respaldo en minutos "impares" (ej. `7,22,37,52` en vez de `0,15,30,45`) — reduce el atraso promedio al evitar la ola de jobs que arranca en los minutos redondos.
  2. El fetch incremental ya hace el sistema auto-recuperable ante atrasos: un run tardío igual trae todas las barras pendientes, así que un atraso demora la alerta pero no genera huecos de datos.
- **Resampling en cascada (30m→1h→4h)**: se resuelve explícitamente en la implementación de la fase de ingestión — excluir siempre la última barra si está incompleta (sesión en curso), y manejar feriados/medios días con el calendario de mercado (ej. vía `pandas_market_calendars`) en vez de asumir sesiones completas.

### Tercera ronda de ajustes (costo, comparación de timeframes, scheduler)

- **Costo — objetivo $0/mes confirmado como alcanzable**:
  - Alpaca: gratis siempre (Basic/IEX en tiempo real; para históricos — que es todo lo que usa el scanner, nunca dato "en vivo" puro — el feed **SIP consolidado es gratis** mientras el rango consultado termine >15 min en el pasado. Esto además mejora la paridad con ThinkorSwim sin pagar nada).
  - Supabase free tier (500MB), Vercel Hobby (uso personal no comercial), Telegram Bot API, cron-job.org: todos $0.
  - **GitHub Actions era el único punto de fricción**: repos privados solo dan 2,000 min gratis/mes, y con 15 símbolos × escaneo cada 15 min en horario extendido (~1,400 corridas/mes) se rozaba ese límite. **Decisión: repo público** → Actions ilimitado y gratis. Ningún secreto/API key vive en el código — todos van en GitHub Secrets, siempre encriptados y nunca expuestos aunque el repo sea público.
- **Scheduler — se agrega cron-job.org (gratis)**: en vez de depender solo del trigger `schedule` nativo de GitHub (el que sufre los atrasos de 5-30 min), cron-job.org le pega cada 15 min a un endpoint pequeño (función serverless en Vercel) que dispara el workflow vía `workflow_dispatch` con un GitHub PAT de scope `actions:write`. Los runs disparados así arrancan más consistentemente que los de la cola de `schedule`. Se mantiene el `schedule` nativo como respaldo (si cron-job.org falla, igual corre, solo que con más atraso posible).
- **30m se agrega como timeframe completo de escaneo** (ver "Timeframes" arriba — el usuario confirmó que quiere detección de divergencias en 30m también, no solo la vista comparativa). El dashboard igual gana la comparación visual: cuando el scanner marca una divergencia en 4h, el usuario puede abrir `/symbol/[ticker]` y comparar contra 1h y 30 min (y ver si también hay una divergencia propia marcada ahí). Implica: (a) ingerir y guardar barras de 30m en `price_bars`, (b) agregar `'30m'` al enum `timeframe_t`, (c) tabs de timeframe en `SymbolChart` incluyen 30m/1h/4h/1d, (d) `pivots.py`/`divergence.py` corren sobre las 4 temporalidades activas.
- **Criterio de validación de paridad refinado**: no se trata de que el RSI calce al centavo entre Alpaca y ThinkorSwim, sino de que **la señal de divergencia se detecte igual** — si una divergencia real ocurre en un timeframe dado, el scanner debe marcarla también, aunque el valor exacto de RSI varíe levemente entre feeds. Si una divergencia conocida en ThinkorSwim no aparece con datos de Alpaca, esa es la señal de que la fuente de datos no sirve y hay que reconsiderar el feed SIP de pago.

---

## Análisis del blueprint original (resumen)

### Pros que se mantienen
1. Separación limpia scanner (Python) ↔ dashboard (Next.js) vía Postgres.
2. Definición de divergencia fijada explícitamente, sin ambigüedad.
3. RSI de Wilder escrito a mano (no `pandas-ta`) — sigue siendo la decisión correcta, ahora paso obligado además para poder comparar Alpaca vs. ThinkorSwim con una fórmula controlada.
4. Dedup de alertas vía `status` + `alerted_at`.
5. Estrategia de testing table-driven para RSI/pivotes/divergencia.

### Contras que ya quedaron resueltos con los cambios de alcance
- Riesgo sobre la cuenta de trading real → resuelto cambiando a Alpaca (cuenta separada, sin fondos).
- Latencia de confirmación fractal en weekly → resuelto eliminando weekly.
- Rotación de refresh token de 7 días / falta de red de seguridad → resuelto: Alpaca no tiene ese ciclo, y el health-check cubre fallas de scan en general.
- Volumen de 500+ símbolos contra rate limits → resuelto reduciendo el universo a 15 símbolos fijos.

### Contras que siguen vigentes (a tener presente durante la construcción)
- Cron de GitHub Actions no es preciso — mitigado pero no eliminado (ver arriba).
- Resampling en cascada sigue siendo la pieza con más superficie de bugs sutiles — requiere manejo explícito de barras incompletas y calendario de feriados.
- Backtest idealizado (sin slippage/comisiones) — el win rate mostrado será optimista frente a operar en vivo; dejar esto explícito en la UI del dashboard.
- Paridad de precios Alpaca (IEX) vs. ThinkorSwim (SIP) — a validar en la fase de verificación, ver Regla No Negociable #1 abajo.

---

## Plan de construcción

Todo el trabajo es ejecutable ya (a diferencia de la versión anterior de este plan, que estaba bloqueada por la aprobación de la app de Schwab) — Alpaca permite crear una cuenta y generar API keys de inmediato, sin proceso de aprobación de días. Aun así, conviene una secuencia que valide lo barato/rápido de probar antes de automatizar.

1. **Repo público**: pasar Axelrod (o el sub-path del proyecto) a público antes de configurar Actions — se confirma explícitamente con el usuario en el momento de hacerlo, ya que es una acción visible/difícil de revertir del todo, no se asume en automático aunque ya esté decidida en principio.
2. **Estructura de carpetas y schema**: `scanner/`, `dashboard/`, `.github/workflows/`, `supabase/`. `supabase/schema.sql` ajustado: cambiar `timeframe_t` a `('30m','1h','4h','1d')` (quitar `'1w'`, agregar `'30m'` para el timeframe de solo-visualización), quitar la tabla `oauth_tokens` (Alpaca no rota tokens — una tabla simple de config, o directamente env vars/secrets, basta), agregar columna/flag de sesión (`regular`/`pre`/`post`) en `price_bars`.
3. **`scanner/config.py`**: universo fijo de 15 símbolos, zonas RSI (≤40/≥60), ancho de fractal N=2, timeframes de escaneo `30m/1h/4h/1d` (las 4 activas para detección de divergencias).
4. **`scanner/indicators.py`** (RSI de Wilder) y **`scanner/pivots.py`** (fractales) — desarrollo y tests con series sintéticas, sin depender de datos reales.
5. **`scanner/divergence.py`** con tests table-driven de la definición de divergencia.
6. **`pytest`** completo para indicators/pivots/divergence antes de tocar datos reales.
7. **Cuenta Alpaca + `scanner/alpaca_client.py`**: crear cuenta Alpaca (data-only/paper), generar API key + secret, wrapper simple de `alpaca-py` para históricos (incluye 30m para el timeframe de comparación) con soporte de extended hours. Guardar credenciales como secrets de GitHub Actions (no rotan, no necesitan tabla en Supabase).
8. **Ingesta + resampling**: barras nativas de Alpaca (1min o 5min como base, más 30m nativo si Alpaca lo ofrece directo), agregación a 1h/4h alineada a 9:30 ET, manejo explícito de barra incompleta y calendario de feriados/medios días. Fetch incremental desde el último `ts` por `(ticker, timeframe)`.
9. **Conectar pivotes/divergencia a datos reales** (`1h/4h/1d`), persistir en `pivots`/`divergences`.
10. **`scanner/telegram.py`**: alertas de divergencia con dedup, **más el mensaje de health-check** (si no hay scan exitoso en >3h durante ventana extendida de mercado). El mensaje de alerta incluye un link directo a `/symbol/[ticker]` en el dashboard, para que el usuario pueda entrar y comparar de inmediato las 4 temporalidades (30m/1h/4h/1d), no solo la que disparó la señal.
11. **`scan.py`** como entry point, prueba local end-to-end contra los 15 símbolos.
12. **Validación de señal (no solo de valor)**: comparar contra ThinkorSwim para 3-5 símbolos por timeframe. Criterio de aprobación: una divergencia real conocida en ThinkorSwim debe **detectarse también** con datos de Alpaca — el RSI exacto puede variar levemente, la señal no. Si una divergencia conocida no aparece, reevaluar el feed SIP de pago de Alpaca antes de seguir.
13. **`.github/workflows/scan.yml`**: trigger `workflow_dispatch` (para que cron-job.org lo pueda disparar) + `schedule` nativo de respaldo en minutos impares (`7,22,37,52`), ventana ampliada para cubrir pre-market/after-hours en 1h/4h. Endpoint serverless en Vercel (o una GitHub Action de un solo paso) que cron-job.org llama cada 15 min para disparar `workflow_dispatch` vía GitHub API con un PAT de scope `actions:write`.
14. **`backtest.py`** + `backtest.yml` (semanal + manual), con nota explícita en el resultado de que es sin slippage/comisiones.
15. **Dashboard**: scaffolding Next.js 15 + TS + Tailwind v4 + shadcn/ui + `iron-session` + `lightweight-charts`, login por password, páginas `DivergenceTable`/`SymbolChart`/`BacktestStats`, primero con datos mock y luego conectado a Supabase real. **`SymbolChart` es el punto central de comparación**: siempre muestra tabs para las 4 temporalidades (30m/1h/4h/1d) del símbolo, con marcadores de pivotes y divergencias propias de cada una — así, ante cualquier alerta (venga de la temporalidad que venga), el usuario puede saltar entre las 4 y ver si la señal se confirma o diverge entre timeframes.
16. **Deploy**: Vercel para el dashboard, variables de entorno, verificación final de tema oscuro/animaciones.

### Verificación
- `pytest` en `scanner/` debe pasar completo con datos sintéticos antes de conectar Alpaca.
- Validación de señal Alpaca vs. ThinkorSwim (paso 12) es la validación crítica de la Regla No Negociable de RSI — sin esto, las alertas no son confiables.
- Forzar un caso de divergencia histórica conocida y confirmar un solo mensaje de Telegram (sin duplicados en corridas subsecuentes).
- Simular una falla de scan (ej. desconectar credenciales temporalmente) y confirmar que el health-check dispara el aviso de Telegram tras la ventana de >3h.
- Confirmar que un trigger de cron-job.org efectivamente dispara el workflow vía `workflow_dispatch` y que el `schedule` nativo sigue funcionando como respaldo si cron-job.org falla.
- Dashboard: probar login, tabla, chart (incluyendo el cambio entre tabs 30m/1h/4h/1d, y que al llegar desde un link de alerta de Telegram se pueda comparar la señal contra las otras 3 temporalidades) y backtest con datos mock primero, luego con datos reales, antes del deploy a Vercel.
- Confirmar que el repo quedó público sin ningún secreto/API key committeado (revisar historial de commits, no solo el estado actual).

### Próximo paso concreto
En cuanto el usuario dé luz verde, arrancar por los pasos 1-6 (repo público, estructura, schema, config, indicadores/pivotes/divergencia con tests sintéticos) — no requieren cuenta de Alpaca todavía. El paso 7 (cuenta Alpaca) se puede hacer en paralelo apenas el usuario la registre.
