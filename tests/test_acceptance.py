"""The end-to-end acceptance recipe from the project brief.

Expected: title "Test", servings 4, one section named "Prep", one note,
two steps, one ingredient, one cookware, one timer.
"""

from __future__ import annotations

import pytest

import cooklang_rs

RECIPE = """---
title: Test
servings: 4
---

== Prep ==

Chop the @onion{1}.

> A note that is not a step.

Fry it in a #pan{} for ~{5%minutes}.
"""


@pytest.fixture(scope="module")
def recipe():
    return cooklang_rs.parse(RECIPE)


def test_title(recipe):
    assert recipe.title == "Test"


def test_servings(recipe):
    assert recipe.servings == 4


def test_one_section_named_prep(recipe):
    assert len(recipe.sections) == 1
    assert recipe.sections[0].name == "Prep"


def test_one_note(recipe):
    assert len(recipe.notes) == 1
    assert recipe.notes[0].text == "A note that is not a step."


def test_two_steps(recipe):
    assert len(recipe.steps) == 2
    assert recipe.method == ("Chop the onion.", "Fry it in a pan for 5 minutes.")


def test_one_ingredient(recipe):
    assert len(recipe.ingredients) == 1
    onion = recipe.ingredients[0]
    assert onion.name == "onion"
    assert onion.quantity.value == 1
    assert onion.quantity.unit is None


def test_one_cookware(recipe):
    assert len(recipe.cookware) == 1
    assert recipe.cookware[0].name == "pan"


def test_one_timer(recipe):
    assert len(recipe.timers) == 1
    timer = recipe.timers[0]
    assert timer.name is None
    assert timer.quantity.value == 5
    assert timer.quantity.unit == "minutes"


def test_components_are_attached_to_their_own_steps(recipe):
    first, second = recipe.steps

    assert [i.name for i in first.ingredients] == ["onion"]
    assert first.cookware == () and first.timers == ()
    assert [c.name for c in second.cookware] == ["pan"]
    assert len(second.timers) == 1


def test_everything_at_once(recipe):
    """The brief's checklist, as one assertion."""
    assert (
        recipe.title,
        recipe.servings,
        [s.name for s in recipe.sections],
        len(recipe.notes),
        len(recipe.steps),
        len(recipe.ingredients),
        len(recipe.cookware),
        len(recipe.timers),
    ) == ("Test", 4, ["Prep"], 1, 2, 1, 1, 1)
