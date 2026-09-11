"""Promises the README and docstrings make about the Python layer.

Every stated guarantee gets a test here: that the model types hash and pickle,
that every error the package raises shares one base, and that a wrong argument
type fails with the same readable TypeError at every entry point.
"""

from __future__ import annotations

import pickle
from decimal import Decimal
from fractions import Fraction

import pytest

import cooklang

SOURCE = (
    "---\ntitle: Pie\ntags: [sweet, baked]\nservings: 4\n---\n\n"
    "Bake @apples{3} in a #dish{} for ~{40%minutes}.\n\n> Serve warm.\n"
)


class TestRecipeIsAValue:
    def test_recipe_is_hashable(self):
        assert hash(cooklang.parse(SOURCE)) == hash(cooklang.parse(SOURCE))

    def test_recipe_pickles_to_an_equal_recipe(self):
        recipe = cooklang.parse(SOURCE)

        assert pickle.loads(pickle.dumps(recipe)) == recipe

    def test_metadata_is_read_only(self):
        recipe = cooklang.parse(SOURCE)

        with pytest.raises(TypeError):
            recipe.metadata["title"] = "Tart"

    def test_tags_are_a_tuple_in_the_metadata_too(self):
        assert cooklang.parse(SOURCE).metadata["tags"] == ("sweet", "baked")

    def test_metadata_compares_equal_to_a_plain_dict(self):
        metadata = cooklang.parse(SOURCE).metadata

        assert metadata == {"title": "Pie", "tags": ("sweet", "baked"), "servings": 4}

    def test_a_hand_built_recipe_is_frozen_too(self):
        """A caller passing a dict must not get an unhashable Recipe back."""
        recipe = cooklang.Recipe(metadata={"tags": ["a", "b"]})

        assert recipe.metadata["tags"] == ("a", "b")
        assert hash(recipe) == hash(cooklang.Recipe(metadata={"tags": ("a", "b")}))


class TestExceptionHierarchy:
    @pytest.mark.parametrize("error", [cooklang.ParseError, cooklang.ShoppingListError])
    def test_every_error_derives_from_cooklang_error(self, error):
        assert issubclass(error, cooklang.CooklangError)

    @pytest.mark.parametrize("error", [cooklang.ParseError, cooklang.ShoppingListError])
    def test_every_error_is_still_a_value_error(self, error):
        """Handlers written as `except ValueError` before the base existed keep working."""
        assert issubclass(error, ValueError)

    def test_parse_raises_a_parse_error(self):
        with pytest.raises(cooklang.ParseError):
            cooklang.parse("Wait ~{}.")

    def test_one_handler_catches_both_formats(self):
        for bad in (lambda: cooklang.parse("Wait ~{}."),
                    lambda: cooklang.parse_shopping_list("./a\n   bad\n")):
            with pytest.raises(cooklang.CooklangError):
                bad()

    def test_a_parse_error_can_be_built_without_a_panic_string(self):
        error = cooklang.ParseError("Invalid thing", span=(3, 5), label="here")

        assert error.raw is None
        assert str(error) == "Invalid thing (here) at 3..5"

    def test_a_parse_error_pickles_with_its_attributes(self):
        error = cooklang.ParseError("Invalid thing", span=(3, 5))

        copy = pickle.loads(pickle.dumps(error))

        assert (copy.message, copy.span, str(copy)) == ("Invalid thing", (3, 5), str(error))


_CONFIG = cooklang.parse_aisle_config("[produce]\nonion\n")
_INGREDIENTS = cooklang.parse("@salt{1%tsp}").ingredients


class TestWrongTypesRaiseTypeError:
    @pytest.mark.parametrize(
        "call",
        [
            pytest.param(lambda: cooklang.parse(b"@salt"), id="parse text"),
            pytest.param(lambda: cooklang.parse("x", scale="2"), id="parse scale str"),
            pytest.param(lambda: cooklang.parse("x", scale=True), id="parse scale bool"),
            pytest.param(lambda: cooklang.parse_value(None), id="parse_value"),
            pytest.param(lambda: cooklang.format_value(b"x"), id="format_value bytes"),
            pytest.param(lambda: cooklang.format_value(True), id="format_value bool"),
            pytest.param(lambda: cooklang.parse_aisle_config(1), id="parse_aisle_config"),
            pytest.param(lambda: cooklang.parse_shopping_list(b""), id="parse_shopping_list"),
            pytest.param(lambda: cooklang.parse_checked_log(None), id="parse_checked_log"),
            pytest.param(lambda: _CONFIG.category_for(None), id="category_for"),
            pytest.param(lambda: _CONFIG.common_name_for(1), id="common_name_for"),
            pytest.param(
                lambda: cooklang.combine_ingredients(_INGREDIENTS, indices=["0"]),
                id="indices str",
            ),
            pytest.param(
                lambda: cooklang.combine_ingredients(_INGREDIENTS, indices=[True]),
                id="indices bool",
            ),
        ],
    )
    def test_wrong_type_is_a_type_error(self, call):
        with pytest.raises(TypeError):
            call()

    def test_the_message_names_the_argument(self):
        with pytest.raises(TypeError, match="^text must be str, not NoneType$"):
            cooklang.parse(None)

    @pytest.mark.parametrize("scale", [2, 2.0, Fraction(2), Decimal("2")])
    def test_any_real_number_is_a_scale(self, scale):
        assert cooklang.parse("@flour{100%g}", scale=scale).ingredients[0].quantity.value == 200
