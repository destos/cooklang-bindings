# Python style guide for cooklang-bindings

This is the contract for code under `src/cooklang/`. It is written so that a
person or an LLM can check a change against it without reading the rest of the
codebase. Generated code under `src/cooklang/_generated/` is exempt: never edit
it, regenerate it.

When this guide and existing code disagree, the guide wins and the code is a
bug. When this guide is silent, follow PEP 8 and PEP 257.

## 1. What this package is

A thin Pythonic layer over UniFFI-generated bindings to cooklang-rs. It
contains no parser logic. Every public function either maps onto one upstream
function or lives in `cooklang.contrib`. Before adding anything, decide which
of those it is, because the answer decides where it goes:

| The code... | Lives in |
| --- | --- |
| wraps an upstream function or converts its output | `parser.py`, `values.py`, `aisle.py`, `shopping.py` |
| is a plain data type with no FFI object inside | `models.py` (recipes) or the module for its format |
| is an opinion about how an app should read a recipe, backed by no upstream function | `contrib.py` |
| patches the generated module to make it usable | `_ffi.py` only |

Nothing outside `_ffi.py` imports `_generated` directly. Everything else
imports `from ._ffi import ffi`.

## 2. Public surface

- Every module defines `__all__`. `cooklang/__init__.py` re-exports the public
  names and lists them in its own `__all__`, grouped by area with a comment.
- A name is public if and only if it is in `__all__`. Everything else is
  prefixed with `_`.
- Do not put dunder names in `__all__`.
- Never expose an FFI object through a public attribute or signature. If a
  class must hold one (like `AisleConfig`), the attribute is private and the
  public constructor does not take it. Provide a `parse_*` function or a
  `from_text` classmethod instead.
- `Any` does not appear in a public signature. Internal converters that take
  raw FFI objects may use `Any`, and should be private.

## 3. Data types

- Model types are `@dataclass(frozen=True, slots=True)`.
- A model holds only immutable Python values: `str`, `int`, `float`, `bool`,
  `None`, other frozen models, `tuple`, `frozenset`, or a `Mapping` that is
  itself read-only. No `list`, no `dict`, no FFI handles. This is what makes
  the promise "compares, hashes and pickles normally" true. If a field cannot
  meet this, either change the field or remove the promise from the docs.
- Sequences are `tuple[T, ...]` in fields and return types. Accept the
  broadest input that works: `Iterable[T]` when consumed once,
  `Sequence[T]` when indexed or measured.
- Unions that appear in more than one public annotation get a named, exported
  alias (`Item`, `Block`, `ShoppingItem`, `CheckEntry`).
- A boolean state is one class with a `bool` field, not two classes.
- Name the same concept the same way everywhere. Current vocabulary:

  | Concept | Name | Not |
  | --- | --- | --- |
  | multiply a recipe | `scale` | `multiplier`, `factor` |
  | parsed amount | `quantity: Quantity` | `amount` |
  | raw unparsed amount text | `quantity_text: str` | `quantity` |
  | unit of a quantity | `unit` | `units` |
  | ingredient annotation `(softened)` | `note` | `descriptor` |
  | heading | `name` | `title` (except `Recipe.title`, which is metadata) |
  | text of a step or note | `text` | `value`, `content` |

  Upstream's names are not binding here. This layer already renames
  `descriptor`, `units` and `title`; keep doing it when the Python word is
  clearer, and record the mapping in the converter's docstring.

## 4. Dunder methods

- `__str__` is the human display form: what you would print inline in prose.
  It never returns file syntax, never returns a bracketed placeholder, and
  returns `""` when there is nothing to show.
- Serialising back to a file format is a method named `to_text()`. It is the
  inverse of the matching `parse_*` function and raises that format's error.
- `__repr__` is the dataclass default unless the type holds a handle, in which
  case it is `<ClassName summary>`.
- Do not implement `__iter__`, `__len__` or `__getitem__` on model types.
  Iterate the named attribute (`recipe.steps`), which is explicit and
  type-checks cleanly. If a type genuinely is a sequence, implement all of
  `collections.abc.Sequence`, not a subset.
- Frozen dataclasses with an unhashable field need an explicit `__hash__`,
  or the field needs to change. Never leave `__hash__ = None` silently.

## 5. Functions

- Parsing entry points are module-level functions named `parse_<thing>` that
  take `text: str` first. Options are keyword-only (`*,`).
- Required arguments are positional-or-keyword. Optional behaviour switches
  are keyword-only with a default. Never add a positional `bool`.
