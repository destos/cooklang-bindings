"""Proves every exported UniFFI function is callable and correct from Python.

The point of this file is coverage of the *binding*, not the parser: UniFFI's
Python backend is the least-exercised of upstream's three targets, so each
exported function gets called here at least once. `test_every_exported_function`
is the guard that keeps this honest — it fails if upstream adds a function that
nothing in this file touches.
"""

from __future__ import annotations

import inspect

import pytest

import cooklang
from cooklang._ffi import ffi

# Every function upstream exports, and how this package reaches it. Keeping
# this explicit means `test_the_coverage_map_matches_upstream` fails the moment
# upstream adds or removes a function, rather than the gap going unnoticed.
RECIPE = "Chop @onion{1} in a #pan{} for ~{5%minutes}."

_COVERAGE = {
    # Recipes
    "parse_recipe": "cooklang.parse()",
    "format_amount": "Quantity.text",
    "format_value": "cooklang.format_value()",
    "parse_value": "cooklang.parse_value()",
    # Metadata
    "metadata_title": "Recipe.title",
    "metadata_description": "Recipe.description",
    "metadata_tags": "Recipe.tags",
    "metadata_servings": "Recipe.servings",
    "metadata_author": "Recipe.author",
    "metadata_source": "Recipe.source",
    "metadata_time": "Recipe.time",
    "metadata_get": "Recipe.metadata",
    "metadata_get_std": "Recipe.metadata",
    "metadata_custom_keys": "Recipe.metadata",
    # Reference resolution -- done eagerly at parse time, so the Python model
    # never hands out an unresolved reference for a caller to dereference.
    "deref_component": "raw FFI only (model resolves references eagerly)",
    "deref_ingredient": "raw FFI only (Recipe.ingredients)",
    "deref_cookware": "raw FFI only (Recipe.cookware)",
    "deref_timer": "raw FFI only (Recipe.timers)",
    # Totalling
    "combine_ingredients": "cooklang.combine_ingredients()",
    "combine_ingredients_selected": "combine_ingredients(indices=...)",
    "use_common_names": "combine_ingredients(aisle=...)",
    # Aisle configuration
    "parse_aisle_config": "cooklang.parse_aisle_config()",
    # Shopping lists
    "parse_shopping_list": "cooklang.parse_shopping_list()",
    "write_shopping_list": "ShoppingList.to_text()",
    # Checked log
    "parse_shopping_checked": "cooklang.parse_checked_log()",
    "shopping_checked_set": "cooklang.checked_names()",
    "compact_shopping_checked": "cooklang.compact_checked_log()",
    "write_shopping_check_entry": "Checked.to_text() / Unchecked.to_text()",
}


def _exported_functions() -> set[str]:
    return {
        name
        for name, obj in vars(ffi).items()
        if inspect.isfunction(obj) and not name.startswith("_")
    }


def test_the_coverage_map_matches_upstream():
    """Fails when upstream adds or removes an exported function."""
    exported = _exported_functions()

    assert exported - set(_COVERAGE) == set(), "upstream added functions we do not cover"
    assert set(_COVERAGE) - exported == set(), "coverage map lists functions upstream dropped"


def test_object_methods_are_covered():
    """The two UniFFI objects expose methods rather than free functions."""
    assert {m for m in dir(ffi.CooklangRecipe) if not m.startswith("_")} == {
        "sections",
        "ingredients",
        "cookware",
        "timers",
    }
    assert {m for m in dir(ffi.AisleConf) if not m.startswith("_")} == {
        "categories",
        "category_for",
        "common_name_for",
    }


