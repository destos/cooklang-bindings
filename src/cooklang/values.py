"""Standalone helpers for reading and rendering quantity values.

These wrap upstream's own number handling rather than reimplementing it, which
matters because Cooklang's notion of a "value" is not Python's: it round-trips
fractions, and it treats an unparseable amount as text rather than an error.

Useful when you accept a quantity from a user — a shopping-list app letting
someone edit "1 1/2" — and want upstream's reading of it, not `float()`'s.
"""

from __future__ import annotations

from ._ffi import ffi
from .models import Range

__all__ = ["parse_value", "format_value"]


def parse_value(text: str) -> int | float | str | Range:
    """Parse a quantity string the way upstream does.

    Handles plain numbers, fractions (``"1/2"`` -> ``0.5``), mixed numbers
    (``"1 1/2"`` -> ``1.5``) and ranges (``"1/2 - 3/4"`` -> ``Range``).
    Anything it cannot read comes back as the original string rather than
    raising, matching Cooklang's tolerance of free-text amounts.

    Raises:
        TypeError: If ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    from .parser import _value

    return _value(ffi.parse_value(text))


def format_value(value: int | float | str | Range | None) -> str:
    """Render a value the way upstream does, restoring fractions.

    ``0.5`` comes back as ``"1/2"``. ``None`` renders as the empty string.
    """
    from .parser import _to_ffi_value

    return (ffi.format_value(_to_ffi_value(value)) or "").strip()
