"""Shopping lists and the checked log.

Two related file formats upstream parses:

``.shopping-list``
    Recipe references (``./pasta`` with an optional multiplier) and free-hand
    ingredients, nested by indentation.

``.shopping-checked``
    An append-only log of ``+ name`` / ``- name`` entries recording what has
    been picked up. Replaying it yields the currently-checked set; later
    entries win over earlier ones for the same ingredient.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ._ffi import ffi

__all__ = [
    "ShoppingListError",
    "RecipeItem",
    "IngredientItem",
    "ShoppingList",
    "Checked",
    "Unchecked",
    "CheckEntry",
    "parse_shopping_list",
    "parse_checked_log",
    "checked_names",
    "compact_checked_log",
]


class ShoppingListError(ValueError):
    """Raised when a shopping list cannot be parsed or serialized."""


@dataclass(frozen=True, slots=True)
class IngredientItem:
    """A free-hand ingredient line, e.g. ``salt{1%tsp}``.

    ``quantity`` is kept as the raw string the file gave, unparsed --
    :func:`cooklang.parse_value` will read it if you need a number.
    """

    name: str
    quantity: str | None = None

    def __str__(self) -> str:
        return f"{self.name}{{{self.quantity}}}" if self.quantity else self.name


@dataclass(frozen=True, slots=True)
class RecipeItem:
    """A reference to another recipe, e.g. ``./Breakfast/Pancakes{2}``.

    ``path`` is stored without the leading ``./`` that marks the line as a
    recipe reference in the file. ``multiplier`` scales that recipe.
    """

    path: str
    multiplier: float | None = None
    children: tuple["RecipeItem | IngredientItem", ...] = ()

    def __str__(self) -> str:
        if self.multiplier is None:
            return f"./{self.path}"
        scale = int(self.multiplier) if float(self.multiplier).is_integer() else self.multiplier
        return f"./{self.path}{{{scale}}}"


@dataclass(frozen=True, slots=True)
class ShoppingList:
    """A parsed shopping list."""

    items: tuple[RecipeItem | IngredientItem, ...] = ()

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
        try:
            return ffi.write_shopping_list(ffi.ShoppingList(items=[_to_ffi_item(i) for i in self.items]))
        except ffi.ShoppingListError as exc:
            raise ShoppingListError(str(exc)) from exc

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


@dataclass(frozen=True, slots=True)
class Checked:
    """A log entry recording that an ingredient was picked up."""

    name: str
    checked: bool = field(default=True, init=False)

    def to_text(self) -> str:
        return _write_entry(self)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Unchecked:
    """A log entry recording that an ingredient was put back."""

    name: str
    checked: bool = field(default=False, init=False)

    def to_text(self) -> str:
        return _write_entry(self)

    def __str__(self) -> str:
        return self.name


CheckEntry = Checked | Unchecked


def _from_ffi_item(item: Any) -> RecipeItem | IngredientItem:
    if isinstance(item, ffi.ShoppingListItem.RECIPE):
        return RecipeItem(
            path=item.path,
            multiplier=item.multiplier,
            children=tuple(_from_ffi_item(c) for c in item.children),
        )
    return IngredientItem(name=item.name, quantity=item.quantity)


def _to_ffi_item(item: RecipeItem | IngredientItem) -> Any:
    if isinstance(item, RecipeItem):
        return ffi.ShoppingListItem.RECIPE(
            path=item.path,
            multiplier=item.multiplier,
            children=[_to_ffi_item(c) for c in item.children],
        )
    return ffi.ShoppingListItem.INGREDIENT(name=item.name, quantity=item.quantity)


def _from_ffi_entry(entry: Any) -> CheckEntry:
    if isinstance(entry, ffi.CheckEntry.CHECKED):
        return Checked(name=entry.name)
    return Unchecked(name=entry.name)


def _to_ffi_entry(entry: CheckEntry) -> Any:
    if isinstance(entry, Checked):
        return ffi.CheckEntry.CHECKED(name=entry.name)
    return ffi.CheckEntry.UNCHECKED(name=entry.name)


def _write_entry(entry: CheckEntry) -> str:
    try:
        return ffi.write_shopping_check_entry(_to_ffi_entry(entry))
    except ffi.ShoppingListError as exc:
        raise ShoppingListError(str(exc)) from exc


def parse_shopping_list(text: str) -> ShoppingList:
    """Parse a ``.shopping-list`` file.

    Raises:
        ShoppingListError: If the list cannot be parsed.
        TypeError: If ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
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
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
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