class TestDerefFunctions:
    """The four deref_* functions, which the Python model makes redundant."""

    def test_deref_ingredient_cookware_and_timer(self):
        raw = ffi.parse_recipe(RECIPE, 1.0)

        assert ffi.deref_ingredient(raw, 0).name == "onion"
        assert ffi.deref_cookware(raw, 0).name == "pan"
        assert ffi.deref_timer(raw, 0).amount.units == "minutes"

    def test_deref_component_resolves_each_item_kind(self):
        raw = ffi.parse_recipe(RECIPE, 1.0)
        step = raw.sections()[0].blocks[0][0]

        resolved = [ffi.deref_component(raw, item) for item in step.items]
        kinds = {type(c).__name__ for c in resolved}

        assert "Component.INGREDIENT_COMPONENT" in kinds
        assert "Component.COOKWARE_COMPONENT" in kinds
        assert "Component.TIMER_COMPONENT" in kinds

    def test_the_wrapper_gives_the_same_answer(self):
        """What deref_* returns is what the model already holds."""
        raw = ffi.parse_recipe(RECIPE, 1.0)
        recipe = cooklang.parse(RECIPE)

        assert ffi.deref_ingredient(raw, 0).name == recipe.ingredients[0].name
        assert ffi.deref_cookware(raw, 0).name == recipe.cookware[0].name


class TestValueHelpers:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("2", 2), ("0.5", 0.5), ("1/2", 0.5), ("1 1/2", 1.5), ("a pinch", "a pinch")],
    )
    def test_parse_value(self, text, expected):
        assert cooklang.parse_value(text) == expected

    def test_parse_value_range(self):
        value = cooklang.parse_value("1/2 - 3/4")

        assert value == cooklang.Range(start=0.5, end=0.75)

    def test_parse_value_rejects_non_strings(self):
        with pytest.raises(TypeError):
            cooklang.parse_value(3)

    @pytest.mark.parametrize(
        ("value", "expected"), [(0.5, "1/2"), (1.5, "1 1/2"), (2, "2"), ("some", "some")]
    )
    def test_format_value_restores_fractions(self, value, expected):
        assert cooklang.format_value(value) == expected

    def test_format_value_of_none_is_empty(self):
        assert cooklang.format_value(None) == ""

    def test_round_trip(self):
        assert cooklang.format_value(cooklang.parse_value("1 1/2")) == "1 1/2"


AISLE = """[produce]
onion|onions|brown onion
fennel

[dairy]
butter|unsalted butter
"""


class TestAisleConfig:
    def test_parse_aisle_config_reads_categories_in_order(self):
        config = cooklang.parse_aisle_config(AISLE)

        assert [c.name for c in config.categories] == ["produce", "dairy"]

    def test_ingredients_and_aliases(self):
        config = cooklang.parse_aisle_config(AISLE)
        produce = config.categories[0]

        assert produce.ingredients[0].name == "onion"
        assert produce.ingredients[0].aliases == ("onions", "brown onion")
        assert produce.ingredients[1].aliases == ()

    def test_category_for(self):
        config = cooklang.parse_aisle_config(AISLE)

        assert config.category_for("onion") == "produce"
        assert config.category_for("butter") == "dairy"
        assert config.category_for("saffron") is None

    def test_common_name_for_resolves_aliases_case_insensitively(self):
        config = cooklang.parse_aisle_config(AISLE)

        assert config.common_name_for("onions") == "onion"
        assert config.common_name_for("Brown Onion") == "onion"
        assert config.common_name_for("unsalted butter") == "butter"

    def test_common_name_for_passes_unknown_names_through(self):
        config = cooklang.parse_aisle_config(AISLE)

        assert config.common_name_for("saffron") == "saffron"

    def test_group_by_category_keeps_config_order_and_keeps_unknowns(self):
        config = cooklang.parse_aisle_config(AISLE)

        grouped = config.group_by_category(["butter", "saffron", "onion"])

        assert list(grouped) == ["produce", "dairy", None]
        assert grouped["produce"] == ("onion",)
        assert grouped[None] == ("saffron",)

    def test_rejects_non_strings(self):
        with pytest.raises(TypeError):
            cooklang.parse_aisle_config(None)


