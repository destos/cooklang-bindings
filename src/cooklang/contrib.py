"""Helpers this project adds, which upstream does not provide.

Everything in the top-level :mod:`cooklang` namespace maps onto something
cooklang-rs exposes: :func:`~cooklang.parse` is upstream's parser,
:func:`~cooklang.combine_ingredients` is upstream's totalling, and the model
types are its data. This module is the other kind of code — conveniences built
*on top of* the bindings, which no upstream function backs.

The split is deliberate, and named after Django's ``django.contrib``. Two
things follow from it:

* **Upstream cannot change these.** They are ours, so a cooklang-rs release
  will not alter their behaviour, and their semantics are this project's to
  keep stable.
* **They encode opinions.** Whether an ingredient declaration block is noise,
  or whether an unmeasured mention is worth surfacing, are decisions about how
  *your* application reads a recipe — not facts about Cooklang. Keeping them
  out of the main namespace stops them being mistaken for parser semantics.

Import it explicitly::

    from cooklang import contrib
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import timedelta

from .models import Ingredient, Step, Timer

__all__ = ["unquantified_mentions", "is_declaration_only", "timer_duration"]

# Unit spellings a timer may use, mapped to the timedelta keyword they mean.
# Cooklang does not constrain unit names and the canonical parser carries no
# unit knowledge, so "min", "mins" and "Minutes" arrive as three distinct
# strings. Matching is case-insensitive.
_DURATION_UNITS = {
    "s": "seconds", "sec": "seconds", "secs": "seconds",
    "second": "seconds", "seconds": "seconds",
    "m": "minutes", "min": "minutes", "mins": "minutes",
    "minute": "minutes", "minutes": "minutes",
    "h": "hours", "hr": "hours", "hrs": "hours",
    "hour": "hours", "hours": "hours",
    "d": "days", "day": "days", "days": "days",
}


def unquantified_mentions(ingredients: Sequence[Ingredient]) -> dict[str, int]:
    """Count the mentions of each ingredient that carry no amount.

    :func:`~cooklang.combine_ingredients` totals what it can and says nothing
    about the rest: a recipe using ``@salt{2%tsp}`` and later a bare ``@salt``
    totals to ``2 tsp``, with the second mention absent from the result. For a
    shopping list that is right. For anything that needs to distinguish
    "2 tsp" from "2 tsp and more to taste", it is not.

    This counts what that total leaves out. Upstream cannot: its grouping map
    collapses every unquantified mention of a name into one entry, so the FFI
    knows only that at least one exists. Counting here is exact.

    Args:
        ingredients: Ingredients to count, usually ``recipe.ingredients``.

    Returns:
        Ingredient name to the number of mentions with no amount. Names with
        no such mention are absent, so the mapping is empty for a fully
        quantified recipe.

    Example:
        >>> import cooklang
        >>> from cooklang import contrib
        >>> recipe = cooklang.parse("Add @salt{2%tsp}.\\n\\nSeason with @salt.\\n")
        >>> cooklang.combine_ingredients(recipe.ingredients)["salt"]
        (Quantity(value=2, unit='tsp', text='2 tsp'),)
        >>> contrib.unquantified_mentions(recipe.ingredients)
        {'salt': 1}
    """
    return dict(
        Counter(item.name for item in ingredients if item.quantity is None)
    )


def is_declaration_only(step: Step) -> bool:
    """Whether a step is a bare block of ingredient declarations.

    Consecutive lines are one step, so a recipe written as a list of
    ingredients with no prose parses to a single step whose text is just those
    names in sequence. Importers from other formats emit that shape routinely,
    because they have no method text to weave the ingredients into.

    Whether to render such a step or drop it is a presentation decision, which
    is why it lives here rather than on :class:`~cooklang.Step`. The
    ingredients are on ``recipe.ingredients`` either way, so filtering the step
    loses nothing.

    Args:
        step: The step to test.

    Returns:
        Whether the step's text is exactly its own ingredient names in
        sequence.

    Example:
        >>> import cooklang
        >>> from cooklang import contrib
        >>> block = cooklang.parse("@olive oil{2%tbsp}\\n@leeks{2}\\n")
        >>> contrib.is_declaration_only(block.steps[0])
        True
        >>> prose = cooklang.parse("Fry the @leeks{2} in @olive oil{2%tbsp}.")
        >>> contrib.is_declaration_only(prose.steps[0])
        False
    """
    if not step.ingredients:
        return False
    return step.text == " ".join(item.name for item in step.ingredients)


def timer_duration(
    timer: Timer, *, assume_unit: str | None = None
) -> timedelta | None:
    """Interpret a timer's duration as a :class:`~datetime.timedelta`.

    A timer carries a number and a **free-text unit string**: upstream's
    canonical parser has no unit knowledge, so ``min``, ``mins`` and
    ``Minutes`` reach you as three unrelated strings and cannot be summed or
    compared. This maps the common spellings of seconds, minutes, hours and
    days onto a real duration.

    It returns ``None`` rather than guessing whenever the timer does not
    describe a definite length of time — a text duration such as
    ``~{a while}``, a range, an unrecognised unit, a timer with no quantity at
    all, or a bare ``~{20}`` with no unit. Distinguishing "no duration" from a
    wrong one matters more here than always producing a number.

    Args:
        timer: The timer to interpret.
        assume_unit: Unit to use when the timer gives none, for a corpus whose
            convention you know — ``"minutes"`` is the usual one. Left unset,
            an unlabelled duration returns ``None``.

    Returns:
        The duration, or ``None`` if it cannot be determined.

    Example:
        >>> import cooklang
        >>> from cooklang import contrib
        >>> recipe = cooklang.parse("Simmer for ~{45%mins}. Rest ~{1.5%h}.")
        >>> from datetime import timedelta
        >>> contrib.timer_duration(recipe.timers[0])
        datetime.timedelta(seconds=2700)
        >>> sum(
        ...     (contrib.timer_duration(t) for t in recipe.timers),
        ...     start=timedelta(),
        ... )
        datetime.timedelta(seconds=8100)

        Anything that is not a definite duration is ``None``, not a guess:

        >>> vague = cooklang.parse("Wait ~{a while}.").timers[0]
        >>> contrib.timer_duration(vague) is None
        True
    """
    quantity = timer.quantity
    if quantity is None or not isinstance(quantity.value, (int, float)):
        return None
    if isinstance(quantity.value, bool):  # bool is an int; never a duration
        return None

    unit = quantity.unit or assume_unit
    if unit is None:
        return None

    keyword = _DURATION_UNITS.get(unit.strip().lower())
    if keyword is None:
        return None

    return timedelta(**{keyword: quantity.value})
