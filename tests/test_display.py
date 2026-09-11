"""`__str__` is display text and `to_text()` is file syntax, for every type.

Before 0.6.0, `str()` of a shopping-list item returned file syntax while
`str()` of a recipe component returned prose, so the same call meant two
different things depending on the type. The rule is now one: `str()` is what
you would print in a sentence, and `to_text()` is what you would write to disk.
"""

from __future__ import annotations

import pytest

import cooklang
from cooklang import CheckEntry, IngredientItem, RecipeItem


class TestShoppingItems:
    def test_ingredient_str_is_prose(self):
        assert str(IngredientItem("salt", quantity_text="1%tsp")) == "salt (1 tsp)"

    def test_ingredient_without_an_amount_is_just_its_name(self):
        assert str(IngredientItem("bread")) == "bread"

    def test_ingredient_to_text_is_its_file_line(self):
        assert IngredientItem("salt", quantity_text="1%tsp").to_text() == "salt{1%tsp}\n"

    def test_recipe_str_is_the_path_and_scale(self):
        assert str(RecipeItem("Breakfast/Pancakes", scale=2.0)) == "Breakfast/Pancakes ×2"

    def test_unscaled_recipe_str_is_just_the_path(self):
        assert str(RecipeItem("sauce")) == "sauce"

    def test_recipe_to_text_includes_its_children(self):
        item = RecipeItem("pasta", scale=2.0, children=(IngredientItem("salt"),))

        assert item.to_text() == "./pasta{2}\n  salt\n"

    def test_item_to_text_matches_the_list_writer(self):
        """An item alone serializes exactly as it does inside a list."""
        shopping = cooklang.parse_shopping_list("./a{2}\n  b{1%kg}\nc\n")

        assert "".join(i.to_text() for i in shopping.items) == shopping.to_text()


class TestCheckEntry:
    def test_one_type_holds_both_states(self):
        entries = cooklang.parse_checked_log("+ milk\n- milk\n")

        assert entries == (CheckEntry("milk", checked=True), CheckEntry("milk", checked=False))

    def test_checked_must_be_passed_by_keyword(self):
        with pytest.raises(TypeError):
            CheckEntry("milk", True)

    def test_str_is_the_name(self):
        assert str(CheckEntry("milk", checked=False)) == "milk"


class TestRecipe:
    def test_untitled_recipe_str_is_empty(self):
        """Every other `__str__` returns "" when there is nothing to show."""
        assert str(cooklang.parse("Bake.")) == ""


@pytest.mark.parametrize(
    "obj",
    [
        cooklang.parse("Bake.").sections[0],
        cooklang.parse_shopping_list("salt\n"),
    ],
    ids=["Section", "ShoppingList"],
)
def test_model_types_are_not_half_sequences(obj):
    """Iterate the named attribute instead; a partial protocol confuses type checkers."""
    assert not hasattr(obj, "__iter__")
    assert not hasattr(obj, "__len__")