class TestCombineWithAisle:
    """`use_common_names`, reached through combine_ingredients(aisle=...)."""

    def test_aliases_are_merged_under_the_common_name(self):
        config = cooklang.parse_aisle_config(AISLE)
        recipe = cooklang.parse("Add @onions{1} and @brown onion{2}.")

        totals = cooklang.combine_ingredients(recipe.ingredients, aisle=config)

        assert set(totals) == {"onion"}
        assert [q.value for q in totals["onion"]] == [3]

    def test_without_an_aisle_they_stay_separate(self):
        recipe = cooklang.parse("Add @onions{1} and @brown onion{2}.")

        totals = cooklang.combine_ingredients(recipe.ingredients)

        assert set(totals) == {"onions", "brown onion"}

    def test_unknown_ingredients_survive_unchanged(self):
        config = cooklang.parse_aisle_config(AISLE)
        recipe = cooklang.parse("Add @saffron{1%pinch}.")

        totals = cooklang.combine_ingredients(recipe.ingredients, aisle=config)

        assert set(totals) == {"saffron"}


class TestCombineSelected:
    """`combine_ingredients_selected`, reached through the indices argument."""

    SOURCE = "Add @salt{1%tsp}, @pepper{2%tsp} and @cumin{3%tsp}."

    def test_indices_select_a_subset(self):
        recipe = cooklang.parse(self.SOURCE)

        totals = cooklang.combine_ingredients(recipe.ingredients, indices=[0, 2])

        assert set(totals) == {"salt", "cumin"}

    def test_empty_selection_is_empty(self):
        recipe = cooklang.parse(self.SOURCE)

        assert cooklang.combine_ingredients(recipe.ingredients, indices=[]) == {}

    def test_none_means_all(self):
        recipe = cooklang.parse(self.SOURCE)

        assert set(cooklang.combine_ingredients(recipe.ingredients)) == {
            "salt",
            "pepper",
            "cumin",
        }

    def test_out_of_range_index_is_an_index_error(self):
        recipe = cooklang.parse(self.SOURCE)

        with pytest.raises(IndexError):
            cooklang.combine_ingredients(recipe.ingredients, indices=[9])


SHOPPING_LIST = """./Breakfast/Pancakes{2}
salt{1%tsp}
./sauce
"""


class TestShoppingList:
    def test_parse_splits_recipes_from_ingredients(self):
        parsed = cooklang.parse_shopping_list(SHOPPING_LIST)

        assert [r.path for r in parsed.recipes] == ["Breakfast/Pancakes", "sauce"]
        assert [i.name for i in parsed.ingredients] == ["salt"]

    def test_multiplier_is_read(self):
        parsed = cooklang.parse_shopping_list(SHOPPING_LIST)

        assert parsed.recipes[0].multiplier == 2
        assert parsed.recipes[1].multiplier is None

    def test_len_and_iteration(self):
        parsed = cooklang.parse_shopping_list(SHOPPING_LIST)

        assert len(parsed) == 3
        assert len(list(parsed)) == 3

    def test_round_trips_through_to_text(self):
        parsed = cooklang.parse_shopping_list(SHOPPING_LIST)

        reparsed = cooklang.parse_shopping_list(parsed.to_text())

        assert reparsed == parsed

    def test_a_hand_built_list_serializes(self):
        built = cooklang.ShoppingList(
            items=(
                cooklang.RecipeItem(path="pasta", multiplier=2.0),
                cooklang.IngredientItem(name="salt", quantity="1%tsp"),
            )
        )

        assert built.to_text() == "./pasta{2}\nsalt{1%tsp}\n"

    def test_empty_list(self):
        assert cooklang.parse_shopping_list("").items == ()

    def test_rejects_non_strings(self):
        with pytest.raises(TypeError):
            cooklang.parse_shopping_list(None)


CHECKED_LOG = "+ salt\n+ pepper\n- salt\n+ cumin\n"


