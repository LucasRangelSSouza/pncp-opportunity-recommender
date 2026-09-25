"""Organization-only identifier guard applied before any record enters an index."""

from __future__ import annotations

import re


def _cnpj_check_digits(base: str) -> str:
    digits = [int(char) for char in base]
    for weights in ((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)):
        total = sum(d * w for d, w in zip(digits, weights))
        remainder = total % 11
        digits.append(0 if remainder < 2 else 11 - remainder)
    return "".join(str(d) for d in digits[-2:])


def classify_identifier(value: object) -> str:
    """Return `organization`, `natural_person`, or `unknown`.

    An 11-digit value is treated as a possible CPF and never indexed, even if
    its check digits are invalid, because the cost of a false negative is higher.
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11:
        return "natural_person"
    if len(digits) == 14 and len(set(digits)) > 1 and _cnpj_check_digits(digits[:12]) == digits[12:]:
        return "organization"
    return "unknown"
