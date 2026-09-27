"""Funciones puras de normalización: convierten los formatos de texto que usa
stockanalysis.com en valores tipados, distinguiendo siempre "dato ausente"
(devuelve None) de un cero genuino.

Unidades:
    - los valores monetarios (market cap) se normalizan a unidades planas de
      moneda (p. ej. USD), como float. "1.05T" -> 1_050_000_000_000.0 aprox
      (se prioriza el valor exacto "hover", cuando está disponible, sobre el
      abreviado).
    - los porcentajes se normalizan a un float en puntos porcentuales, p. ej.
      "+59.53%" -> 59.53 (NO 0.5953).
    - los precios se normalizan a un float plano en la moneda detectada.
"""

from __future__ import annotations

import re

_TOKENS_AUSENTES = {"", "n/a", "na", "-", "--", "none", "null", "undefined"}

_MULTIPLICADORES_SUFIJO = {
    "K": 1e3,
    "M": 1e6,
    "B": 1e9,
    "T": 1e12,
}


def _esta_ausente(bruto: str | None) -> bool:
    return bruto is None or bruto.strip().lower() in _TOKENS_AUSENTES


def analizar_numero_abreviado(bruto: str | None) -> float | None:
    """Convierte valores como '1.05T', '653.61B', '-45.16B', '98.02M' a float.

    Devuelve None para dato ausente (nunca para un cero genuino).
    """
    if _esta_ausente(bruto):
        return None
    texto = bruto.strip().replace(",", "")
    coincidencia = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([KMBT])?", texto, re.IGNORECASE)
    if not coincidencia:
        return None
    numero, sufijo = coincidencia.groups()
    valor = float(numero)
    if sufijo:
        valor *= _MULTIPLICADORES_SUFIJO[sufijo.upper()]
    return valor


def analizar_numero_exacto(bruto: str | None) -> float | None:
    """Convierte un número exacto separado por comas como '1,054,885,432,145'
    o '-45,162,000,000' a float. Devuelve None si está ausente o no se puede
    interpretar.
    """
    if _esta_ausente(bruto):
        return None
    texto = bruto.strip().replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None


def analizar_porcentaje(bruto: str | None) -> float | None:
    """Convierte '+59.53%' -> 59.53, '-33.95%' -> -33.95, '0.00%' -> 0.0.

    Devuelve None únicamente cuando el valor de origen está genuinamente
    ausente.
    """
    if _esta_ausente(bruto):
        return None
    texto = bruto.strip().replace(",", "").replace("%", "")
    try:
        return float(texto)
    except ValueError:
        return None


def analizar_precio(bruto: str | None) -> float | None:
    """Convierte un precio en texto plano como '1,183.46' -> 1183.46."""
    if _esta_ausente(bruto):
        return None
    texto = bruto.strip().lstrip("$").replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None
