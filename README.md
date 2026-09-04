# cooklang-rs (Python bindings)

Python bindings for [cooklang-rs][upstream], the official Rust implementation of
the [Cooklang][cooklang] recipe markup language.

**This is a binding to cooklang-rs, not a fork of it.** It contains no parser
logic. Everything under `src/cooklang_rs/_generated/` is produced by
[UniFFI][uniffi] from the interface upstream already maintains — the same
interface behind their Swift and Kotlin bindings — and the rest is a thin
Pythonic layer over that output.

```python
import cooklang_rs

recipe = cooklang_rs.parse(source)

recipe.title                      # "Sourdough"
recipe.servings                   # 4
recipe.metadata                   # {"title": "Sourdough", "servings": 4, ...}
recipe.method                     # ("Mix flour.", "Rest it for 12 hours.")
recipe.sections[0].name           # "Prep"
recipe.notes[0].text              # "Use a warm room."
recipe.ingredients[0].name        # "flour"
recipe.ingredients[0].quantity    # Quantity(value=500, unit="g", text="500 g")
```

## Install

```sh
pip install cooklang-rs
```

Wheels ship a prebuilt native library, so **installing needs no Rust toolchain.**
UniFFI's Python output drives the library through `ctypes` rather than the
CPython C API, so a wheel carries no Python ABI tag at all — one
`py3-none-<platform>` wheel per platform covers every supported interpreter.
That is a weaker constraint than `abi3`, which would still pin a minimum CPython.

### Supported platforms

| Platform | Wheel tag | Notes |
| --- | --- | --- |
| Linux x86_64 | `py3-none-manylinux_2_28_x86_64` | glibc 2.28+ (RHEL 8, Debian 10, Ubuntu 18.10+) |
| macOS arm64 | `py3-none-macosx_11_0_arm64` | Apple Silicon, macOS 11+ |

Python 3.10+; built and tested on 3.14. Other platforms must build from source.

## Upstream version

These bindings are pinned to **cooklang-rs v0.18.7** (crate `cooklang-bindings`
v0.18.7), included as a git submodule at `vendor/cooklang-rs` and used
unmodified. The pin is deliberate: reproducible builds matter more here than
tracking tip.

`cooklang_rs.UPSTREAM_VERSION` reports it at runtime, and CI fails if that
constant and the submodule tag ever disagree.

To move to a new upstream release, bump the submodule to the new tag, update
`UPSTREAM_VERSION`, and run the test suite — it is written against parser
behaviour, so it will catch a regression in the bump.

## Build from source

Requires a Rust toolchain, Python 3.10+, and git.

```sh
git clone --recurse-submodules <this repo>
cd cooklang-bindings

make generate      # build the cdylib, generate the Python bindings
make test          # run the suite against the working tree
make wheel         # build a wheel for this machine
```

`make wheel-linux` builds the manylinux x86_64 wheel in Docker, using the same
recipe as CI. On an Apple Silicon host it runs under emulation — correct, but
slow.

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

`Step` has `number`, `text` (markup-free, components rendered inline), and the
`ingredients` / `cookware` / `timers` it uses. `Section` has `name`, `blocks`,
and `steps` / `notes` views. `Quantity` has `value` (an `int` for whole numbers,
`float`, `str`, or `None`), `unit`, and `text` — upstream's own rendering, which
keeps fractions as `1/2` rather than `0.5`. Use `text` for display and
`value`/`unit` for arithmetic.

`combine_ingredients(ingredients)` totals repeats, letting upstream do the unit
arithmetic: two `@salt{2%tsp}` and `@salt{3%tsp}` mentions become one `5 tsp`.
Amounts in units that cannot be added stay separate under the same name.

All model types are frozen dataclasses holding no FFI objects, so they compare,
hash and pickle normally.

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
only Python trips over it. `cooklang_rs/_ffi.py` restores a consistent
`__hash__` on the generated class at import, matching upstream's own derive.
It is three lines, it touches no parser logic, and it is covered by
`TestCombineIngredients` so a future UniFFI release that fixes this upstream
will not break us silently.

**Ranges are an extension, not canonical.** Upstream's
`CooklangParser::canonical()` has range extensions off, so `@onion{1-2}` parses
as the text amount `"1-2"`, not a numeric range. The `Range` type is kept in the
model because the FFI can express it, and a test asserts the current behaviour
so an upstream change surfaces here rather than silently changing a consumer's
types.

## Licence

MIT, matching upstream. Distributed wheels contain a compiled copy of the
MIT-licensed cooklang-rs. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

[upstream]: https://github.com/cooklang/cooklang-rs
[cooklang]: https://cooklang.org
[uniffi]: https://mozilla.github.io/uniffi-rs/
