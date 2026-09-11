"""Python bindings for the official Cooklang parser.

This package wraps `cooklang-rs <https://github.com/cooklang/cooklang-rs>`_,
the reference Rust implementation of Cooklang, through bindings generated with
UniFFI. It contains no parser logic of its own.

    >>> import cooklang
    >>> recipe = cooklang.parse("Chop the @onion{1}.")
    >>> recipe.steps[0].text
    'Chop the onion.'
    >>> recipe.ingredients[0].name
    'onion'
"""

from __future__ import annotations

from . import contrib
from .aisle import AisleCategory, AisleConfig, AisleIngredient, parse_aisle_config
from .models import (
    Block,
    Cookware,
    CookwareRef,
    Ingredient,
    IngredientRef,
    Item,
    NameAndUrl,
    Note,
    Quantity,
    Range,
    Recipe,
    RecipeTime,
    Section,
    Step,
    TextItem,
    Timer,
    TimerRef,
)
from .errors import CooklangError
from .parser import ParseError, combine_ingredients, parse
from .shopping import (
    CheckEntry,
    IngredientItem,
    RecipeItem,
    ShoppingItem,
    ShoppingList,
    ShoppingListError,
    checked_names,
    compact_checked_log,
    parse_checked_log,
    parse_shopping_list,
)
from .values import format_value, parse_value

__all__ = [
    # Helpers this project adds, which upstream does not provide.
    "contrib",
    # Errors
    "CooklangError",
    # Recipes
    "parse",
    "combine_ingredients",
    "ParseError",
    "Recipe",
    "Section",
    "Step",
    "TextItem",
    "IngredientRef",
    "CookwareRef",
    "TimerRef",
    "Item",
    "Note",
    "Block",
    "Ingredient",
    "Cookware",
    "Timer",
    "Quantity",
    "Range",
    "NameAndUrl",
    "RecipeTime",
    # Aisle configuration
    "parse_aisle_config",
    "AisleConfig",
    "AisleCategory",
    "AisleIngredient",
    # Shopping lists
    "parse_shopping_list",
    "ShoppingList",
    "RecipeItem",
    "IngredientItem",
    "ShoppingItem",
    "ShoppingListError",
    # Checked log
    "parse_checked_log",
    "checked_names",
    "compact_checked_log",
    "CheckEntry",
    # Value helpers
    "parse_value",
    "format_value",
    # Metadata. `__version__` is importable too, but dunder names stay out of
    # `__all__` so `from cooklang import *` does not export it.
    "UPSTREAM_VERSION",
]

__version__ = "0.5.0"

UPSTREAM_VERSION = "0.18.7"
"""The pinned cooklang-rs release these bindings are generated from."""