- Validate at the boundary, in one shared helper, and raise `TypeError` for
  a wrong type. The reason is that the FFI layer produces unreadable errors
  for wrong types. Reject `bool` where a number is expected. Do not coerce
  silently: `scale="2"` is an error, not `2.0`.
- Return the most specific type you can name. `dict[str, tuple[Quantity, ...]]`
  not `dict[str, Any]`. If the result is set-shaped, return `frozenset`.
- Mutating input is forbidden. Functions return new values.
- Conversion helpers between FFI and model types are private, named
  `_<model>` for FFI to model (`_ingredient(raw)`) and `_to_ffi_<model>` for
  the reverse. Keep them next to the type they produce.
- A file-based convenience, if provided, is `parse_<thing>_file(path, *,
  encoding="utf-8", **same options)` and accepts `str | os.PathLike`.

## 6. Errors

- `CooklangError` (in `cooklang.errors`) is the base for every exception this
  package raises about its *input*. It subclasses `ValueError`, so every
  format-specific error (`ParseError`, `ShoppingListError`) is one too and
  existing `except ValueError` handlers keep working.
- A wrong argument *type* is a bug in the caller, not bad input, and raises a
  plain `TypeError` from the shared helper in `_validate.py`. It is
  deliberately not a `CooklangError`.
- Wrap every FFI exception at the boundary with `raise OurError(...) from
  exc`. A generated exception class must never escape a public function.
- An exception carries structured attributes when upstream gives structure
  (message, span, label), each `None` when unavailable, and `raw` holding the
  original text. The `str()` of the exception is readable without the raw.
- Exceptions are constructible from keyword arguments without a raw string,
  so tests and callers can build one.
- Forgiving-parser behaviour is not an error. If upstream turns bad input
  into text, so do we, and the docstring says so.

## 7. Typing

- `from __future__ import annotations` at the top of every module.
- PEP 604 unions (`str | None`), builtin generics (`tuple[str, ...]`).
- Import `Iterable`, `Sequence`, `Mapping`, `Iterator` from
  `collections.abc`, not `typing`.
- `TYPE_CHECKING` guards only for import cycles, and the guarded import gets
  a `# pragma: no cover`.
- The package ships `py.typed`. Any public name must type-check under
  strict mode with no `Any` leaking out.

## 8. Docstrings

- Google style, as configured for mkdocstrings. Sections in this order:
  summary line, explanation, `Args:`, `Returns:`, `Raises:`, `Example:`.
- The summary line says what the thing is, in one sentence, and is a noun
  phrase for classes and attributes, an imperative for functions.
- The explanation says *why* when the behaviour is surprising: why timers
  render as their duration, why `common_name_for` never returns `None`. Do
  not restate the signature.
- Attribute docstrings go on the line after the field, as a string literal.
- Examples are doctests and are run by `pytest --doctest-modules`. An example
  that would need `+ELLIPSIS` or `+SKIP` is not an example, it is prose.
- Cross-reference with `:func:`, `:class:`, `:attr:`, `:meth:` and the full
  dotted path.
- When a docstring and the README describe the same thing, they say the
  same thing. Grep for the term before changing either.

## 9. Tests

- One behaviour per test, named `test_<subject>_<expectation>` in plain
  English: `test_content_before_any_heading_is_an_unnamed_section`.
- A test docstring explains why the case exists when it is not obvious,
  especially for regressions and upstream quirks.
- Test the Python layer's promises, not upstream's parser. If a test would
  pass against the raw FFI, it belongs in `test_ffi_surface.py`.
- Every stated guarantee in a docstring or the README has a test:
  hashability, pickling, `__str__` output, exception attributes, the
  exception hierarchy.
- Breaking a public name or signature needs a `CHANGELOG.md` entry under
  "Changed" in the same commit.

## 10. Checklist for a change

Before opening a PR, confirm each line:

- [ ] New public names are in the module `__all__` and, if top-level, in
      `cooklang/__init__.py`.
- [ ] No `Any`, `list`, `dict` or FFI object in a public signature or model
      field.
- [ ] `__str__` is display text; serialisation is `to_text()`.
- [ ] Names follow the vocabulary table in section 3.
- [ ] Wrong-type input raises `TypeError` via the shared helper; nothing is
      silently coerced.
- [ ] Every exception raised about input subclasses `CooklangError`; wrong
      types raise `TypeError`.
- [ ] Docstring has `Args`/`Returns`/`Raises`, and the README agrees with it.
- [ ] A test covers the new promise.
- [ ] `CHANGELOG.md` updated if anything public changed.
