# cooklang-bindings (Python bindings for Cooklang)

Python bindings for [cooklang-rs][upstream], the official Rust implementation of
the [Cooklang][cooklang] recipe markup language.

**This is a binding to cooklang-rs, not a fork of it.** It contains no parser
logic. Everything under `src/cooklang/_generated/` is produced by
[UniFFI][uniffi] from the interface upstream already maintains — the same
interface behind their Swift and Kotlin bindings — and the rest is a thin
Pythonic layer over that output.

```python
import cooklang

recipe = cooklang.parse(source)

recipe.title                      # "Sourdough"
recipe.servings                   # 4
recipe.metadata                   # {"title": "Sourdough", "servings": 4, ...}
recipe.method                     # ("Mix flour.", "Rest it for 12 hours.")
recipe.sections[0].name           # "Prep"
recipe.notes[0].text              # "Use a warm room."
recipe.ingredients[0].name        # "flour"
recipe.ingredients[0].quantity    # Quantity(value=500, unit="g", text="500 g")
```

Full documentation, including guides and a complete API reference, is built
with `make docs` and configured to deploy to Read the Docs.

## Install

```sh
pip install cooklang-bindings
```

The distribution is `cooklang-bindings`, mirroring the name of the upstream
crate it packages; the import is `cooklang`.

Wheels ship a prebuilt native library, so **installing needs no Rust toolchain.**
UniFFI's Python output drives the library through `ctypes` rather than the
CPython C API, so a wheel carries no Python ABI tag at all — one
`py3-none-<platform>` wheel per platform covers every supported interpreter.
That is a weaker constraint than `abi3`, which would still pin a minimum CPython.

### Supported platforms

| Platform | Wheel tag | Notes |
| --- | --- | --- |
| Linux x86_64 | `py3-none-manylinux_2_28_x86_64` | glibc 2.28+ (RHEL 8, Debian 10, Ubuntu 18.10+) |
| Linux aarch64 | `py3-none-manylinux_2_28_aarch64` | glibc 2.28+; arm64 servers and Docker on Apple Silicon |
| macOS arm64 | `py3-none-macosx_11_0_arm64` | Apple Silicon, macOS 11+ |

Python 3.10+, with each wheel tested on 3.10 through 3.14 in CI. Since there is
no ABI tag the matrix is platform-only, so a new Python release needs no new
wheels. Other platforms — Windows, Intel macOS, musl-based Linux — have no
published wheel; `pip install` fails cleanly there rather than installing
something that cannot load.

Release notes are in [CHANGELOG.md](CHANGELOG.md).

## Upstream version

These bindings are pinned to **cooklang-rs v0.18.7** (crate `cooklang-bindings`
v0.18.7), included as a git submodule at `vendor/cooklang-rs` and used
unmodified. The pin is deliberate: reproducible builds matter more here than
tracking tip.

`cooklang.UPSTREAM_VERSION` reports it at runtime, and CI fails if that
constant and the submodule tag ever disagree.

To move to a new upstream release, bump the submodule to the new tag, update
`UPSTREAM_VERSION`, and run the test suite — it is written against parser
behaviour, so it will catch a regression in the bump.

## Build from source

Requires a Rust toolchain, Python 3.10+, and git.

```sh
git clone --recurse-submodules https://github.com/destos/cooklang-bindings.git
cd cooklang-bindings

make generate      # build the cdylib, generate the Python bindings
make test          # run the suite against the working tree
make wheel         # build a wheel for this machine
```

`make wheel-linux` builds the manylinux **x86_64** wheel in Docker, using the
same recipe as CI. On an Apple Silicon host it runs that under emulation —
correct, but slow.

There is no local target for the aarch64 wheel: CI builds it on a native arm64
runner, which is both faster and the artifact that actually ships. To test an
arm64 wheel, take it from the Wheels workflow run rather than building one
here.

Generated artifacts are **not** committed. `scripts/generate.py` recreates them,
and `make clean` removes them.

## API

`parse(text, *, scale=1.0) -> Recipe` is the entry point. `scale` multiplies
every quantity, so `scale=2.0` doubles the recipe.

`Recipe` exposes:

| Attribute | Type | |
| --- | --- | --- |
| `title`, `description` | `str \| None` | from metadata |
| `servings` | `int \| str \| None` | `int` when the recipe gave a number |
| `tags` | `tuple[str, ...]` | |
| `metadata` | `Mapping[str, Any]` | standard keys under Python names (`prep_time`), custom keys verbatim |
| `sections` | `tuple[Section, ...]` | one unnamed section for content before any heading |
| `steps`, `notes` | `tuple[Step, ...]` / `tuple[Note, ...]` | flattened across sections |
| `method` | `tuple[str, ...]` | just the step text |
| `ingredients`, `cookware`, `timers` | `tuple[...]` | every occurrence, in document order |

