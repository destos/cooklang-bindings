"""Turns the generated UniFFI objects into the plain types in :mod:`models`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from ._ffi import ffi
from .models import (
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

__all__ = ["parse", "combine_ingredients", "CooklangError"]

if TYPE_CHECKING:  # pragma: no cover
    from .aisle import AisleConfig


class CooklangError(ValueError):
    """Raised when the upstream parser cannot parse the input at all.

    Cooklang is a forgiving format and almost any text is a valid recipe, so
    this is rare. Malformed metadata or unclosed markup does not raise; it
    parses to whatever upstream decides it means.
    """


# Standard metadata keys, exposed under Python-friendly names.
_STD_KEYS = {
    "title": ffi.StdKey.TITLE,
    "description": ffi.StdKey.DESCRIPTION,
    "author": ffi.StdKey.AUTHOR,
    "source": ffi.StdKey.SOURCE,
    "course": ffi.StdKey.COURSE,
    "time": ffi.StdKey.TIME,
    "prep_time": ffi.StdKey.PREP_TIME,
    "cook_time": ffi.StdKey.COOK_TIME,
    "difficulty": ffi.StdKey.DIFFICULTY,
    "cuisine": ffi.StdKey.CUISINE,
    "diet": ffi.StdKey.DIET,
    "images": ffi.StdKey.IMAGES,
    "locale": ffi.StdKey.LOCALE,
}


def _value(raw: Any) -> int | float | str | Range | None:
    if isinstance(raw, ffi.Value.NUMBER):
        number = raw.value
        return int(number) if float(number).is_integer() else number
    if isinstance(raw, ffi.Value.RANGE):
        return Range(start=raw.start, end=raw.end)
    if isinstance(raw, ffi.Value.TEXT):
        return raw.value
    return None


def _quantity(amount: Any) -> Quantity | None:
    """Convert an FFI ``Amount``. Returns ``None`` for ``@salt{}`` and bare ``@salt``."""
    if amount is None:
        return None
    value = _value(amount.quantity)
    unit = amount.units or None
    if value is None and unit is None:
        return None
    return Quantity(value=value, unit=unit, text=ffi.format_amount(amount).strip())


def _ingredient(raw: Any) -> Ingredient:
    reference = None
    if raw.reference is not None:
        parts = [*raw.reference.components, raw.reference.name]
        reference = "/".join(parts)
    return Ingredient(
        name=raw.name,
        quantity=_quantity(raw.amount),
        note=raw.descriptor or None,
        recipe_reference=reference,
    )


def _cookware(raw: Any) -> Cookware:
    return Cookware(name=raw.name, quantity=_quantity(raw.amount))


def _timer(raw: Any) -> Timer:
    return Timer(name=raw.name or None, quantity=_quantity(raw.amount))


def _name_and_url(raw: Any) -> NameAndUrl | None:
    if raw is None or (raw.name is None and raw.url is None):
        return None
    return NameAndUrl(name=raw.name, url=raw.url)


def _recipe_time(raw: Any) -> RecipeTime | None:
    """Flatten upstream's Total/Composed split into one shape.

    A composed time gets a `total` too, summed from whichever halves are
    present, so callers can read `.total` without first asking which form the
    recipe happened to use.
    """
    if raw is None:
        return None
    if isinstance(raw, ffi.RecipeTime.TOTAL):
        return RecipeTime(total=int(raw.minutes))
    prep = None if raw.prep_time is None else int(raw.prep_time)
    cook = None if raw.cook_time is None else int(raw.cook_time)
    total = None if prep is None and cook is None else (prep or 0) + (cook or 0)
    return RecipeTime(total=total, prep=prep, cook=cook)


def _metadata(recipe: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    for name, key in _STD_KEYS.items():
        value = ffi.metadata_get_std(recipe, key)
        if value is not None:
            metadata[name] = value

    tags = ffi.metadata_tags(recipe)
    if tags:
        metadata["tags"] = list(tags)

    servings = ffi.metadata_servings(recipe)
    if isinstance(servings, ffi.Servings.NUMBER):
        metadata["servings"] = int(servings.value)
    elif isinstance(servings, ffi.Servings.TEXT):
        metadata["servings"] = servings.value

    for key in ffi.metadata_custom_keys(recipe):
        value = ffi.metadata_get(recipe, key)
        if value is not None:
            metadata.setdefault(key, value)

    return metadata


def _items(
    raw_items: Any,
    ingredients: list[Ingredient],
    cookware: list[Cookware],
    timers: list[Timer],
) -> tuple[Item, ...]:
    """Convert a step's items, resolving each reference as it goes.

    A reference carries both its index and the resolved object. The object is
    the same instance held in the recipe's component list rather than a copy,
    so a caller can use either without the two being able to disagree.
    """
    items: list[Item] = []
    for item in raw_items:
        if isinstance(item, ffi.Item.TEXT):
            items.append(TextItem(value=item.value))
        elif isinstance(item, ffi.Item.INGREDIENT_REF):
            items.append(
                IngredientRef(index=item.index, ingredient=ingredients[item.index])
            )
        elif isinstance(item, ffi.Item.COOKWARE_REF):
            items.append(CookwareRef(index=item.index, cookware=cookware[item.index]))
        elif isinstance(item, ffi.Item.TIMER_REF):
            items.append(TimerRef(index=item.index, timer=timers[item.index]))
    return tuple(items)


def _step_text(items: tuple[Item, ...]) -> str:
    """Render a step's items back to prose, with components rendered inline."""
    return "".join(str(item) for item in items).strip()


