"""Tests unitarios para pipeline_farmaceutico.normalizacion.

Sin llamadas HTTP y sin conexión a base de datos -- funciones puras sobre
strings.
"""

from pipeline_farmaceutico.normalizacion import (
    analizar_numero_abreviado,
    analizar_numero_exacto,
    analizar_porcentaje,
    analizar_precio,
)


def test_analizar_numero_abreviado_maneja_sufijos_y_signos():
    """Los sufijos B/T y los signos negativos son comunes en cifras de
    market cap / flujo de caja (p. ej. '-45.16B' para caja neta)."""
    assert analizar_numero_abreviado("1.05T") == 1.05e12
    assert analizar_numero_abreviado("653.61B") == 653.61e9
    assert analizar_numero_abreviado("-45.16B") == -45.16e9
    assert analizar_numero_abreviado("98.02M") == 98.02e6


def test_analizar_porcentaje_distingue_ausente_de_cero():
    """Este es el requisito central: una acción que genuinamente no se movió
    en 52 semanas ('0.00%') NO debe guardarse igual que una acción para la
    cual ese dato simplemente está ausente (None/'n/a')."""
    assert analizar_porcentaje("0.00%") == 0.0
    assert analizar_porcentaje("+59.53%") == 59.53
    assert analizar_porcentaje("-33.95%") == -33.95
    assert analizar_porcentaje(None) is None
    assert analizar_porcentaje("n/a") is None
    assert analizar_porcentaje("-") is None


def test_analizar_numero_exacto_y_precio_separados_por_comas():
    assert analizar_numero_exacto("1,054,885,432,145") == 1_054_885_432_145.0
    assert analizar_numero_exacto("-45,162,000,000") == -45_162_000_000.0
    assert analizar_numero_exacto(None) is None

    assert analizar_precio("1,183.46") == 1183.46
    assert analizar_precio("$28.67") == 28.67
    assert analizar_precio("") is None
