"""`Step.items` — the positional view of a step.

The component tuples on a Step answer "what does this step use". These answer
"where", which is what inline markup needs: rendering "whisk the **flour
300 g**" rather than prose with a summary above it.
"""

from __future__ import annotations

import cooklang
from cooklang import CookwareRef, IngredientRef, TextItem, TimerRef


def _only_step(source):
    return cooklang.parse(source).steps[0]


class TestTextIsUnchanged:
    """`text` is what every existing consumer reads; items are purely additive."""

    def test_items_reproduce_text_exactly(self):
        step = _only_step("Whisk @flour{300%g} in a #bowl{} for ~{2%minutes}.")

        assert "".join(str(item) for item in step.items).strip() == step.text

    def test_text_is_still_markup_free(self):
        step = _only_step("Whisk @flour{300%g} in a #bowl{}.")

        assert step.text == "Whisk flour in a bowl."

    def test_a_step_can_still_be_built_positionally(self):
        """`items` defaults to (), so existing construction keeps working."""
        step = cooklang.Step(1, "Stir it.")

        assert step.items == ()
        assert step.text == "Stir it."


class TestTheSameIngredientTwice:
    """The motivating case: 300 g in the pastry, 30 g for dusting."""

    SOURCE = "Rub @flour{300%g} into the butter.\n\nRoll on a @flour{30%g} surface.\n"

    def test_each_occurrence_has_its_own_index(self):
        recipe = cooklang.parse(self.SOURCE)
        first, second = recipe.steps

        first_ref = next(i for i in first.items if isinstance(i, IngredientRef))
        second_ref = next(i for i in second.items if isinstance(i, IngredientRef))

        assert first_ref.index != second_ref.index

    def test_each_index_resolves_to_its_own_amount(self):
        recipe = cooklang.parse(self.SOURCE)
        first, second = recipe.steps

        first_ref = next(i for i in first.items if isinstance(i, IngredientRef))
        second_ref = next(i for i in second.items if isinstance(i, IngredientRef))

        assert first_ref.ingredient.quantity.text == "300 g"
        assert second_ref.ingredient.quantity.text == "30 g"

    def test_the_index_points_into_the_recipe_ingredient_list(self):
        recipe = cooklang.parse(self.SOURCE)

        for step in recipe.steps:
            for item in step.items:
                if isinstance(item, IngredientRef):
                    assert recipe.ingredients[item.index] is item.ingredient


class TestResolutionCannotDrift:
    """A ref carries the same object the recipe holds, not a copy."""

    def test_ingredient_is_the_same_instance(self):
        recipe = cooklang.parse("Add @salt{1%tsp}.")
        ref = next(i for i in recipe.steps[0].items if isinstance(i, IngredientRef))

        assert ref.ingredient is recipe.ingredients[ref.index]

    def test_cookware_is_the_same_instance(self):
        recipe = cooklang.parse("Use a #pan{}.")
        ref = next(i for i in recipe.steps[0].items if isinstance(i, CookwareRef))

        assert ref.cookware is recipe.cookware[ref.index]

    def test_timer_is_the_same_instance(self):
        recipe = cooklang.parse("Wait ~{5%minutes}.")
        ref = next(i for i in recipe.steps[0].items if isinstance(i, TimerRef))

        assert ref.timer is recipe.timers[ref.index]


class TestEdgeCases:
    def test_plain_prose_is_a_single_text_item(self):
        step = _only_step("Preheat the oven.")

        assert step.items == (TextItem(value="Preheat the oven."),)

    def test_a_step_that_is_only_a_component(self):
        step = _only_step("@salt{1%tsp}")

        assert len(step.items) == 1
        assert isinstance(step.items[0], IngredientRef)
        assert step.text == "salt"

    def test_an_unnamed_timer_renders_as_its_duration(self):
        step = _only_step("Wait ~{5%minutes}.")
        ref = next(i for i in step.items if isinstance(i, TimerRef))

        assert ref.timer.name is None
        assert str(ref) == "5 minutes"

    def test_a_named_timer_also_renders_as_its_duration(self):
        step = _only_step("Boil for ~eggs{3%minutes}.")
        ref = next(i for i in step.items if isinstance(i, TimerRef))

        assert ref.timer.name == "eggs"
        assert str(ref) == "3 minutes"

    def test_items_are_frozen_and_comparable(self):
        one = _only_step("Add @salt{1%tsp}.")
        two = _only_step("Add @salt{1%tsp}.")

        assert one.items == two.items
        assert len({one.items, two.items}) == 1

    def test_notes_have_no_items(self):
        """Only steps carry positions; a note is plain text."""
        recipe = cooklang.parse("Stir.\n\n> A note.\n")

        assert not hasattr(recipe.notes[0], "items")


def test_marking_up_a_step_inline():
    """The use case, end to end: components marked at their point of use."""
    step = _only_step("Whisk @flour{300%g} and @salt{1%tsp} in a #bowl{}.")

    rendered = "".join(
        f"**{item.ingredient.name} {item.ingredient.quantity.text}**"
        if isinstance(item, IngredientRef)
        else str(item)
        for item in step.items
    )

    assert rendered == "Whisk **flour 300 g** and **salt 1 tsp** in a bowl."