`Step` has `number`, `text` (markup-free, components rendered inline), the
`ingredients` / `cookware` / `timers` it uses, and `items` — the same step as a
sequence of `TextItem` and component references, for marking components where
they occur. Each reference carries an `index` into the recipe's component list
and the resolved object, which is how two mentions of one ingredient at
different amounts stay distinguishable. `Section` has `name`, `blocks`,
and `steps` / `notes` views. `Quantity` has `value` (an `int` for whole numbers,
`float`, `str`, or `None`), `unit`, and `text` — upstream's own rendering, which
keeps fractions as `1/2` rather than `0.5`. Use `text` for display and
`value`/`unit` for arithmetic.

Timers render inline as their duration rather than their name, because that is
what reads correctly in prose: `Boil for ~eggs{3%minutes}` becomes
`Boil for 3 minutes`. A timer written without a duration falls back to its name.

`combine_ingredients(ingredients, *, indices=None, aisle=None)` totals repeats,
letting upstream do the unit arithmetic: two `@salt{2%tsp}` and `@salt{3%tsp}`
mentions become one `5 tsp`. Amounts in units that cannot be added stay separate
under the same name. `indices` totals only a subset; `aisle` resolves names
through an aisle config first (see below).

All model types are frozen dataclasses holding no FFI objects, so they compare,
hash and pickle normally.

### Aisle configuration and common names

An aisle config groups ingredient names and their aliases into shopping
categories and gives each group one canonical name. That is what makes totals
across recipes trustworthy: without it, `@onions{1}` in one recipe and
`@brown onion{2}` in another are two different ingredients.

```python
config = cooklang.parse_aisle_config("""
[produce]
onion|onions|brown onion
fennel

[dairy]
butter|unsalted butter
""")

config.common_name_for("Brown Onion")   # "onion"  (case-insensitive, matches aliases)
config.category_for("butter")           # "dairy"
config.categories                       # in config-file order

recipe = cooklang.parse("Add @onions{1} and @brown onion{2}.")
cooklang.combine_ingredients(recipe.ingredients, aisle=config)
# {"onion": (Quantity(value=3, unit=None, text="3"),)}
```

`common_name_for` never returns `None` — an ingredient the config does not list
comes back unchanged, so it is safe to apply across a whole list.
`group_by_category(names)` buckets names for rendering, keeping config order and
collecting anything unlisted under `None` rather than dropping it.
`apply_common_names(totals)` does the same normalisation on totals you already
computed, merging quantities that collapse onto one name.

### Shopping lists and the checked log

Two more formats upstream parses. A `.shopping-list` holds recipe references
(`./Breakfast/Pancakes{2}`, the `./` marking a reference and the braces scaling
it) and free-hand ingredients (`salt{1%tsp}`), nested by two-space indents:

```python
shopping = cooklang.parse_shopping_list("./Breakfast/Pancakes{2}\nsalt{1%tsp}\n")
shopping.recipes[0].path        # "Breakfast/Pancakes"  (the ./ is stripped)
shopping.recipes[0].multiplier  # 2.0
shopping.ingredients[0].name    # "salt"
shopping.to_text()              # round-trips back to the file format
```

A `.shopping-checked` file is an append-only log of `+ name` / `- name` entries.
Replaying it gives the currently-checked set, with later entries winning:

```python
entries = cooklang.parse_checked_log("+ salt\n+ pepper\n- salt\n")
cooklang.checked_names(entries)                      # ("pepper",)
cooklang.compact_checked_log(entries, ["pepper"])    # drops stale entries
```

`compact_checked_log` wants the *aggregated* ingredient names the user actually
sees. A `.shopping-list` on disk holds only recipe references, so expand those
first — passing the raw list's own names would discard every entry as stale.

### Value helpers

`parse_value` reads a quantity the way upstream does, and `format_value` renders
one back. Useful when a user types an amount and you want Cooklang's reading of
it rather than `float()`'s:

```python
cooklang.parse_value("1 1/2")     # 1.5
cooklang.parse_value("1/2 - 3/4") # Range(start=0.5, end=0.75)
cooklang.parse_value("a pinch")   # "a pinch"  (text, not an error)
cooklang.format_value(0.5)        # "1/2"
```

### Upstream coverage

Every function upstream exports is reachable. `tests/test_ffi_surface.py` holds
a `_COVERAGE` map naming how each of the 28 is reached, and a test that fails if
upstream adds or removes one.

The four `deref_*` functions are the only ones with no Python wrapper: the model
resolves every reference eagerly at parse time, so a caller never holds an
unresolved reference to dereference. They are still exercised by the test suite,
and reachable on `cooklang._ffi.ffi` if you want them.

### What this project adds

Most of the API maps onto something cooklang-rs does. The parts that are ours,
with no upstream function behind them, live in `cooklang.contrib`:

