# Changelog

Notable changes to `cooklang-bindings`. The upstream parser it binds to is
pinned per release; see [NOTICE](NOTICE) for the relationship to cooklang-rs.

## 0.6.0 — unreleased

### Changed

- **Every error shares one base.** `CooklangError` is now the base class for
  everything the package raises about its input, and `parse()` raises the new
  `ParseError`, which carries the same `message`, `span` and other attributes
  `CooklangError` used to. `ShoppingListError` derives from `CooklangError`
  too. `except cooklang.CooklangError` and `except ValueError` both still catch
  a failed parse. `ParseError` can be built from keyword arguments,
  `ParseError("bad", span=(3, 5))`, with `raw` optional.
- **`Recipe` hashes, as the README always said.** `Recipe.metadata` is now a
  read-only mapping and `metadata["tags"]` is a tuple rather than a list, so a
  recipe hashes and pickles by value. `dict(recipe.metadata)` gives a mutable
  copy.
- **Wrong types fail the same way everywhere.** Every entry point raises
  `TypeError: <argument> must be <type>, not <type>`. `parse(scale="2")` and
  `scale=True` are now errors rather than being read as numbers.
  `format_value(True)` and `format_value(b"x")` raise rather than rendering
  `"True"` and `"b'x'"`. `combine_ingredients(indices=...)` accepts only ints.
- **`str()` is display text; `to_text()` is file syntax, for every type.**
  `str(IngredientItem)` is now `salt (1 tsp)` and `str(RecipeItem)` is
  `Breakfast/Pancakes ×2`; each gains a `to_text()` giving its file line, as
  `str()` used to. `str()` of an untitled `Recipe` is `""` rather than
  `<untitled recipe>`.
- **Shopping-list fields renamed to this package's vocabulary.**
  `IngredientItem.quantity` is now `quantity_text`, since it is raw text and
  `Ingredient.quantity` is a parsed `Quantity`. `RecipeItem.multiplier` is now
  `scale`, matching `parse(scale=...)`.
- **`Checked` and `Unchecked` are one class.** Use
  `CheckEntry(name, checked=True)`; the two old classes are gone, and
  `CheckEntry` is no longer a type alias. `checked` is keyword-only.
- **No half-implemented container protocols.** `Section` no longer iterates
  and `ShoppingList` no longer iterates or has a length; use `section.blocks`
  and `shopping.items`. A type with `__len__` but no `__getitem__` misleads
  type checkers, and `reversed()` failed on it.
- **`AisleConfig` is built from text.** `AisleConfig(text)` and the new
  `AisleConfig.from_text(text)` both parse; the constructor used to take a
  private FFI object. `parse_aisle_config` is unchanged.
- **`category_for` matches the way `common_name_for` does.** Upstream's lookup
  is exact-match, so `category_for("Onions")` was `None` while
  `common_name_for("Onions")` was `"onion"`, and `group_by_category` filed the
  name under "other". It now falls back to the common name.
- **`__version__` is no longer in `__all__`.** It is still importable by name.

### Fixed

- **`AisleConfig` pickles safely.** It used to pickle its native pointer,
  which dangles in another process; it now re-parses its source text. Two
  configs with the same categories now compare equal and hash alike.

### Added

- `ShoppingItem` and `Block`, exported aliases for `RecipeItem |
  IngredientItem` and `Step | Note`.
- `RecipeTime.total_duration`, `prep_duration` and `cook_duration`, the
  minute fields as `timedelta`, so recipe time adds to
  `contrib.timer_duration` without unit conversion.
- `combine_ingredients(indices=...)` accepts any iterable of ints, and
  `apply_common_names` has a precise signature instead of `Any`.

## 0.5.0 — 2026-09-11

### Parse errors carry upstream's diagnostic

`CooklangError` now exposes `message`, `severity`, `stage`, `span` and `label`
recovered from the parser's own report, plus `raw` for the original text.
`span` is a pair of byte offsets into the input you passed, so a caller can
underline the offending characters rather than reporting a bare failure.

`str(error)` is now a readable summary — `Invalid cookware name: is empty (add a
name here) at 23` — instead of a Rust panic dump. Code matching on the message
keeps working. Fields are `None` rather than guessed when they cannot be read.

### A Rust panic on stderr is expected on a refused parse, and is not a crash

Upstream reports a refused parse by **panicking** rather than returning an
error, and Rust writes to stderr before the error reaches Python. So a bad
recipe prints something like:

```text
thread '<unnamed>' panicked at bindings/src/lib.rs:25:70:
called `Result::unwrap()` on an `Err` value: SourceReport { ...
```

**This is not a process death.** The exception is raised and catchable, and a
batch job that logs this for one recipe finishes the rest. It cannot be
suppressed from Python — the output happens inside Rust, and intercepting it
would mean redirecting the process's stderr around every parse, which would
swallow logging this library was never asked to touch. Fixing it needs an
upstream change; see `UPSTREAM_ISSUES.md`.

Two inputs are known to trigger it: `#{}` (cookware with no name) and `~{}` (a
timer with neither duration nor name).

## 0.4.0

- `Step.items` — the step as an ordered sequence of `TextItem` and component
  references, for marking components at their point of use rather than
  summarising them above the prose. Each reference carries an `index` into the
  recipe's component list *and* the resolved object, which is the same instance
  the recipe holds. Purely additive: `text` is unchanged.
- `contrib.timer_duration` — a timer's number and free-text unit interpreted as
  a `timedelta`, since `min`, `mins` and `Minutes` are unrelated strings to the
  parser. Returns `None` rather than guessing for a text duration, a range, an
  unknown unit, or a missing unit.

## 0.3.0

- `cooklang.contrib`, for helpers with no upstream counterpart — named after
  `django.contrib` so opinionated extras are not mistaken for parser semantics.
  Adds `unquantified_mentions`, which counts the mentions
  `combine_ingredients` leaves out, and `is_declaration_only`.
- **Fixed:** `Quantity.text` from `combine_ingredients` omitted the unit,
  giving `'5'` where a parsed quantity gave `'5 tsp'`. Totals now carry their
  unit, so `text` means one thing wherever it came from.

## 0.2.1

- **Fixed:** the macOS wheel was tagged `macosx_11_0_universal2` while
  containing an arm64-only library, so pip on an Intel Mac installed it and
  then failed at import. Wheels are now tagged by the architecture actually
  present.

## 0.2.0

First published release. Wraps the whole `cooklang-bindings` UniFFI surface:
parsing, metadata, ingredient totalling, aisle configuration, shopping lists
and the checked log.

Wheels for manylinux x86_64, manylinux aarch64 and macOS arm64. They carry no
Python ABI tag — UniFFI's output uses `ctypes`, not the CPython C API — so one
wheel per platform serves Python 3.10 through 3.14 and every later release.
