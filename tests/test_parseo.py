"""Test unitario para pipeline_farmaceutico.parseo contra un fixture HTML
sintético que imita los fragmentos relevantes de una página YA RENDERIZADA
(post-hidratación) de stockanalysis.com: precio principal, línea de moneda,
y dos filas de tabla con etiqueta visible + valor. Sin llamada de red, sin
navegador y sin página real -- esto solo ejercita nuestra propia lógica de
extracción contra un string que controlamos.
"""

from pipeline_farmaceutico.parseo import analizar_html_estadisticas, es_pagina_de_verificacion_bot

HTML_FIXTURE = """
<html><body>
<div class="max-w-[50%]">
  <div class="text-4xl font-bold transition-colors duration-300 block sm:inline">1,183.46</div>
  <div class="mt-px text-tiny text-faded">NYSE: LLY · Real-Time Price · USD</div>
</div>
<table><tbody>
  <tr>
    <td><a class="dothref" href="/stocks/lly/market-cap/">Market Cap</a></td>
    <td class="text-right font-semibold" title="1,054,885,432,145">1.05T</td>
  </tr>
  <tr>
    <td><span>52-Week Price Change</span></td>
    <td class="text-right font-semibold" title="59.53%">+59.53%</td>
  </tr>
</tbody></table>
<!-- este link de navegación repite el mismo texto "Market Cap" pero SIN estar
     en una fila de tabla -- el parser debe ignorarlo -->
<nav><ul><li><a href="/stocks/lly/market-cap/">Market Cap</a></li></ul></nav>
</body></html>
"""


def test_analizar_html_estadisticas_extrae_todos_los_campos_requeridos():
    estadisticas = analizar_html_estadisticas(HTML_FIXTURE, ticker="LLY")

    assert estadisticas.precio_principal_accion == 1183.46
    assert estadisticas.moneda == "USD"
    assert estadisticas.market_cap == 1_054_885_432_145.0
    assert estadisticas.market_cap_texto == "1.05T"
    assert estadisticas.cambio_precio_52_semanas == 59.53


def test_es_pagina_de_verificacion_bot_detecta_interstitial_cloudflare():
    """El scraper debe distinguir una página real de una página de
    verificación bot de Cloudflare aunque ambas vuelvan con status 200/403,
    porque si no una página de verificación se guardaría silenciosamente
    como si fueran datos reales (vacíos)."""
    assert es_pagina_de_verificacion_bot("<title>Just a moment...</title>") is True
    assert es_pagina_de_verificacion_bot(HTML_FIXTURE) is False
