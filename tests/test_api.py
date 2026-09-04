"""Tests for the Pythonic layer over the generated bindings."""

from __future__ import annotations

import pytest

import cooklang_rs
from cooklang_rs import Range


def test_pins_the_upstream_version():
    assert cooklang_rs.UPSTREAM_VERSION == "0.18.7"


def test_empty_input_is_an_empty_recipe():
    recipe = cooklang_rs.parse("")

    assert recipe.steps == ()
    assert recipe.ingredients == ()
    assert recipe.title is None
    assert recipe.servings is None
    assert recipe.tags == ()


def test_non_string_input_is_a_type_error():
    with pytest.raises(TypeError):
        cooklang_rs.parse(None)


def test_content_before_any_heading_is_an_unnamed_section():
    recipe = cooklang_rs.parse("Mix it.\n\n== Later ==\n\nBake it.\n")

    assert [s.name for s in recipe.sections] == [None, "Later"]


def test_step_numbers_run_across_sections():
    recipe = cooklang_rs.parse("== A ==\n\nOne.\n\n== B ==\n\nTwo.\n\nThree.\n")

    assert [s.number for s in recipe.steps] == [1, 2, 3]


class TestQuantities:
    def test_whole_numbers_are_ints(self):
        quantity = cooklang_rs.parse("@flour{500%g}").ingredients[0].quantity

        assert quantity.value == 500
        assert isinstance(quantity.value, int)
        assert quantity.unit == "g"

    def test_fractional_amounts(self):
        quantity = cooklang_rs.parse("@milk{2.5%cups}").ingredients[0].quantity

        assert quantity.value == 2.5
        assert quantity.unit == "cups"

    def test_fractions_are_preserved_in_the_display_text(self):
        quantity = cooklang_rs.parse("@butter{1/2%cup}").ingredients[0].quantity

        assert quantity.value == 0.5
        assert quantity.text == "1/2 cup"

    def test_ranges_are_text_under_the_canonical_parser(self):
        """Ranges are a cooklang-rs *extension*, off in canonical mode.

        Upstream's `CooklangParser::canonical()` reports `1-2` as a text
        amount rather than a range. The `Range` type stays in the model
        because the FFI can express it, but a canonical parse never yields
        one. Asserted so a future upstream bump that enables extensions
        shows up here rather than silently changing a consumer's types.
        """
        quantity = cooklang_rs.parse("@onion{1-2}").ingredients[0].quantity

        assert quantity.value == "1-2"
        assert not isinstance(quantity.value, Range)

    def test_text_amounts(self):
        quantity = cooklang_rs.parse("@salt{a pinch}").ingredients[0].quantity

        assert quantity.value == "a pinch"
        assert quantity.unit is None

    def test_no_amount_is_none(self):
        recipe = cooklang_rs.parse("@salt{} and @pepper")

        assert [i.quantity for i in recipe.ingredients] == [None, None]

    def test_str_renders_the_display_text(self):
        quantity = cooklang_rs.parse("@flour{500%g}").ingredients[0].quantity

        assert str(quantity) == "500 g"


class TestScaling:
    SOURCE = "---\nservings: 2\n---\n\nAdd @flour{200%g} and @eggs{2}.\n"

    def test_default_is_unscaled(self):
        recipe = cooklang_rs.parse(self.SOURCE)

        assert [i.quantity.value for i in recipe.ingredients] == [200, 2]

    def test_doubling(self):
        recipe = cooklang_rs.parse(self.SOURCE, scale=2.0)

        assert [i.quantity.value for i in recipe.ingredients] == [400, 4]

    def test_halving(self):
        recipe = cooklang_rs.parse(self.SOURCE, scale=0.5)

        assert [i.quantity.value for i in recipe.ingredients] == [100, 1]


class TestIngredientDetail:
    def test_descriptor_becomes_a_note(self):
        ingredient = cooklang_rs.parse("@butter{2%tbsp}(softened)").ingredients[0]

        assert ingredient.name == "butter"
        assert ingredient.note == "softened"

    def test_multiword_names(self):
        ingredient = cooklang_rs.parse("@unsalted chicken stock{1%L}").ingredients[0]

        assert ingredient.name == "unsalted chicken stock"

    def test_repeats_are_listed_once_per_occurrence(self):
        recipe = cooklang_rs.parse("Add @salt{1%tsp}.\n\nAdd more @salt{2%tsp}.\n")

        assert [i.name for i in recipe.ingredients] == ["salt", "salt"]

    def test_unicode_survives_the_round_trip(self):
        recipe = cooklang_rs.parse("Add @jalapeño{2} and @crème fraîche{100%g}.")

        assert [i.name for i in recipe.ingredients] == ["jalapeño", "crème fraîche"]
        assert recipe.steps[0].text == "Add jalapeño and crème fraîche."


class TestCombineIngredients:
    """Also the regression test for the unhashable-record fixup in `_ffi`.

    Without it, `combine_ingredients` raises
    `TypeError: cannot use 'GroupedQuantityKey' as a dict key`.
    """

    def test_same_unit_amounts_are_summed(self):
        recipe = cooklang_rs.parse("Add @salt{2%tsp} then @salt{3%tsp}.")

        totals = cooklang_rs.combine_ingredients(recipe.ingredients)

        assert [(q.value, q.unit) for q in totals["salt"]] == [(5, "tsp")]

    def test_distinct_ingredients_are_kept_apart(self):
        recipe = cooklang_rs.parse("Add @salt{1%tsp} and @pepper{2%tsp}.")

        totals = cooklang_rs.combine_ingredients(recipe.ingredients)

        assert set(totals) == {"salt", "pepper"}

    def test_ingredients_without_amounts_are_still_listed(self):
        recipe = cooklang_rs.parse("Add @salt{} and @pepper.")

        totals = cooklang_rs.combine_ingredients(recipe.ingredients)

        assert set(totals) == {"salt", "pepper"}

    def test_incompatible_units_stay_separate(self):
        recipe = cooklang_rs.parse("Add @salt{1%tsp} then @salt{2%pinches}.")

        totals = cooklang_rs.combine_ingredients(recipe.ingredients)

        assert sorted(q.unit for q in totals["salt"]) == ["pinches", "tsp"]


class TestModelTypes:
    def test_recipe_types_are_hashable_and_comparable(self):
        one = cooklang_rs.parse("@salt{1%tsp}").ingredients[0]
        two = cooklang_rs.parse("@salt{1%tsp}").ingredients[0]

        assert one == two
        assert len({one, two}) == 1

    def test_no_ffi_objects_leak_into_the_model(self):
        recipe = cooklang_rs.parse("Fry @egg{1} in a #pan{} for ~{2%minutes}.")

        for obj in (*recipe.ingredients, *recipe.cookware, *recipe.timers, *recipe.steps):
            assert type(obj).__module__.startswith("cooklang_rs")

    def test_section_iteration_yields_blocks_in_order(self):
        recipe = cooklang_rs.parse("One.\n\n> A note.\n\nTwo.\n")

        kinds = [type(b).__name__ for b in recipe.sections[0]]
        assert kinds == ["Step", "Note", "Step"]

    def test_recipe_str_is_the_title(self):
        assert str(cooklang_rs.parse("---\ntitle: Pie\n---\n\nBake.")) == "Pie"
