from __future__ import annotations

import asyncio
import logging
import sqlite3

from .pipeline import PipelineFarmaceutico

RUTA_BD = "data/pharma.db"


def _imprimir_reporte(filas: list[sqlite3.Row]) -> None:
    encabezado = f"{'Ticker':<8}{'Empresa':<28}{'Precio':>12}{'Mon':>5}{'Market Cap':>14}{'Cambio 52S':>12}"
    print(encabezado)
    print("-" * len(encabezado))
    for fila in filas:
        precio = f"{fila['main_share_price']:.2f}" if fila["main_share_price"] is not None else "N/D"
        cambio = f"{fila['week_52_price_change']:+.2f}%" if fila["week_52_price_change"] is not None else "N/D"
        market_cap = fila["market_cap_display"] or "N/D"
        print(
            f"{fila['ticker']:<8}{fila['company'][:27]:<28}{precio:>12}"
            f"{(fila['currency'] or 'N/D'):>5}{market_cap:>14}{cambio:>12}"
        )


async def _ejecutar() -> int:
    pipeline = PipelineFarmaceutico(ruta_bd=RUTA_BD)
    resumen = await pipeline.ejecutar()

    print(f"\nOK: {len(resumen.exitosos)} | FALLIDOS: {len(resumen.fallidos)}")
    for ticker, mensaje in resumen.fallidos:
        print(f"  - {ticker}: {mensaje}")

    print()
    _imprimir_reporte(pipeline.obtener_reporte())
    return 1 if resumen.fallidos and not resumen.exitosos else 0


def principal() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(asyncio.run(_ejecutar()))


if __name__ == "__main__":
    principal()
