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
from typing import Iterable, Sequence

from .models import Ingredient, Step

__all__ = ["unquantified_mentions", "is_declaration_only"]


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
