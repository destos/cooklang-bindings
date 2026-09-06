"""Tests for `cooklang.contrib` — helpers this project adds itself.

These have no upstream counterpart, so unlike the rest of the suite they are
not pinned to cooklang-rs behaviour. Their semantics are ours to keep stable.
"""

from __future__ import annotations

import cooklang
from cooklang import contrib


def test_contrib_is_reachable_from_a_plain_import():
    """`import cooklang` is enough; no separate import needed to discover it."""
    assert cooklang.contrib is contrib
    assert "contrib" in cooklang.__all__


def test_contrib_members_are_not_in_the_top_level_namespace():
    """The boundary is the point: these must not look like parser semantics."""
    for name in contrib.__all__:
        assert not hasattr(cooklang, name), f"{name} leaked into the top level"


class TestUnquantifiedMentions:
    def test_counts_what_combine_ingredients_leaves_out(self):
        recipe = cooklang.parse("Add @salt{2%tsp}.\n\nSeason with @salt.\n")

        totals = cooklang.combine_ingredients(recipe.ingredients)
        extra = contrib.unquantified_mentions(recipe.ingredients)

        assert [(q.value, q.unit) for q in totals["salt"]] == [(2, "tsp")]
        assert extra == {"salt": 1}

    def test_counts_are_exact_not_merely_a_flag(self):
        """Upstream collapses these into one entry; counting here does not."""
        recipe = cooklang.parse(
            "Add @salt{2%tsp}.\n\nMore @salt.\n\nMore @salt.\n\nMore @salt.\n"
        )

        assert contrib.unquantified_mentions(recipe.ingredients) == {"salt": 3}

    def test_fully_quantified_recipe_gives_an_empty_mapping(self):
        recipe = cooklang.parse("Add @salt{2%tsp} and @pepper{1%tsp}.")

        assert contrib.unquantified_mentions(recipe.ingredients) == {}

    def test_several_ingredients(self):
        recipe = cooklang.parse("Add @salt and @pepper{1%tsp} and @cumin.")

        assert contrib.unquantified_mentions(recipe.ingredients) == {
            "salt": 1,
            "cumin": 1,
        }

    def test_an_empty_braces_amount_counts_as_unquantified(self):
        """`@salt{}` carries no amount, so it counts the same as a bare mention."""
        recipe = cooklang.parse("Add @salt{}.")

        assert contrib.unquantified_mentions(recipe.ingredients) == {"salt": 1}

    def test_accepts_any_sequence_of_ingredients(self):
        recipe = cooklang.parse("Add @salt and @pepper{1%tsp}.")

        assert contrib.unquantified_mentions(list(recipe.ingredients)) == {"salt": 1}
        assert contrib.unquantified_mentions([]) == {}


class TestIsDeclarationOnly:
    def test_a_bare_declaration_block(self):
        recipe = cooklang.parse("@olive oil{2%tbsp}\n@leeks{2}\n@potatoes{3}\n")

        assert [contrib.is_declaration_only(s) for s in recipe.steps] == [True]

    def test_prose_is_not_a_declaration(self):
        recipe = cooklang.parse("Fry the @leeks{2} in @olive oil{2%tbsp}.")

        assert [contrib.is_declaration_only(s) for s in recipe.steps] == [False]

    def test_a_step_with_no_ingredients_is_not_a_declaration(self):
        recipe = cooklang.parse("Preheat the oven.")

        assert contrib.is_declaration_only(recipe.steps[0]) is False

    def test_a_single_bare_ingredient_line_is_a_declaration(self):
        recipe = cooklang.parse("@salt{1%tsp}\n")

        assert contrib.is_declaration_only(recipe.steps[0]) is True

    def test_filtering_keeps_the_ingredients(self):
        """Dropping such steps loses nothing -- the ingredients survive."""
        recipe = cooklang.parse("@leeks{2}\n@potatoes{3}\n\nSimmer for ~{20%minutes}.")

        kept = [s for s in recipe.steps if not contrib.is_declaration_only(s)]

        assert [s.text for s in kept] == ["Simmer for 20 minutes."]
        assert [i.name for i in recipe.ingredients] == ["leeks", "potatoes"]
