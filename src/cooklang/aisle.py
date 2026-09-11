"""Aisle configuration: ingredient categories and common names.

An aisle config maps ingredient names (and their aliases) to shopping
categories, and gives each group a single canonical name. It is the mechanism
behind `common_name_for`: a recipe writing ``@onions{2}`` and another writing
``@brown onion{1}`` can be reconciled to one name before their quantities are
totalled.

The format is the one upstream parses:

    [produce]
    onion|onions|brown onion
    fennel

    [dairy]
    butter|unsalted butter
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ._ffi import ffi
from ._validate import require_str
from .models import Quantity, Range

__all__ = ["AisleIngredient", "AisleCategory", "AisleConfig", "parse_aisle_config"]


@dataclass(frozen=True, slots=True)
class AisleIngredient:
    """One ingredient in a category, with any aliases that also map to it."""

    name: str
    aliases: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class AisleCategory:
    """A shopping category, e.g. ``produce``, and the ingredients under it."""

    name: str
    ingredients: tuple[AisleIngredient, ...] = ()

    def __str__(self) -> str:
        return self.name


class AisleConfig:
    """A parsed aisle configuration.

    Build one with :func:`parse_aisle_config` or :meth:`from_text`. Instances
    are immutable and safe to keep and reuse across parses. They hold an FFI
    object, so unlike the recipe model they are not dataclasses, but they still
    behave as values: two configs with the same categories compare equal and
    hash alike, and pickling one re-parses its source text on the other side
    rather than carrying a pointer that would dangle in another process.

    Args:
        text: The config source.

    Raises:
        TypeError: If ``text`` is not a ``str``.
    """

    __slots__ = ("_conf", "_categories", "_text")

    def __init__(self, text: str) -> None:
        self._text = require_str("text", text)
        conf = ffi.parse_aisle_config(text)
        self._conf = conf
        self._categories = tuple(
            AisleCategory(
                name=category.name,
                ingredients=tuple(
                    AisleIngredient(name=i.name, aliases=tuple(i.aliases))
                    for i in category.ingredients
                ),
            )
            for category in conf.categories()
        )

    @classmethod
    def from_text(cls, text: str) -> AisleConfig:
        """Parse an aisle configuration; the same as :func:`parse_aisle_config`.

        Raises:
            TypeError: If ``text`` is not a ``str``.
        """
        return cls(text)

    @property
    def categories(self) -> tuple[AisleCategory, ...]:
        """Every category, in the order the config file listed them."""
        return self._categories

    def category_for(self, ingredient_name: str) -> str | None:
        """The category an ingredient belongs to, or ``None`` if unlisted.

        Matches the way :meth:`common_name_for` does -- case-insensitively,
        and through aliases -- so the two never disagree about whether an
        ingredient is listed. Upstream's own lookup is exact-match only, which
        filed ``"Onions"`` under no category while resolving its common name
        to ``"onion"``; this tries that exact match first, then the common
        name.
        """
        name = require_str("ingredient_name", ingredient_name)
        return self._conf.category_for(name) or self._conf.category_for(
            self._conf.common_name_for(name)
        )

    def common_name_for(self, ingredient_name: str) -> str:
        """The canonical name for an ingredient, or the name itself if unlisted.

        Matches case-insensitively against both names and aliases, so
        ``"Onions"`` and ``"brown onion"`` both resolve to ``"onion"`` given a
        config that groups them. Never returns ``None``: an unknown ingredient
        is returned unchanged, which makes this safe to apply to a whole list.
        """
        return self._conf.common_name_for(require_str("ingredient_name", ingredient_name))

    def group_by_category(self, names: Iterable[str]) -> dict[str | None, tuple[str, ...]]:
        """Bucket ingredient names by category, for laying out a shopping list.

        Categories come back in config order, and anything the config does not
        list is grouped under ``None`` so it can be rendered as "other" rather
        than silently dropped.
        """
        buckets: dict[str | None, list[str]] = {}
        for name in names:
            buckets.setdefault(self.category_for(name), []).append(name)

        ordered: dict[str | None, tuple[str, ...]] = {}
        for category in self._categories:
            if category.name in buckets:
                ordered[category.name] = tuple(buckets.pop(category.name))
        for remaining in [key for key in buckets if key is not None]:
            ordered[remaining] = tuple(buckets.pop(remaining))
        if None in buckets:
            ordered[None] = tuple(buckets.pop(None))
        return ordered

    def apply_common_names(
        self, totals: Mapping[str, Iterable[Quantity]]
    ) -> dict[str, tuple[Quantity, ...]]:
        """Rewrite the keys of a combined-ingredient mapping to common names.

        Ingredients that collapse onto the same common name have their
        quantities merged by upstream, so this is not a plain key rename.

        Prefer ``combine_ingredients(..., aisle=config)`` when you are totalling
        a recipe; this is for totals that arrived from somewhere else.

        Args:
            totals: Ingredient name to its quantities, the shape
                :func:`cooklang.combine_ingredients` returns.

        Returns:
            The same shape, keyed by common name.
        """
        from .parser import _quantities_from_grouped, _to_ffi_value

        raw = {
            name: {
                ffi.GroupedQuantityKey(
                    name=quantity.unit or "",
                    unit_type=_quantity_type(quantity),
                ): _to_ffi_value(quantity.value)
                for quantity in quantities
            }
            for name, quantities in totals.items()
        }
        normalized = ffi.use_common_names(raw, self._conf)
        return {
            name: _quantities_from_grouped(grouped)
            for name, grouped in normalized.items()
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AisleConfig):
            return NotImplemented
        return self._categories == other._categories

    def __hash__(self) -> int:
        return hash(self._categories)

    def __reduce__(self) -> tuple[type[AisleConfig], tuple[str]]:
        return (type(self), (self._text,))

    def __repr__(self) -> str:
        return f"<AisleConfig {len(self._categories)} categories>"


def _quantity_type(quantity: Quantity) -> Any:
    """Classify a quantity the way upstream's grouping key expects."""
    value = quantity.value
    if value is None:
        return ffi.QuantityType.EMPTY
    if isinstance(value, Range):
        return ffi.QuantityType.RANGE
    if isinstance(value, str):
        return ffi.QuantityType.TEXT
    return ffi.QuantityType.NUMBER


def parse_aisle_config(text: str) -> AisleConfig:
    """Parse an aisle configuration file.

    Args:
        text: The config source.

    Raises:
        TypeError: If ``text`` is not a ``str``.
    """
    return AisleConfig(text)
