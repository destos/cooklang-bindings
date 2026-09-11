"""Small conveniences on the public surface: aliases, durations, exports."""

from __future__ import annotations

from datetime import timedelta
from typing import get_args

import cooklang
from cooklang import contrib


def test_block_alias_names_what_a_section_holds():
    assert set(get_args(cooklang.Block)) == {cooklang.Step, cooklang.Note}


def test_shopping_item_alias_names_what_a_list_holds():
    assert set(get_args(cooklang.ShoppingItem)) == {cooklang.RecipeItem, cooklang.IngredientItem}


class TestRecipeTimeDurations:
    def test_each_field_has_a_timedelta(self):
        time = cooklang.RecipeTime(total=45, prep=15, cook=30)

        assert (time.total_duration, time.prep_duration, time.cook_duration) == (
            timedelta(minutes=45), timedelta(minutes=15), timedelta(minutes=30),
        )

    def test_missing_fields_are_none_not_zero(self):
        assert cooklang.RecipeTime(total=45).prep_duration is None

    def test_recipe_time_adds_to_timer_time(self):
        """The reason these exist: no unit conversion between the two."""
        recipe = cooklang.parse("---\ntime: 30\n---\n\nRest ~{1%h}.")

        total = recipe.time.total_duration + contrib.timer_duration(recipe.timers[0])

        assert total == timedelta(minutes=90)


def test_indices_accepts_any_iterable():
    recipe = cooklang.parse("Add @salt{1%tsp}, @salt{2%tsp} and @pepper{1%tsp}.")

    totals = cooklang.combine_ingredients(recipe.ingredients, indices=iter([0, 1]))

    assert [(q.value, q.unit) for q in totals["salt"]] == [(3, "tsp")]
    assert "pepper" not in totals


def test_version_is_importable_but_not_star_exported():
    assert isinstance(cooklang.__version__, str)
    assert "__version__" not in cooklang.__all__
