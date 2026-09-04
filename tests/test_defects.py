"""One test per confirmed defect in the previously-used Python parser.

Each test uses the exact input that failed in production. Together they are the
acceptance criterion for replacing `destos/cooklang-py` with these bindings.
"""

from __future__ import annotations

import cooklang


class TestDefect1SectionGluedOntoStep:
    """`== Section ==` was glued onto the following step's text.

    "== Dough == Mix flour." parsed as a single step whose text carried the
    heading markup, corrupting the step rather than dropping it.
    """

    SOURCE = "== Dough ==\n\nMix flour.\n"

    def test_section_becomes_a_section(self):
        recipe = cooklang.parse(self.SOURCE)

        assert len(recipe.sections) == 1
        assert recipe.sections[0].name == "Dough"

    def test_step_text_is_clean(self):
        recipe = cooklang.parse(self.SOURCE)

        assert len(recipe.steps) == 1
        assert recipe.steps[0].text == "Mix flour."

    def test_no_heading_markup_survives_anywhere(self):
        recipe = cooklang.parse(self.SOURCE)

        for step in recipe.steps:
            assert "==" not in step.text
            assert "Dough" not in step.text

    def test_heading_on_the_line_above_still_separates(self):
        """The glued form — no blank line between heading and step."""
        recipe = cooklang.parse("== Dough ==\nMix flour.\n")

        assert recipe.sections[0].name == "Dough"
        assert recipe.steps[0].text == "Mix flour."

    def test_multiple_sections_keep_their_own_steps(self):
        recipe = cooklang.parse(
            "== Dough ==\n\nMix flour.\n\n== Filling ==\n\nChop @apple{2}.\n"
        )

        assert [s.name for s in recipe.sections] == ["Dough", "Filling"]
        assert [s.text for s in recipe.sections[0].steps] == ["Mix flour."]
        assert [s.text for s in recipe.sections[1].steps] == ["Chop apple."]


class TestDefect2NotesRenderedAsSteps:
    """`> note` lines rendered as numbered cooking steps, angle bracket included."""

    SOURCE = "Mix flour.\n\n> Rest the dough overnight.\n\nBake it.\n"

    def test_note_is_a_note(self):
        recipe = cooklang.parse(self.SOURCE)

        assert len(recipe.notes) == 1
        assert recipe.notes[0].text == "Rest the dough overnight."
        assert isinstance(recipe.notes[0], cooklang.Note)

    def test_note_is_not_a_step(self):
        recipe = cooklang.parse(self.SOURCE)

        assert len(recipe.steps) == 2
        assert [s.text for s in recipe.steps] == ["Mix flour.", "Bake it."]

    def test_angle_bracket_never_appears_in_output(self):
        recipe = cooklang.parse(self.SOURCE)

        for step in recipe.steps:
            assert ">" not in step.text
        for note in recipe.notes:
            assert not note.text.startswith(">")

    def test_step_numbering_skips_notes(self):
        """The note must not consume a step number."""
        recipe = cooklang.parse(self.SOURCE)

        assert [s.number for s in recipe.steps] == [1, 2]


class TestDefect3FrontMatterSilentlyDiscarded:
    """YAML front matter was dropped; only the older `>> key: value` form was read."""

    SOURCE = (
        "---\n"
        "title: Sourdough\n"
        "servings: 4\n"
        "tags:\n"
        "  - bread\n"
        "  - slow\n"
        "---\n"
        "\n"
        "Mix @flour{500%g}.\n"
    )

    def test_title_is_read(self):
        assert cooklang.parse(self.SOURCE).title == "Sourdough"

    def test_servings_is_read_as_a_number(self):
        recipe = cooklang.parse(self.SOURCE)

        assert recipe.servings == 4
        assert isinstance(recipe.servings, int)

    def test_tags_are_read(self):
        assert cooklang.parse(self.SOURCE).tags == ("bread", "slow")

    def test_front_matter_is_not_leaked_into_steps(self):
        recipe = cooklang.parse(self.SOURCE)

        assert [s.text for s in recipe.steps] == ["Mix flour."]

    def test_legacy_double_angle_form_still_works(self):
        """The older syntax must keep working, not be traded away for the new one."""
        recipe = cooklang.parse(">> title: Legacy\n>> servings: 2\n\nStir it.\n")

        assert recipe.title == "Legacy"
        assert recipe.servings == 2

    def test_custom_keys_reach_the_metadata_dict(self):
        recipe = cooklang.parse("---\ntitle: T\noven: fan\n---\n\nBake.\n")

        assert recipe.metadata["oven"] == "fan"
        assert recipe.metadata["title"] == "T"


class TestDefect4ConsecutiveIngredientLines:
    """A block of `@ingredient` lines rendered with the names run together.

    "lemongrassunsalted chicken stockfennel" — the parser dropped the line
    separator between components. Per the Cooklang spec, consecutive non-blank
    lines are one step (a paragraph), so the step count is correct; the defect
    was the missing separator between the ingredient names.
    """

    SOURCE = "@lemongrass{2%stalks}\n@unsalted chicken stock{1%L}\n@fennel{1}\n"

    def test_names_are_not_run_together(self):
        recipe = cooklang.parse(self.SOURCE)

        text = " ".join(step.text for step in recipe.steps)
        assert "lemongrassunsalted" not in text
        assert "stockfennel" not in text

    def test_each_ingredient_is_parsed_separately(self):
        recipe = cooklang.parse(self.SOURCE)

        assert [i.name for i in recipe.ingredients] == [
            "lemongrass",
            "unsalted chicken stock",
            "fennel",
        ]

    def test_quantities_survive(self):
        recipe = cooklang.parse(self.SOURCE)

        assert [(i.quantity.value, i.quantity.unit) for i in recipe.ingredients] == [
            (2, "stalks"),
            (1, "L"),
            (1, None),
        ]

    def test_rendered_text_separates_the_names(self):
        recipe = cooklang.parse(self.SOURCE)

        assert len(recipe.steps) == 1
        assert recipe.steps[0].text == "lemongrass unsalted chicken stock fennel"

    def test_blank_separated_lines_are_distinct_steps(self):
        """With blank lines they must split, proving the join is deliberate."""
        recipe = cooklang.parse(
            "@lemongrass{2%stalks}\n\n@unsalted chicken stock{1%L}\n\n@fennel{1}\n"
        )

        assert [s.text for s in recipe.steps] == [
            "lemongrass",
            "unsalted chicken stock",
            "fennel",
        ]
