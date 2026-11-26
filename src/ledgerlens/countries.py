"""Country profiles: the rules that change from one tax system to another.

Adding a country means adding one profile here; validation.py stays untouched.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal


def peru_ruc_is_valid(tax_id: str) -> bool:
    """Peru RUC: 11 digits, known prefix, modulo-11 check digit."""
    if len(tax_id) != 11 or not tax_id.isdigit() or tax_id[:2] not in {"10", "15", "16", "17", "20"}:
        return False
    total = sum(int(d) * w for d, w in zip(tax_id[:10], (5, 4, 3, 2, 7, 6, 5, 4, 3, 2), strict=True))
    check = 11 - total % 11
    return {10: 0, 11: 1}.get(check, check) == int(tax_id[10])


def chile_rut_is_valid(tax_id: str) -> bool:
    """Chile RUT: body + check digit (0-9 or K), modulo 11 with weights 2..7."""
    body, check = tax_id[:-1], tax_id[-1:].upper()
    if not body.isdigit() or len(body) < 7:
        return False
    total = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(body)))
    expected = 11 - total % 11
    return {11: "0", 10: "K"}.get(expected, str(expected)) == check


@dataclass(frozen=True)
class CountryProfile:
    code: str
    name: str
    tax_name: str                                     # IGV, IVA, VAT...
    tax_rates: tuple[Decimal, ...] = ()               # accepted rates; empty = do not check
    tax_id_name: str = "tax ID"
    tax_id_is_valid: Callable[[str], bool] | None = field(default=None, compare=False)


PROFILES = {
    "GENERIC": CountryProfile("GENERIC", "Generic", "tax"),
    "PE": CountryProfile("PE", "Peru", "IGV", (Decimal("0.18"), Decimal("0.10")), "RUC", peru_ruc_is_valid),
    "CL": CountryProfile("CL", "Chile", "IVA", (Decimal("0.19"),), "RUT", chile_rut_is_valid),
    "ES": CountryProfile("ES", "Spain", "IVA", (Decimal("0.21"), Decimal("0.10"), Decimal("0.04")), "NIF"),
}


def get_profile(code: str) -> CountryProfile:
    try:
        return PROFILES[code.upper()]
    except KeyError:
        raise ValueError(f"Unknown country '{code}'. Available: {', '.join(PROFILES)}") from None
