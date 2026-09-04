"""Python bindings for the official Cooklang parser.

This package wraps `cooklang-rs <https://github.com/cooklang/cooklang-rs>`_,
the reference Rust implementation of Cooklang, through bindings generated with
UniFFI. It contains no parser logic of its own.

    >>> import cooklang_rs
    >>> recipe = cooklang_rs.parse("Chop the @onion{1}.")
    >>> recipe.steps[0].text
    'Chop the onion.'
    >>> recipe.ingredients[0].name
    'onion'
"""

from __future__ import annotations

from .models import (
    Cookware,
    Ingredient,
    Note,
    Quantity,
    Range,
    Recipe,
    Section,
    Step,
    Timer,
)
from .parser import CooklangError, combine_ingredients, parse

__all__ = [
    "parse",
    "combine_ingredients",
    "CooklangError",
    "Recipe",
    "Section",
    "Step",
    "Note",
    "Ingredient",
    "Cookware",
    "Timer",
    "Quantity",
    "Range",
    "__version__",
    "UPSTREAM_VERSION",
]

__version__ = "0.1.0"

UPSTREAM_VERSION = "0.18.7"
"""The pinned cooklang-rs release these bindings are generated from."""