def parse(text: str, *, scale: float = 1.0) -> Recipe:
    """Parse Cooklang source into a :class:`~cooklang.models.Recipe`.

    Args:
        text: The recipe source.
        scale: Factor applied to every quantity. ``2.0`` doubles the recipe.

    Raises:
        CooklangError: If the upstream parser fails outright.
        TypeError: If ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    try:
        raw = ffi.parse_recipe(text, float(scale))
    except ffi.InternalError as exc:
        raise CooklangError(str(exc)) from exc

    ingredients = [_ingredient(i) for i in raw.ingredients()]
    cookware = [_cookware(c) for c in raw.cookware()]
    timers = [_timer(t) for t in raw.timers()]

    sections: list[Section] = []
    step_number = 0
    for raw_section in raw.sections():
        blocks: list[Step | Note] = []
        for block in raw_section.blocks:
            if isinstance(block, ffi.Block.NOTE_BLOCK):
                blocks.append(Note(text=block[0].text.strip()))
                continue
            raw_step = block[0]
            step_number += 1
            step_items = _items(raw_step.items, ingredients, cookware, timers)
            blocks.append(
                Step(
                    number=step_number,
                    text=_step_text(step_items),
                    items=step_items,
                    ingredients=tuple(ingredients[i] for i in raw_step.ingredient_refs),
                    cookware=tuple(cookware[i] for i in raw_step.cookware_refs),
                    timers=tuple(timers[i] for i in raw_step.timer_refs),
                )
            )
        sections.append(Section(name=raw_section.title or None, blocks=tuple(blocks)))

    return Recipe(
        metadata=_metadata(raw),
        author=_name_and_url(ffi.metadata_author(raw)),
        source=_name_and_url(ffi.metadata_source(raw)),
        time=_recipe_time(ffi.metadata_time(raw)),
        sections=tuple(sections),
        ingredients=tuple(ingredients),
        cookware=tuple(cookware),
        timers=tuple(timers),
    )


def _to_ffi_value(value: int | float | str | Range | None) -> Any:
    if value is None:
        return ffi.Value.EMPTY()
    if isinstance(value, Range):
        return ffi.Value.RANGE(start=float(value.start), end=float(value.end))
    if isinstance(value, bool):
        return ffi.Value.TEXT(value=str(value))
    if isinstance(value, (int, float)):
        return ffi.Value.NUMBER(value=float(value))
    return ffi.Value.TEXT(value=str(value))


def _quantities_from_grouped(grouped: Any) -> tuple[Quantity, ...]:
    """Convert one entry of upstream's `GroupedQuantity` map to Quantities."""
    quantities = []
    for key, value in grouped.items():
        if isinstance(value, ffi.Value.EMPTY):
            continue
        unit = key.name or None
        quantities.append(
            Quantity(
                value=_value(value),
                unit=unit,
                # format_amount, not format_value: `text` must include the unit
                # here exactly as it does on a Quantity from parse(). Using
                # format_value gave "2" where parse() gives "2 tsp", so the
                # same type meant two different things depending on where it
                # came from, and rendering a total showed a bare number.
                text=ffi.format_amount(
                    ffi.Amount(quantity=value, units=unit)
                ).strip(),
            )
        )
    return tuple(quantities)


def _to_ffi_ingredients(ingredients: Sequence[Ingredient]) -> list[Any]:
    return [
        ffi.Ingredient(
            name=item.name,
            amount=(
                None
                if item.quantity is None
                else ffi.Amount(
                    quantity=_to_ffi_value(item.quantity.value),
                    units=item.quantity.unit,
                )
            ),
            descriptor=item.note,
            reference=None,
        )
        for item in ingredients
    ]


def combine_ingredients(
    ingredients: Sequence[Ingredient],
    *,
    indices: Sequence[int] | None = None,
    aisle: "AisleConfig | None" = None,
) -> dict[str, tuple[Quantity, ...]]:
    """Total up repeated ingredients, letting upstream do the unit arithmetic.

    Ingredients of the same name are summed per unit, so two ``@salt{2%tsp}``
    and ``@salt{3%tsp}`` mentions become a single ``5 tsp``. Amounts in units
    that cannot be added together stay as separate entries under one name.

    Args:
        ingredients: The ingredients to total.
        indices: Positions to include, for totalling a subset — the steps a
            user ticked, say. ``None`` (the default) uses all of them.
        aisle: An :class:`~cooklang.aisle.AisleConfig`. When given,
            ingredient names are resolved to their common names *before*
            totalling, so ``@onions{1}`` and ``@brown onion{2}`` combine into
            one ``onion`` entry instead of two.

    Returns:
        A mapping of ingredient name to its totals.

    Raises:
        IndexError: If ``indices`` refers to a position that does not exist.
    """
    raw_ingredients = _to_ffi_ingredients(ingredients)

    if indices is None:
        selected = list(range(len(raw_ingredients)))
    else:
        selected = [int(i) for i in indices]
        for index in selected:
            if not 0 <= index < len(raw_ingredients):
                raise IndexError(
                    f"index {index} out of range for {len(raw_ingredients)} ingredients"
                )

    combined = ffi.combine_ingredients_selected(raw_ingredients, selected)

    if aisle is not None:
        combined = ffi.use_common_names(combined, aisle._conf)

    return {
        name: _quantities_from_grouped(grouped) for name, grouped in combined.items()
    }
