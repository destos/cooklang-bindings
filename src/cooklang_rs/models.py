"""Plain Python data types for a parsed Cooklang recipe.

These are ordinary frozen dataclasses with no FFI objects inside them, so they
are safe to hold onto, compare, pickle, and hand to a template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence

__all__ = [
    "Range",
    "Quantity",
    "Ingredient",
    "Cookware",
    "Timer",
    "Step",
    "Note",
    "Section",
    "Recipe",
]


@dataclass(frozen=True, slots=True)
class Range:
    """A quantity written as a range, e.g. ``@onion{1-2}``."""

    start: float
    end: float

    def __str__(self) -> str:
        return f"{_trim(self.start)}-{_trim(self.end)}"


def _trim(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


@dataclass(frozen=True, slots=True)
class Quantity:
    """An amount attached to an ingredient, cookware item or timer.

    ``value`` is an ``int`` for whole numbers, a ``float`` for fractional ones,
    a :class:`Range`, a ``str`` for free-text amounts (``@salt{a pinch}``), or
    ``None`` when the recipe gave no amount.

    ``text`` is upstream's own rendering, which restores fractions where they
    were written that way (``1/2`` rather than ``0.5``). Use it for display and
    ``value``/``unit`` for arithmetic.
    """

    value: int | float | str | Range | None
    unit: str | None
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Ingredient:
    """An ingredient occurrence, e.g. ``@unsalted butter{2%tbsp}(softened)``."""

    name: str
    quantity: Quantity | None = None
    note: str | None = None
    recipe_reference: str | None = None
    """Set when the ingredient refers to another recipe (``@./pasta/dough{}``)."""

    def __str__(self) -> str:
        return f"{self.name} ({self.quantity})" if self.quantity else self.name


@dataclass(frozen=True, slots=True)
class Cookware:
    """A piece of cookware, e.g. ``#frying pan{2}``."""

    name: str
    quantity: Quantity | None = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Timer:
    """A timer, e.g. ``~simmer{20%minutes}``. ``name`` is ``None`` if unnamed.

    Rendering prefers the duration over the name, because that is what reads
    correctly inline: "Boil for ~eggs{3%minutes}" should render as "Boil for
    3 minutes", not "Boil for eggs". The name is a label for the timer, so it
    is the fallback for a timer written without a duration.
    """

    name: str | None
    quantity: Quantity | None = None

    def __str__(self) -> str:
        if self.quantity is not None and self.quantity.text:
            return self.quantity.text
        return self.name or ""


@dataclass(frozen=True, slots=True)
class Step:
    """A single cooking instruction."""

    number: int
    """1-based position among the recipe's steps, counting across sections."""
    text: str
    """The step with its components rendered inline, free of Cooklang markup."""
    ingredients: tuple[Ingredient, ...] = ()
    cookware: tuple[Cookware, ...] = ()
    timers: tuple[Timer, ...] = ()

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Note:
    """A ``> note`` line. Deliberately not a step."""

    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Section:
    """A ``== Section ==`` heading and the blocks beneath it.

    ``name`` is ``None`` for content that appears before any heading, which is
    the only section present in a recipe that uses no headings at all.
    """

    name: str | None
    blocks: tuple[Step | Note, ...] = ()

    @property
    def steps(self) -> tuple[Step, ...]:
        return tuple(b for b in self.blocks if isinstance(b, Step))

    @property
    def notes(self) -> tuple[Note, ...]:
        return tuple(b for b in self.blocks if isinstance(b, Note))

    def __iter__(self) -> Iterator[Step | Note]:
        return iter(self.blocks)

    def __str__(self) -> str:
        return self.name or ""


@dataclass(frozen=True, slots=True)
class Recipe:
    """A parsed recipe.

    Build one with :func:`cooklang_rs.parse`.
    """

    metadata: Mapping[str, Any] = field(default_factory=dict)
    """All recipe metadata, from YAML front matter or ``>> key: value`` lines.

    Standard keys use Python-friendly names (``prep_time``, not ``prep time``);
    custom keys appear exactly as written. ``tags`` is a list and ``servings``
    is an ``int`` where the recipe gave a number; every other value is a string.
    """
    sections: tuple[Section, ...] = ()
    ingredients: tuple[Ingredient, ...] = ()
    """Every ingredient occurrence, in document order, including repeats."""
    cookware: tuple[Cookware, ...] = ()
    timers: tuple[Timer, ...] = ()

    @property
    def title(self) -> str | None:
        value = self.metadata.get("title")
        return value if isinstance(value, str) else None

    @property
    def description(self) -> str | None:
        value = self.metadata.get("description")
        return value if isinstance(value, str) else None

    @property
    def servings(self) -> int | str | None:
        value = self.metadata.get("servings")
        return value if isinstance(value, (int, str)) else None

    @property
    def tags(self) -> tuple[str, ...]:
        value = self.metadata.get("tags")
        return tuple(value) if isinstance(value, Sequence) and not isinstance(value, str) else ()

    @property
    def steps(self) -> tuple[Step, ...]:
        """Every step in the recipe, in order, across all sections."""
        return tuple(b for s in self.sections for b in s.blocks if isinstance(b, Step))

    @property
    def notes(self) -> tuple[Note, ...]:
        """Every note in the recipe, in order, across all sections."""
        return tuple(b for s in self.sections for b in s.blocks if isinstance(b, Note))

    @property
    def method(self) -> tuple[str, ...]:
        """Just the step text, for when you only want the method as prose."""
        return tuple(step.text for step in self.steps)

    def __str__(self) -> str:
        return self.title or "<untitled recipe>"
