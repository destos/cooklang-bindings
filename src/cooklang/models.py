"""Plain Python data types for a parsed Cooklang recipe.

These are ordinary frozen dataclasses with no FFI objects inside them, so they
are safe to hold onto, compare, pickle, and hand to a template.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field

__all__ = [
    "Range",
    "NameAndUrl",
    "RecipeTime",
    "Quantity",
    "Ingredient",
    "Cookware",
    "Timer",
    "Step",
    "TextItem",
    "IngredientRef",
    "CookwareRef",
    "TimerRef",
    "Item",
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
class NameAndUrl:
    """A metadata credit, used for ``author`` and ``source``.

    Cooklang lets either part stand alone, so both are optional: a recipe may
    credit a name, a bare URL, or a name linked to one.
    """

    name: str | None = None
    url: str | None = None

    def __str__(self) -> str:
        return self.name or self.url or ""


@dataclass(frozen=True, slots=True)
class RecipeTime:
    """Recipe timing, in minutes.

    Cooklang accepts either a single total (``time: 45``) or a prep/cook split
    (``prep time:`` and ``cook time:``). Both shapes land here: ``total`` is
    the number the recipe gave, or the sum of the split when it gave one.
    """

    total: int | None = None
    prep: int | None = None
    cook: int | None = None

    def __str__(self) -> str:
        return f"{self.total} minutes" if self.total is not None else ""


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
class TextItem:
    """Literal text in a step, between the components."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class IngredientRef:
    """An ingredient at its point of use in a step.

    ``index`` is the position in :attr:`Recipe.ingredients`, and is what links
    this occurrence to the recipe's ingredient list. ``ingredient`` is that
    entry itself -- the very same object, not a copy, so the two cannot drift.
    """

    index: int
    ingredient: Ingredient

    def __str__(self) -> str:
        return self.ingredient.name


@dataclass(frozen=True, slots=True)
class CookwareRef:
    """A piece of cookware at its point of use in a step."""

    index: int
    cookware: Cookware

    def __str__(self) -> str:
        return self.cookware.name


@dataclass(frozen=True, slots=True)
class TimerRef:
    """A timer at its point of use in a step."""

    index: int
    timer: Timer

    def __str__(self) -> str:
        return str(self.timer)


Item = TextItem | IngredientRef | CookwareRef | TimerRef
"""One piece of a step: literal text, or a component at its position."""


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
    items: tuple[Item, ...] = ()
    """The step in order, as literal text and components at their positions.

    Use this to mark up components where they occur -- "whisk the **flour
    300 g**" -- rather than rendering plain prose with a summary above it.
    ``"".join(str(item) for item in step.items)`` reproduces :attr:`text`.

    The component tuples above answer "what does this step use"; this answers
    "where". An ingredient used twice at different amounts appears twice here,
    each with its own index, which is what tells the two occurrences apart.
    """

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

    def __str__(self) -> str:
        return self.name or ""


class _Metadata(Mapping[str, "str | int | tuple[str, ...]"]):
    """A read-only, hashable, picklable mapping for :attr:`Recipe.metadata`.

    ``types.MappingProxyType`` would be read-only but can be neither hashed nor
    pickled, and either failure would break the promise the model types make.
    Lists are stored as tuples so every value is hashable.
    """

    __slots__ = ("_data",)

    def __init__(
        self, data: Mapping[str, object] | Iterable[tuple[str, object]] = ()
    ) -> None:
        items = data.items() if isinstance(data, Mapping) else data
        self._data: dict[str, str | int | tuple[str, ...]] = {
            key: tuple(value) if isinstance(value, list) else value  # type: ignore[misc]
            for key, value in items
        }

    def __getitem__(self, key: str) -> str | int | tuple[str, ...]:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __hash__(self) -> int:
        return hash(frozenset(self._data.items()))

    def __repr__(self) -> str:
        return repr(self._data)

    def __reduce__(self) -> tuple[type[_Metadata], tuple[dict[str, object]]]:
        return (type(self), (self._data,))


@dataclass(frozen=True, slots=True)
class Recipe:
    """A parsed recipe.

    Build one with :func:`cooklang.parse`. Like every model type it compares,
    hashes and pickles by value.
    """

    metadata: Mapping[str, str | int | tuple[str, ...]] = field(default_factory=_Metadata)
    """All recipe metadata, from YAML front matter or ``>> key: value`` lines.

    Standard keys use Python-friendly names (``prep_time``, not ``prep time``);
    custom keys appear exactly as written. ``tags`` is a tuple and ``servings``
    is an ``int`` where the recipe gave a number; every other value is a string.

    The mapping is read-only, as the rest of the recipe is. ``dict(recipe.metadata)``
    gives a mutable copy.
    """
    sections: tuple[Section, ...] = ()
    ingredients: tuple[Ingredient, ...] = ()
    """Every ingredient occurrence, in document order, including repeats."""
    cookware: tuple[Cookware, ...] = ()
    timers: tuple[Timer, ...] = ()
    author: NameAndUrl | None = None
    """Structured form of the ``author`` metadata; the raw string stays in ``metadata``."""
    source: NameAndUrl | None = None
    """Structured form of the ``source`` metadata; the raw string stays in ``metadata``."""
    time: RecipeTime | None = None
    """Structured form of the recipe's timing, in minutes."""

    def __post_init__(self) -> None:
        # A caller building a Recipe by hand may pass a plain dict; freeze it
        # so the hash and immutability promises hold whoever constructed it.
        if not isinstance(self.metadata, _Metadata):
            object.__setattr__(self, "metadata", _Metadata(self.metadata))

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
        value = self.metadata.get("tags", ())
        return value if isinstance(value, tuple) else ()

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
        """The title, or ``""`` for an untitled recipe, like every other ``__str__``."""
        return self.title or ""
