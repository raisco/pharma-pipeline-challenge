"""Cliente basado en navegador (Playwright) para stockanalysis.com, con un
límite duro de concurrencia.

Se usa un navegador real (headless) en vez de un simple cliente HTTP porque
gran parte de la tabla de estadísticas de stockanalysis.com se hidrata en el
cliente (con JavaScript): recién después de que el navegador ejecuta ese
JavaScript aparecen, como HTML normal y visible, filas de tabla con
etiquetas legibles como "Market Cap" o "52-Week Price Change" junto a su
valor. Playwright permite esperar esa hidratación y después leer el HTML ya
renderizado con selectores simples, basados en el texto que un humano vería
en pantalla -- exactamente lo que hace `pipeline_farmaceutico.parseo`.

stockanalysis.com está detrás de Cloudflare; por eso:
  - se reutiliza un único navegador y un único contexto (con sus cookies)
    para todas las páginas de la corrida.
  - un semáforo limita la concurrencia real a MAX_PAGINAS_CONCURRENTES
    pestañas/solicitudes en simultáneo.
  - se reintenta con backoff cuando se detecta una página de verificación
    bot o un error transitorio de navegación.
"""

from __future__ import annotations

import asyncio
import logging
import random

from playwright.async_api import Browser, async_playwright

from .parseo import es_pagina_de_verificacion_bot

logger = logging.getLogger(__name__)

URL_BASE = "https://stockanalysis.com"
MAX_PAGINAS_CONCURRENTES = 2
MAX_INTENTOS = 3
TIEMPO_ESPERA_NAVEGACION_MS = 30_000

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class ErrorDeDescarga(RuntimeError):
    """Se lanza cuando la página de un ticker no pudo obtenerse tras agotar
    todos los reintentos."""


class ClienteStockAnalysis:
    """Obtiene páginas de estadísticas ya renderizadas, limitado a
    MAX_PAGINAS_CONCURRENTES pestañas en simultáneo."""

    def __init__(self, max_paginas_concurrentes: int = MAX_PAGINAS_CONCURRENTES) -> None:
        self._semaforo = asyncio.Semaphore(max_paginas_concurrentes)
        self._playwright = None
        self._navegador: Browser | None = None

    async def __aenter__(self) -> "ClienteStockAnalysis":
        self._playwright = await async_playwright().start()
        self._navegador = await self._playwright.chromium.launch()
        return self

    async def __aexit__(self, *info_excepcion: object) -> None:
        if self._navegador is not None:
            await self._navegador.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def obtener_html_estadisticas(self, ticker: str) -> str:
        """Abre `/stocks/<ticker>/statistics/` en una pestaña nueva, espera a
        que la tabla de estadísticas termine de hidratarse, y devuelve el
        HTML ya renderizado. Respeta el límite de concurrencia y reintenta
        fallos transitorios o páginas de verificación bot.
        """
        assert self._navegador is not None, "usar dentro de 'async with ClienteStockAnalysis()'"
        url = f"{URL_BASE}/stocks/{ticker.lower()}/statistics/"
        ultimo_error: Exception | None = None

        for intento in range(1, MAX_INTENTOS + 1):
            pagina = None
            try:
                async with self._semaforo:
                    pagina = await self._navegador.new_page(user_agent=_USER_AGENT)
                    await pagina.goto(url, wait_until="networkidle", timeout=TIEMPO_ESPERA_NAVEGACION_MS)
                    try:
                        await pagina.wait_for_selector("text=Market Cap", timeout=TIEMPO_ESPERA_NAVEGACION_MS)
                    except Exception:
                        pass  # si no aparece, dejamos que el parseo detecte la página de bloqueo o los campos faltantes
                    html = await pagina.content()

                if es_pagina_de_verificacion_bot(html):
                    raise ErrorDeDescarga(f"[{ticker}] bloqueado por una página de verificación bot")
                return html
            except Exception as exc:  # noqa: BLE001 - cualquier fallo de navegación se reintenta igual
                ultimo_error = exc
                logger.warning("intento %d/%d falló para %s: %s", intento, MAX_INTENTOS, ticker, exc)
                if intento < MAX_INTENTOS:
                    espera = (2 ** (intento - 1)) + random.uniform(0, 1)
                    await asyncio.sleep(espera)
            finally:
                if pagina is not None:
                    await pagina.close()

        raise ErrorDeDescarga(f"[{ticker}] falló tras {MAX_INTENTOS} intentos: {ultimo_error}") from ultimo_error
