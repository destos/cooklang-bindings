"""Turns the generated UniFFI objects into the plain types in :mod:`models`."""

from __future__ import annotations

from typing import Any, Sequence

from ._ffi import ffi
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

__all__ = ["parse", "combine_ingredients", "CooklangError"]


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


def _step_text(items: Any, ingredients: list[Ingredient], cookware: list[Cookware],
               timers: list[Timer]) -> str:
    """Render a step's items back to prose, with components rendered inline."""
    parts: list[str] = []
    for item in items:
        if isinstance(item, ffi.Item.TEXT):
            parts.append(item.value)
        elif isinstance(item, ffi.Item.INGREDIENT_REF):
            parts.append(ingredients[item.index].name)
        elif isinstance(item, ffi.Item.COOKWARE_REF):
            parts.append(cookware[item.index].name)
        elif isinstance(item, ffi.Item.TIMER_REF):
            parts.append(str(timers[item.index]))
    return "".join(parts).strip()


def parse(text: str, *, scale: float = 1.0) -> Recipe:
    """Parse Cooklang source into a :class:`~cooklang_rs.models.Recipe`.

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
            blocks.append(
                Step(
                    number=step_number,
                    text=_step_text(raw_step.items, ingredients, cookware, timers),
                    ingredients=tuple(ingredients[i] for i in raw_step.ingredient_refs),
                    cookware=tuple(cookware[i] for i in raw_step.cookware_refs),
                    timers=tuple(timers[i] for i in raw_step.timer_refs),
                )
            )
        sections.append(Section(name=raw_section.title or None, blocks=tuple(blocks)))

    return Recipe(
        metadata=_metadata(raw),
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


def combine_ingredients(ingredients: Sequence[Ingredient]) -> dict[str, tuple[Quantity, ...]]:
    """Total up repeated ingredients, letting upstream do the unit arithmetic.

    Ingredients of the same name are summed per unit, so two ``@salt{2%tsp}``
    and ``@salt{3%tsp}`` mentions become a single ``5 tsp``. Amounts in units
    that cannot be added together stay as separate entries under one name.

    Returns a mapping of ingredient name to its totals.
    """
    raw_ingredients = [
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

    combined: dict[str, tuple[Quantity, ...]] = {}
    for name, grouped in ffi.combine_ingredients(raw_ingredients).items():
        totals = []
        for key, value in grouped.items():
            if isinstance(value, ffi.Value.EMPTY):
                continue
            totals.append(
                Quantity(
                    value=_value(value),
                    unit=key.name or None,
                    text=(ffi.format_value(value) or "").strip(),
                )
            )
        combined[name] = tuple(totals)
    return combined
