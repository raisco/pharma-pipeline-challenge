"""Lista curada manualmente de las compañías objetivo.

El criterio de selección, la fuente y la fecha de consulta quedan
documentados acá (y en el README), según lo pedido por el enunciado para
justificar una selección manual.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    nombre: str
    ticker: str
    nota: str = ""


# Criterio: las diez compañías farmacéuticas cotizadas públicamente con mayor
# capitalización bursátil a nivel mundial, identificadas manualmente a partir
# de conocimiento público de mercado y verificadas contra la capitalización
# bursátil que reporta la propia stockanalysis.com al momento de la consulta.
# Se excluyen compañías de biotecnología pura (p. ej. Amgen, Gilead) para
# mantener el foco en laboratorios farmacéuticos diversificados.
#
# Fuente: stockanalysis.com (páginas /stocks/<ticker>/statistics/)
# Fecha de consulta: 2026-09-26/27 (UTC)
#
# Nota de cobertura: las compañías no estadounidenses cotizan en stockanalysis.com
# como ADRs (American Depositary Receipts) denominados en USD (NVO, AZN, NVS, SNY)
# o, en el caso de Roche, como acción OTC (RHHBY) bajo la ruta
# /quote/otc/RHHBY/statistics/ -- stockanalysis.com redirige automáticamente
# /stocks/rhhby/statistics/ hacia esa ruta (HTTP 301), y el cliente HTTP del
# pipeline sigue esa redirección de forma transparente.
EMPRESAS: list[Empresa] = [
    Empresa("Eli Lilly and Company", "LLY"),
    Empresa("Johnson & Johnson", "JNJ"),
    Empresa("AbbVie Inc.", "ABBV"),
    Empresa("Merck & Co., Inc.", "MRK"),
    Empresa("Roche Holding AG", "RHHBY", nota="ADR OTC; stockanalysis.com redirige a /quote/otc/RHHBY/statistics/"),
    Empresa("Novartis AG", "NVS", nota="ADR"),
    Empresa("AstraZeneca PLC", "AZN", nota="ADR"),
    Empresa("Novo Nordisk A/S", "NVO", nota="ADR"),
    Empresa("Pfizer Inc.", "PFE"),
    Empresa("Sanofi", "SNY", nota="ADR"),
]
