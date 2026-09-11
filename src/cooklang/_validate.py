"""Type checks at the public boundary, so a wrong type fails readably.

Without these a wrong type reaches the generated ctypes layer, which either
fails with an error naming none of our arguments or, worse, silently converts
it. Every entry point uses these helpers so the message is the same everywhere.
"""

from __future__ import annotations

import numbers
from typing import NoReturn


def _reject(name: str, expected: str, value: object) -> NoReturn:
    raise TypeError(f"{name} must be {expected}, not {type(value).__name__}")


def require_str(name: str, value: object) -> str:
    """Return ``value`` if it is a ``str``, else raise ``TypeError``."""
    if not isinstance(value, str):
        _reject(name, "str", value)
    return value


def require_number(name: str, value: object) -> float:
    """Return ``value`` as a float if it is a real number, else raise ``TypeError``.

    ``bool`` is an ``int`` to Python but never a quantity, so it is refused, as
    is a numeric-looking ``str``: ``scale="2"`` is a bug, not a request for 2.
    ``Decimal`` is accepted even though it is not ``numbers.Real``.
    """
    if isinstance(value, (bool, complex)) or not isinstance(value, numbers.Number):
        _reject(name, "a number", value)
    return float(value)  # type: ignore[arg-type]


def require_index(name: str, value: object) -> int:
    """Return ``value`` if it is an integer (not a ``bool``), else raise ``TypeError``."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        _reject(name, "an int", value)
    return int(value)
