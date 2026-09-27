# Pipeline Farmacéutico — Scraping de laboratorios farmacéuticos

Pipeline asíncrono en Python que obtiene métricas de los diez laboratorios
farmacéuticos cotizados más grandes del mundo por capitalización bursátil
desde [stockanalysis.com](https://stockanalysis.com/), y las persiste en
SQLite.

## Instalación

Con [uv](https://docs.astral.sh/uv/) (recomendado, gestiona el entorno virtual automáticamente):

```bash
uv sync --extra dev
uv run playwright install chromium
```

O con `pip` en un entorno virtual propio:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac
pip install -r requirements-dev.txt
playwright install chromium
```

`playwright install chromium` descarga un Chromium headless (una sola vez) que el pipeline usa para renderizar las páginas.

## Ejecución

```bash
uv run pipeline-farmaceutico
```

(o, sin uv: `pip install -e .` y luego `pipeline-farmaceutico`, o `python -m pipeline_farmaceutico.consola` parado dentro de `src/`)

Cada ejecución:
1. Abre `https://stockanalysis.com/stocks/<ticker>/statistics/` para las 10 compañías en un navegador headless (Chromium vía Playwright), con un máximo de **2 pestañas/solicitudes simultáneas**.
2. Extrae precio principal, moneda, capitalización bursátil y cambio de precio a 52 semanas, leyendo el HTML ya renderizado.
3. Actualiza (upsert) `data/pharma.db` (SQLite) — se crea automáticamente en el primer run.
4. Imprime un resumen de éxitos/fallos y una tabla con los datos vigentes.

Si falla la descarga de una compañía puntual, el resto se persiste igual y el
error queda registrado en la tabla `pipeline_errors`; el dato previo de esa
compañía en `pharma_metrics` **no se borra ni se pisa con nulos** (se
conserva el último valor válido conocido).

## Tests

```bash
uv run pytest -v
```

Incluye 3+ tests unitarios sobre lógica propia (parseo y normalización),
**sin navegador, sin HTTP y sin conexión a una base real**:

- `test_normalizacion.py::test_analizar_numero_abreviado_maneja_sufijos_y_signos` — verifica que sufijos `B`/`T`/`M` y signos negativos (p. ej. `-45.16B`, usado en cifras de caja neta) se normalizan a un `float` correcto.
- `test_normalizacion.py::test_analizar_porcentaje_distingue_ausente_de_cero` — el requisito central de "diferenciar dato ausente de valor cero": `"0.00%"` debe dar `0.0`, mientras que `None`/`"n/a"`/`"-"` deben dar `None`.
- `test_normalizacion.py::test_analizar_numero_exacto_y_precio_separados_por_comas` — valores exactos con separador de miles (`"1,054,885,432,145"`) y precios con símbolo de moneda (`"$28.67"`).
- `test_parseo.py::test_analizar_html_estadisticas_extrae_todos_los_campos_requeridos` — sobre un HTML sintético (fixture propio, no una página real) que imita la estructura ya renderizada de stockanalysis.com, verifica que se extraen correctamente precio, moneda, market cap y cambio a 52 semanas, y que un link de navegación que repite el texto "Market Cap" fuera de la tabla se ignora correctamente.
- `test_parseo.py::test_es_pagina_de_verificacion_bot_detecta_interstitial_cloudflare` — evita que una página de verificación anti-bot de Cloudflare se guarde silenciosamente como si fueran datos reales (vacíos).

## Selección de compañías

**Criterio:** las diez farmacéuticas cotizadas públicamente con mayor
capitalización bursátil a nivel mundial, seleccionadas manualmente a partir
de conocimiento público de mercado y verificadas contra la capitalización
bursátil que reporta la propia stockanalysis.com al momento de la consulta.
Se excluyen compañías de biotecnología pura (p. ej. Amgen, Gilead) para
mantener el foco en laboratorios farmacéuticos diversificados.

**Fuente:** stockanalysis.com (páginas `/stocks/<ticker>/statistics/`).
**Fecha de consulta:** 2026-09-26/27 (UTC).

| # | Compañía | Ticker | Market cap (al consultar) |
|---|----------|--------|---------------------------|
| 1 | Eli Lilly and Company | LLY | 1.05T |
| 2 | Johnson & Johnson | JNJ | 653.61B |
| 3 | AbbVie Inc. | ABBV | 467.12B |
| 4 | Merck & Co., Inc. | MRK | 367.07B |
| 5 | Roche Holding AG | RHHBY | 348.31B |
| 6 | Novartis AG | NVS | 274.75B |
| 7 | AstraZeneca PLC | AZN | 257.77B |
| 8 | Novo Nordisk A/S | NVO | 170.60B |
| 9 | Pfizer Inc. | PFE | 163.41B |
| 10 | Sanofi | SNY | 98.02B |

**Brecha de cobertura documentada:** las compañías no estadounidenses cotizan
en stockanalysis.com como ADRs denominados en USD (NVO, AZN, NVS, SNY), o —
en el caso de Roche — como acción OTC bajo `/quote/otc/RHHBY/statistics/`;
`/stocks/rhhby/statistics/` responde con un HTTP 301 hacia esa ruta, que
Playwright sigue automáticamente al navegar. No se sustituyó ninguna
compañía: las 10 tienen cobertura completa en el sitio.

## Datos guardados y normalización de unidades

| Campo | Tipo | Notas |
|---|---|---|
| `main_share_price` | float | Precio de la acción tal como se muestra en la página (encabezado), en la moneda detectada. |
| `currency` | str | Detectada leyendo la línea visible bajo el precio (ej. "...Real-Time Price · USD"), no asumida. |
| `market_cap` | float | Normalizado a unidades planas de moneda a partir del valor exacto que muestra el sitio en el atributo `title` de la celda (ej. `"1,054,885,432,145"`). |
| `market_cap_display` | str | Valor abreviado tal como lo muestra el sitio (`"1.05T"`), guardado para referencia/lectura humana. |
| `week_52_price_change` | float | **Cambio de precio** a 52 semanas (no retorno total) en puntos porcentuales, p. ej. `59.53` significa `+59.53%`. Corresponde a la fila visible "52-Week Price Change" de la tabla de estadísticas, que es explícitamente el cambio de precio y no el retorno total (el sitio no expone ese último dato en esta página). |
| `extracted_at_utc` | str (ISO 8601) | Fecha y hora UTC de la extracción exitosa de esa fila. |

**Dato ausente vs. valor cero:** toda función de parseo (`pipeline_farmaceutico.normalizacion`)
devuelve `None` cuando el dato está ausente (`None`, `"n/a"`, `"-"`, etc.) y
un `float` real — incluyendo `0.0` — cuando el valor es genuinamente cero.
Esto se guarda como `NULL` vs. `0` en SQLite respectivamente.

## Cómo funciona el scraping (notas técnicas)

stockanalysis.com está construido con SvelteKit e hidrata en el cliente
buena parte de la tabla de estadísticas (market cap, cambio a 52 semanas,
etc.): recién después de que el navegador ejecuta ese JavaScript aparecen,
como HTML normal, filas de tabla con una etiqueta visible ("Market Cap",
"52-Week Price Change") y su valor en la celda vecina. Por eso el pipeline
usa Playwright (`pipeline_farmaceutico/cliente.py`) para levantar un
Chromium headless, esperar esa hidratación, y recién ahí leer el HTML ya
renderizado.

`pipeline_farmaceutico/parseo.py` extrae los datos buscando ese texto visible
(el mismo que vería una persona navegando el sitio), no datos internos del
sitio: busca la etiqueta exacta ("Market Cap" / "52-Week Price Change")
dentro de una celda de tabla `<td>` y lee la celda hermana. Esto importa
porque "Market Cap" también aparece como link de navegación en otra parte de
la página (fuera de cualquier tabla) — el parser lo descarta explícitamente
por no tener una celda hermana, y hay un test dedicado a este caso.

El sitio está detrás de Cloudflare: ráfagas de requests sin cookies
compartidas activan una página de verificación anti-bot. El cliente mitiga
esto reutilizando un único navegador/contexto para todas las páginas de la
corrida, limitando la concurrencia a 2 pestañas con un `asyncio.Semaphore`, y
reintentando con backoff exponencial cuando detecta una página de bloqueo o
un error transitorio de navegación.

## Uso de IA

Se usó IA (Claude / Claude Code) como asistente de desarrollo en este
proyecto, particularmente para la capa de persistencia en SQLite
(`almacenamiento.py`) y para escribir los tests unitarios.