class TestCheckedLog:
    def test_parse_preserves_order_and_kind(self):
        entries = cooklang.parse_checked_log(CHECKED_LOG)

        assert [e.name for e in entries] == ["salt", "pepper", "salt", "cumin"]
        assert [e.checked for e in entries] == [True, True, False, True]

    def test_checked_names_replays_the_log(self):
        entries = cooklang.parse_checked_log(CHECKED_LOG)

        assert cooklang.checked_names(entries) == ("cumin", "pepper")

    def test_later_entries_win(self):
        entries = cooklang.parse_checked_log("+ salt\n- salt\n+ salt\n")

        assert cooklang.checked_names(entries) == ("salt",)

    def test_entry_to_text(self):
        assert cooklang.Checked(name="salt").to_text().strip() == "+ salt"
        assert cooklang.Unchecked(name="salt").to_text().strip() == "- salt"

    def test_compact_drops_stale_entries(self):
        entries = cooklang.parse_checked_log(CHECKED_LOG)

        compacted = cooklang.compact_checked_log(entries, ["pepper", "cumin"])

        assert {e.name for e in compacted} <= {"pepper", "cumin"}

    def test_compact_collapses_repeats(self):
        entries = cooklang.parse_checked_log("+ salt\n- salt\n+ salt\n")

        compacted = cooklang.compact_checked_log(entries, ["salt"])

        assert [e.name for e in compacted] == ["salt"]
        assert compacted[0].checked is True

    def test_rejects_non_strings(self):
        with pytest.raises(TypeError):
            cooklang.parse_checked_log(None)


class TestStructuredMetadata:
    def test_author_with_name_and_url(self):
        recipe = cooklang.parse(
            "---\nauthor: Jane Doe <https://example.com>\n---\n\nStir.\n"
        )

        assert recipe.author.name == "Jane Doe"
        assert recipe.author.url == "https://example.com"

    def test_source(self):
        recipe = cooklang.parse("---\nsource: A Cookbook\n---\n\nStir.\n")

        assert recipe.source.name == "A Cookbook"

    def test_absent_metadata_is_none(self):
        recipe = cooklang.parse("Stir.")

        assert recipe.author is None
        assert recipe.source is None
        assert recipe.time is None

    def test_total_time(self):
        recipe = cooklang.parse("---\ntime: 45\n---\n\nStir.\n")

        assert recipe.time.total == 45

    def test_composed_time_gets_a_total(self):
        recipe = cooklang.parse(
            "---\nprep time: 10\ncook time: 35\n---\n\nStir.\n"
        )

        assert (recipe.time.prep, recipe.time.cook, recipe.time.total) == (10, 35, 45)


class TestApplyCommonNames:
    """`AisleConfig.apply_common_names`, for totals you already computed."""

    def test_merges_aliases_in_an_existing_total(self):
        config = cooklang.parse_aisle_config(AISLE)
        recipe = cooklang.parse("Add @onions{1} and @onion{2}.")
        totals = cooklang.combine_ingredients(recipe.ingredients)

        assert set(totals) == {"onion", "onions"}

        merged = config.apply_common_names(totals)

        assert set(merged) == {"onion"}
        assert [q.value for q in merged["onion"]] == [3]

    def test_matches_combining_with_the_aisle_up_front(self):
        config = cooklang.parse_aisle_config(AISLE)
        recipe = cooklang.parse("Add @onions{1} and @brown onion{2}.")

        up_front = cooklang.combine_ingredients(recipe.ingredients, aisle=config)
        after = config.apply_common_names(
            cooklang.combine_ingredients(recipe.ingredients)
        )

        assert {k: [q.value for q in v] for k, v in up_front.items()} == {
            k: [q.value for q in v] for k, v in after.items()
        }

    def test_ingredients_without_amounts_survive(self):
        config = cooklang.parse_aisle_config(AISLE)
        totals = cooklang.combine_ingredients(
            cooklang.parse("Add @onions{} and @saffron.").ingredients
        )

        merged = config.apply_common_names(totals)

        assert set(merged) == {"onion", "saffron"}
