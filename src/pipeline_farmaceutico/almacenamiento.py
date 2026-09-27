"""Persistencia en SQLite.

Ante un fallo de descarga/parseo para un ticker, deliberadamente NO se toca
su fila existente -- el último snapshot exitoso se mantiene intacto, y el
fallo se registra en `pipeline_errors` en su lugar. Esto satisface "si una
descarga falla, conservá los datos válidos del resto e informá el error"
tanto entre tickers (las otras filas quedan intactas) como entre
ejecuciones (el último dato válido conocido de un ticker sobrevive a una
corrida posterior fallida).

Nota de nomenclatura: las columnas de `pharma_metrics` usan los nombres de
campo tal como los especifica el enunciado de la prueba técnica (company,
ticker, main_share_price, currency, market_cap, week_52_price_change,
extracted_at_utc), en vez de traducirlos, para que el esquema de datos
coincida exactamente con lo pedido.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pharma_metrics (
    ticker TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    main_share_price REAL,
    currency TEXT,
    market_cap REAL,
    market_cap_display TEXT,
    week_52_price_change REAL,
    source_url TEXT NOT NULL,
    extracted_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    occurred_at_utc TEXT NOT NULL,
    message TEXT NOT NULL
);
"""


class Almacenamiento:
    def __init__(self, ruta_bd: str | Path) -> None:
        self._ruta_bd = Path(ruta_bd)
        self._ruta_bd.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._conectar()) as conexion:
            conexion.executescript(ESQUEMA)
            conexion.commit()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self._ruta_bd)

    def actualizar_metricas(
        self,
        *,
        ticker: str,
        empresa: str,
        precio_principal_accion: float | None,
        moneda: str | None,
        market_cap: float | None,
        market_cap_texto: str | None,
        cambio_precio_52_semanas: float | None,
        url_fuente: str,
        extraido_en_utc: str,
    ) -> None:
        with closing(self._conectar()) as conexion:
            conexion.execute(
                """
                INSERT INTO pharma_metrics (
                    ticker, company, main_share_price, currency, market_cap,
                    market_cap_display, week_52_price_change, source_url, extracted_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    company=excluded.company,
                    main_share_price=excluded.main_share_price,
                    currency=excluded.currency,
                    market_cap=excluded.market_cap,
                    market_cap_display=excluded.market_cap_display,
                    week_52_price_change=excluded.week_52_price_change,
                    source_url=excluded.source_url,
                    extracted_at_utc=excluded.extracted_at_utc
                """,
                (
                    ticker,
                    empresa,
                    precio_principal_accion,
                    moneda,
                    market_cap,
                    market_cap_texto,
                    cambio_precio_52_semanas,
                    url_fuente,
                    extraido_en_utc,
                ),
            )
            conexion.commit()

    def registrar_error(self, *, ticker: str, ocurrido_en_utc: str, mensaje: str) -> None:
        with closing(self._conectar()) as conexion:
            conexion.execute(
                "INSERT INTO pipeline_errors (ticker, occurred_at_utc, message) VALUES (?, ?, ?)",
                (ticker, ocurrido_en_utc, mensaje),
            )
            conexion.commit()

    def obtener_todas_las_metricas(self) -> list[sqlite3.Row]:
        with closing(self._conectar()) as conexion:
            conexion.row_factory = sqlite3.Row
            return conexion.execute("SELECT * FROM pharma_metrics ORDER BY market_cap DESC").fetchall()
