from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .almacenamiento import Almacenamiento
from .cliente import ClienteStockAnalysis, ErrorDeDescarga
from .empresas import EMPRESAS, Empresa
from .parseo import ErrorDeAnalisis, analizar_html_estadisticas

logger = logging.getLogger(__name__)


@dataclass
class ResumenEjecucion:
    exitosos: list[str]
    fallidos: list[tuple[str, str]]  # (ticker, mensaje de error)


class PipelineFarmaceutico:
    def __init__(self, ruta_bd: str = "data/pharma.db", empresas: list[Empresa] | None = None) -> None:
        self._almacenamiento = Almacenamiento(ruta_bd)
        self._empresas = empresas if empresas is not None else EMPRESAS

    async def _procesar_empresa(
        self, cliente: ClienteStockAnalysis, empresa: Empresa
    ) -> tuple[str, str | None]:
        url_fuente = f"https://stockanalysis.com/stocks/{empresa.ticker.lower()}/statistics/"
        try:
            html = await cliente.obtener_html_estadisticas(empresa.ticker)
            estadisticas = analizar_html_estadisticas(html, empresa.ticker)
        except (ErrorDeDescarga, ErrorDeAnalisis) as exc:
            return empresa.ticker, str(exc)

        self._almacenamiento.actualizar_metricas(
            ticker=empresa.ticker,
            empresa=empresa.nombre,
            precio_principal_accion=estadisticas.precio_principal_accion,
            moneda=estadisticas.moneda,
            market_cap=estadisticas.market_cap,
            market_cap_texto=estadisticas.market_cap_texto,
            cambio_precio_52_semanas=estadisticas.cambio_precio_52_semanas,
            url_fuente=url_fuente,
            extraido_en_utc=datetime.now(timezone.utc).isoformat(),
        )
        return empresa.ticker, None

    async def ejecutar(self) -> ResumenEjecucion:
        exitosos: list[str] = []
        fallidos: list[tuple[str, str]] = []

        async with ClienteStockAnalysis() as cliente:
            tareas = [self._procesar_empresa(cliente, empresa) for empresa in self._empresas]
            resultados = await asyncio.gather(*tareas)

        for ticker, error in resultados:
            if error is None:
                exitosos.append(ticker)
            else:
                fallidos.append((ticker, error))
                self._almacenamiento.registrar_error(
                    ticker=ticker,
                    ocurrido_en_utc=datetime.now(timezone.utc).isoformat(),
                    mensaje=error,
                )
                logger.error("no se pudo actualizar %s: %s", ticker, error)

        return ResumenEjecucion(exitosos=exitosos, fallidos=fallidos)

    def obtener_reporte(self):
        return self._almacenamiento.obtener_todas_las_metricas()
