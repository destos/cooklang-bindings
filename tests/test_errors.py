"""`CooklangError` and the diagnostics recovered from upstream's panic.

Upstream reports a parse failure by panicking, which formats its own diagnostic
into the panic message instead of returning it. These tests pin the recovery of
that diagnostic, so an upstream change to the format fails here rather than
silently degrading every error to an unparsed panic dump.
"""

from __future__ import annotations

import pytest

import cooklang

# Inputs upstream refuses outright. Almost nothing does; these are the two
# found so far.
EMPTY_COOKWARE = "Cook @beef{1%lb} in a #{} now."
EMPTY_TIMER = "Wait ~{}."


class TestItStillRaises:
    def test_it_is_a_value_error(self):
        with pytest.raises(cooklang.CooklangError) as caught:
            cooklang.parse(EMPTY_COOKWARE)

        assert isinstance(caught.value, ValueError)

    @pytest.mark.parametrize("source", [EMPTY_COOKWARE, EMPTY_TIMER])
    def test_both_known_refusals(self, source):
        with pytest.raises(cooklang.CooklangError):
            cooklang.parse(source)

    def test_forgiving_input_still_does_not_raise(self):
        """Only an outright refusal raises; malformed markup parses."""
        assert cooklang.parse("@unclosed{1%g").ingredients[0].name == "unclosed"
        assert cooklang.parse("---\nnot: [valid\n---\n\nStep.\n").steps[0].text == "Step."


class TestRecoveredDiagnostics:
    def _error(self, source):
        with pytest.raises(cooklang.CooklangError) as caught:
            cooklang.parse(source)
        return caught.value

    def test_message_is_upstreams_own_wording(self):
        assert self._error(EMPTY_COOKWARE).message == "Invalid cookware name: is empty"

    def test_severity_and_stage(self):
        error = self._error(EMPTY_COOKWARE)

        assert error.severity == "Error"
        assert error.stage == "Parse"

    def test_label_describes_the_position(self):
        assert self._error(EMPTY_COOKWARE).label == "add a name here"

    def test_span_indexes_into_the_source(self):
        """The span is what lets an editor underline the problem."""
        error = self._error(EMPTY_COOKWARE)
        start, end = error.span

        assert EMPTY_COOKWARE[start : end + 1] == "{"

    def test_span_can_cover_a_range(self):
        error = self._error(EMPTY_TIMER)

        assert error.span == (6, 8)
        assert EMPTY_TIMER[6:8] == "{}"  # the empty braces upstream objects to

    def test_raw_keeps_the_original_panic_text(self):
        error = self._error(EMPTY_COOKWARE)

        assert "SourceReport" in error.raw
        assert "unwrap()" in error.raw

    def test_str_is_readable_rather_than_a_panic_dump(self):
        error = self._error(EMPTY_COOKWARE)

        assert str(error) == "Invalid cookware name: is empty (add a name here) at 23"
        assert "unwrap()" not in str(error)

    def test_str_still_contains_the_problem_for_a_naive_caller(self):
        """Anyone matching on the message keeps working."""
        with pytest.raises(cooklang.CooklangError, match="Invalid timer"):
            cooklang.parse(EMPTY_TIMER)

    def test_unrecognised_text_degrades_to_raw(self):
        """If upstream changes the format, keep the text rather than lying."""
        error = cooklang.CooklangError("something entirely unexpected")

        assert error.message is None
        assert error.span is None
        assert error.raw == "something entirely unexpected"
        assert str(error) == "something entirely unexpected"


def test_reporting_an_error_against_the_source():
    """The use case: point at the problem instead of showing a panic."""
    try:
        cooklang.parse(EMPTY_COOKWARE)
    except cooklang.CooklangError as error:
        start, _ = error.span
        caret = " " * start + "^"
        report = f"{error.message}\n{EMPTY_COOKWARE}\n{caret}"

    assert report.splitlines()[1:] == [
        "Cook @beef{1%lb} in a #{} now.",
        "                       ^",
    ]
