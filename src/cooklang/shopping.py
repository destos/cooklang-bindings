"""Shopping lists and the checked log.

Two related file formats upstream parses:

``.shopping-list``
    Recipe references (``./pasta`` with an optional scale) and free-hand
    ingredients, nested by indentation.

``.shopping-checked``
    An append-only log of ``+ name`` / ``- name`` entries recording what has
    been picked up. Replaying it yields the currently-checked set; later
    entries win over earlier ones for the same ingredient.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ._ffi import ffi
from ._validate import require_str
from .errors import CooklangError
from .models import _trim

__all__ = [
    "ShoppingListError",
    "RecipeItem",
    "IngredientItem",
    "ShoppingList",
    "CheckEntry",
    "parse_shopping_list",
    "parse_checked_log",
    "checked_names",
    "compact_checked_log",
]


class ShoppingListError(CooklangError):
    """Raised when a shopping list cannot be parsed or serialized.

    It is a :class:`~cooklang.errors.CooklangError`, and so a ``ValueError``.
    """


@dataclass(frozen=True, slots=True)
class IngredientItem:
    """A free-hand ingredient line, e.g. ``salt{1%tsp}``.

    ``quantity_text`` is the raw amount the file gave, unparsed: ``"1%tsp"``
    here. :func:`cooklang.parse_value` will read it if you need a number. The
    name differs from :attr:`cooklang.models.Ingredient.quantity` on purpose:
    that one is a parsed :class:`~cooklang.models.Quantity`, and this is text.
    """

    name: str
    quantity_text: str | None = None

    def to_text(self) -> str:
        """Serialize to its ``.shopping-list`` line, newline included.

        Raises:
            ShoppingListError: If serialization fails.
        """
        return _write_items((self,))

    def __str__(self) -> str:
        """The name, with any amount in brackets: ``salt (1 tsp)``."""
        if not self.quantity_text:
            return self.name
        return f"{self.name} ({self.quantity_text.replace('%', ' ')})"


@dataclass(frozen=True, slots=True)
class RecipeItem:
    """A reference to another recipe, e.g. ``./Breakfast/Pancakes{2}``.

    ``path`` is stored without the leading ``./`` that marks the line as a
    recipe reference in the file. ``scale`` multiplies that recipe, as the
    ``scale`` argument to :func:`cooklang.parse` does; upstream calls it the
    multiplier.
    """

    path: str
    scale: float | None = None
    children: tuple[ShoppingItem, ...] = ()

    def to_text(self) -> str:
        """Serialize to its ``.shopping-list`` lines, children and newline included.

        Raises:
            ShoppingListError: If serialization fails.
        """
        return _write_items((self,))

    def __str__(self) -> str:
        """The path, with any scale: ``Breakfast/Pancakes ×2``."""
        if self.scale is None:
            return self.path
        return f"{self.path} ×{_trim(self.scale)}"


ShoppingItem = RecipeItem | IngredientItem
"""One line of a shopping list: a recipe reference or a free-hand ingredient."""


@dataclass(frozen=True, slots=True)
class ShoppingList:
    """A parsed shopping list.

    Iterate :attr:`items` for the lines in document order, or use
    :attr:`recipes` and :attr:`ingredients` for one kind.
    """

    items: tuple[ShoppingItem, ...] = ()

    @property
    def recipes(self) -> tuple[RecipeItem, ...]:
        return tuple(i for i in self.items if isinstance(i, RecipeItem))

    @property
    def ingredients(self) -> tuple[IngredientItem, ...]:
        return tuple(i for i in self.items if isinstance(i, IngredientItem))

    def to_text(self) -> str:
        """Serialize back to the ``.shopping-list`` format.

        Raises:
            ShoppingListError: If serialization fails.
        """
        return _write_items(self.items)


@dataclass(frozen=True, slots=True)
class CheckEntry:
    """One line of a ``.shopping-checked`` log.

    ``checked`` is ``True`` for a ``+ name`` line, an ingredient picked up, and
    ``False`` for ``- name``, one put back. It is keyword-only, so a call site
    reads ``CheckEntry("milk", checked=False)`` rather than a bare ``False``.
    """

    name: str
    checked: bool = field(kw_only=True)

    def to_text(self) -> str:
        """Serialize to its log line, newline included: ``+ milk``.

        Raises:
            ShoppingListError: If serialization fails.
        """
        try:
            return ffi.write_shopping_check_entry(_to_ffi_entry(self))
        except ffi.ShoppingListError as exc:
            raise ShoppingListError(str(exc)) from exc

    def __str__(self) -> str:
        return self.name


def _from_ffi_item(item: Any) -> ShoppingItem:
    """Convert an FFI item. Upstream's ``multiplier`` becomes ``scale``, and its
    ``quantity`` becomes ``quantity_text``."""
    if isinstance(item, ffi.ShoppingListItem.RECIPE):
        return RecipeItem(
            path=item.path,
            scale=item.multiplier,
            children=tuple(_from_ffi_item(c) for c in item.children),
        )
    return IngredientItem(name=item.name, quantity_text=item.quantity)


def _to_ffi_item(item: ShoppingItem) -> Any:
    if isinstance(item, RecipeItem):
        return ffi.ShoppingListItem.RECIPE(
            path=item.path,
            multiplier=item.scale,
            children=[_to_ffi_item(c) for c in item.children],
        )
    return ffi.ShoppingListItem.INGREDIENT(name=item.name, quantity=item.quantity_text)


def _write_items(items: Iterable[ShoppingItem]) -> str:
    try:
        return ffi.write_shopping_list(ffi.ShoppingList(items=[_to_ffi_item(i) for i in items]))
    except ffi.ShoppingListError as exc:
        raise ShoppingListError(str(exc)) from exc


def _from_ffi_entry(entry: Any) -> CheckEntry:
    return CheckEntry(name=entry.name, checked=isinstance(entry, ffi.CheckEntry.CHECKED))


def _to_ffi_entry(entry: CheckEntry) -> Any:
    if entry.checked:
        return ffi.CheckEntry.CHECKED(name=entry.name)
    return ffi.CheckEntry.UNCHECKED(name=entry.name)


def parse_shopping_list(text: str) -> ShoppingList:
    """Parse a ``.shopping-list`` file.

    Raises:
        ShoppingListError: If the list cannot be parsed.
        TypeError: If ``text`` is not a ``str``.
    """
    require_str("text", text)
    try:
        raw = ffi.parse_shopping_list(text)
    except ffi.ShoppingListError as exc:
        raise ShoppingListError(str(exc)) from exc
    return ShoppingList(items=tuple(_from_ffi_item(i) for i in raw.items))


def parse_checked_log(text: str) -> tuple[CheckEntry, ...]:
    """Parse a ``.shopping-checked`` log into its entries, in order.

    Raises:
        TypeError: If ``text`` is not a ``str``.
    """
    require_str("text", text)
    return tuple(_from_ffi_entry(e) for e in ffi.parse_shopping_checked(text))


def checked_names(entries: Sequence[CheckEntry]) -> tuple[str, ...]:
    """Replay a log and return the currently-checked names, lowercased and sorted.

    Later entries override earlier ones, so an ingredient checked then
    unchecked does not appear.
    """
    return tuple(ffi.shopping_checked_set([_to_ffi_entry(e) for e in entries]))


def compact_checked_log(
    entries: Sequence[CheckEntry], current_ingredients: Iterable[str]
) -> tuple[CheckEntry, ...]:
    """Drop stale entries and collapse the log so each ingredient appears once.

    Args:
        entries: The current log.
        current_ingredients: The fully-aggregated ingredient names as shown to
            the user. A `.shopping-list` on disk holds only recipe references,
            so expand those first — passing the raw list's own names would
            discard every entry as stale.
    """
    return tuple(
        _from_ffi_entry(e)
        for e in ffi.compact_shopping_checked(
            [_to_ffi_entry(e) for e in entries], list(current_ingredients)
        )
    )