```python
from cooklang import contrib

contrib.unquantified_mentions(recipe.ingredients)  # {"salt": 2}
contrib.is_declaration_only(step)                  # True for a bare @ingredient block
contrib.timer_duration(timer)                      # timedelta(minutes=45), or None
```

`unquantified_mentions` counts what `combine_ingredients` leaves out: a recipe
using `@salt{2%tsp}` and later a bare `@salt` totals to `2 tsp`, with the second
mention absent. That is right for a shopping list and wrong for anything that
needs to tell "2 tsp" from "2 tsp and more to taste". Upstream cannot answer
this — its grouping map collapses every unquantified mention into one entry —
so the count is computed here.

The namespace is named after `django.contrib`, for the same reason: these
encode opinions about how an application should read a recipe, and keeping them
separate stops them being mistaken for parser semantics. Some conveniences on
the model types are also ours rather than upstream's — see
`docs/contrib.md` for the full list.

### Errors

Cooklang is forgiving and nearly any text is a valid recipe: malformed metadata
and unclosed markup parse to whatever upstream decides they mean rather than
raising. `CooklangError` covers an outright parser failure; `parse` raises
`TypeError` for non-`str` input.

## Tests

`tests/test_defects.py` is the acceptance suite. It has one test class per
defect that drove this project, each using the exact input that failed against
the previous parser:

1. `== Section ==` glued onto the following step's text.
2. `> note` lines rendered as numbered steps, angle bracket included.
3. YAML front matter silently discarded.
4. Consecutive `@ingredient` lines rendered with their names run together.

Defects 1 and 2 are structurally impossible against this parser — upstream models
sections and notes as first-class types rather than reconstructing them from
text — but they are tested anyway, because the point is the guarantee, not the
mechanism.

`tests/test_acceptance.py` is the end-to-end check, and `tests/test_api.py`
covers the Python layer.

```sh
make test
```

## Syntax extensions

`cooklang-rs` parses a [superset][ext] of canonical Cooklang — aliases,
modifiers, range values and more. **These bindings parse canonical Cooklang
only, and there is no way to enable the extensions**, because upstream's UniFFI
binding hardcodes `CooklangParser::canonical()` and `parse_recipe` takes no
parser-mode argument. Swift and Kotlin share the constraint; it is not
Python-specific.

That matters more than a missing feature normally would, because Cooklang is
forgiving: unrecognised syntax is read as text rather than rejected, so extended
markup lands *inside* your data instead of raising.
`@onion|onions{1}` parses to an ingredient literally named `onion|onions`, and
`@&onion{1}` to one named `&onion`. `@flour{10 kg}` (no `%`) becomes the text
amount `"10 kg"` rather than 10 + `kg`. Canonical mode also uses an empty unit
converter, so `1%kg` and `500%g` are not converted before totalling.

Supporting the superset needs an upstream change — an exported parse function
taking extension flags. See `docs/extensions.md` for the detail, and
[UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md) for a ready-to-file issue draft.

## Known upstream gaps

**Records used as map keys are unhashable in Python.** UniFFI's Python backend
emits records as classes with a generated `__eq__` and no `__hash__`, which
Python turns into `__hash__ = None`. Upstream returns
`HashMap<GroupedQuantityKey, Value>`, so the generated converter tries to use an
unhashable object as a dict key and `combine_ingredients()` and
`use_common_names()` fail with:

```
TypeError: cannot use 'GroupedQuantityKey' as a dict key
```

This is a UniFFI Python-target gap, not an upstream bug: the Rust type derives
`Hash + Eq`, and Swift and Kotlin get structural hashing for free, which is why
only Python trips over it. `cooklang/_ffi.py` restores a consistent
`__hash__` on the generated class at import, matching upstream's own derive.
It is three lines, it touches no parser logic, and it is covered by
`TestCombineIngredients` so a future UniFFI release that fixes this upstream
will not break us silently. Draft in
[UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md); not yet filed.

**No way to enable syntax extensions.** `parse_recipe` hardcodes
`CooklangParser::canonical()`, so the whole extension set is unreachable and
extended syntax is silently absorbed into ingredient names. This is the one gap
worth raising upstream: it needs an exported parse function that accepts
extension flags. Draft in [UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md); not yet
filed.

**Ranges are an extension, not canonical.** Upstream's
`CooklangParser::canonical()` has range extensions off, so `@onion{1-2}` parses
as the text amount `"1-2"`, not a numeric range. The `Range` type is kept in the
model because the FFI can express it, and a test asserts the current behaviour
so an upstream change surfaces here rather than silently changing a consumer's
types.

## Licence

MIT, matching upstream. Distributed wheels contain a compiled copy of the
MIT-licensed cooklang-rs. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

[ext]: https://github.com/cooklang/cooklang-rs/blob/main/extensions.md
[upstream]: https://github.com/cooklang/cooklang-rs
[cooklang]: https://cooklang.org
[uniffi]: https://mozilla.github.io/uniffi-rs/
