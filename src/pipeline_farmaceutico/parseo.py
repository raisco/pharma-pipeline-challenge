"""Lógica pura de parseo para las páginas '/statistics/' de stockanalysis.com,
ya renderizadas por un navegador (ver `pipeline_farmaceutico.cliente`).

Se mantiene libre de cualquier I/O (navegador o base de datos) para poder
testear directamente contra un string/fixture HTML.

Estrategia (basada en lo que un usuario ve en pantalla, no en datos internos
del sitio):

- El precio principal de la acción está en un <div> grande y en negrita
  justo debajo del nombre de la compañía (clases "text-4xl" y "font-bold").
- Debajo del precio hay una línea de texto chica y gris con el formato
  "<BOLSA>: <TICKER> · Real-Time Price · USD" (o, para acciones OTC como
  Roche, "OTCMKTS · Delayed Price · Currency is USD") -- en ambos casos la
  moneda es la última palabra de esa línea.
- La tabla de estadísticas tiene filas de dos celdas: una con la etiqueta
  visible ("Market Cap", "52-Week Price Change", etc.) y la siguiente con el
  valor. Se busca la etiqueta por su texto exacto y se lee la celda vecina.
  (Ojo: "Market Cap" también aparece como link de navegación en otra parte
  de la página, por eso se exige que la etiqueta esté dentro de una celda de
  tabla <td> con una celda hermana -- si no, no es la fila que buscamos.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Tag

from .normalizacion import analizar_numero_exacto, analizar_porcentaje, analizar_precio

MARCADORES_VERIFICACION_BOT = ("Just a moment", "cf-turnstile", "Enable JavaScript and cookies to continue")

_ETIQUETA_MARKET_CAP = "Market Cap"
_ETIQUETA_CAMBIO_52_SEMANAS = "52-Week Price Change"


class ErrorDeAnalisis(RuntimeError):
    """Se lanza cuando la estructura de una página no coincide con lo esperado."""


@dataclass
class EstadisticasAnalizadas:
    precio_principal_accion: float | None
    moneda: str | None
    market_cap: float | None
    market_cap_texto: str | None
    cambio_precio_52_semanas: float | None


def es_pagina_de_verificacion_bot(html: str) -> bool:
    """True si la respuesta es una página de verificación anti-bot
    (Cloudflare u otra) en vez del contenido real."""
    return any(marcador in html for marcador in MARCADORES_VERIFICACION_BOT)


def _celda_de_valor_por_etiqueta(soup: BeautifulSoup, texto_etiqueta: str) -> Tag | None:
    """Busca, entre los <a> y <span> visibles de la página, el que tenga
    exactamente `texto_etiqueta`, y devuelve la celda <td> vecina con el
    valor -- solo si la etiqueta está dentro de una fila de tabla real."""
    for candidato in soup.find_all(["a", "span"]):
        if candidato.get_text(strip=True) != texto_etiqueta:
            continue
        celda_etiqueta = candidato.find_parent("td")
        if celda_etiqueta is None:
            continue
        celda_valor = celda_etiqueta.find_next_sibling("td")
        if celda_valor is not None:
            return celda_valor
    return None


def _extraer_precio_principal(soup: BeautifulSoup) -> str | None:
    nodo = soup.find(class_=re.compile(r"\btext-4xl\b.*\bfont-bold\b"))
    return nodo.get_text(strip=True) if nodo else None


def _extraer_moneda(soup: BeautifulSoup) -> str | None:
    """La moneda es la última palabra de la línea chica bajo el precio,
    p. ej. '...Real-Time Price · USD' o '...Currency is USD' -> 'USD'."""
    nodo = soup.find(class_=re.compile(r"\btext-tiny\b.*\btext-faded\b"))
    if nodo is None:
        return None
    texto = nodo.get_text(" ", strip=True)
    palabras = texto.split()
    if not palabras:
        return None
    ultima = palabras[-1]
    return ultima if re.fullmatch(r"[A-Z]{3,5}", ultima) else None


def analizar_html_estadisticas(html: str, ticker: str) -> EstadisticasAnalizadas:
    """Extrae las métricas requeridas de una página de estadísticas de
    stockanalysis.com ya renderizada.

    Los campos individuales ausentes se devuelven como None en vez de lanzar
    una excepción, de modo que una página parcialmente renderizada igual
    entregue los datos disponibles. Solo se lanza ErrorDeAnalisis cuando la
    página claramente no es contenido real (una página de verificación bot).
    """
    if es_pagina_de_verificacion_bot(html):
        raise ErrorDeAnalisis(f"[{ticker}] se recibió una página de verificación bot en vez de contenido real")

    soup = BeautifulSoup(html, "html.parser")

    celda_market_cap = _celda_de_valor_por_etiqueta(soup, _ETIQUETA_MARKET_CAP)
    market_cap_texto = celda_market_cap.get_text(strip=True) if celda_market_cap else None
    market_cap_exacto = celda_market_cap.get("title") if celda_market_cap else None
    market_cap = analizar_numero_exacto(market_cap_exacto)

    celda_cambio = _celda_de_valor_por_etiqueta(soup, _ETIQUETA_CAMBIO_52_SEMANAS)
    cambio_precio_52_semanas = analizar_porcentaje(celda_cambio.get_text(strip=True)) if celda_cambio else None

    return EstadisticasAnalizadas(
        precio_principal_accion=analizar_precio(_extraer_precio_principal(soup)),
        moneda=_extraer_moneda(soup),
        market_cap=market_cap,
        market_cap_texto=market_cap_texto,
        cambio_precio_52_semanas=cambio_precio_52_semanas,
    )
