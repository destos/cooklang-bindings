# cooklang-bindings

Python bindings for [cooklang-rs][upstream], the official Rust implementation
of the [Cooklang][cooklang] recipe markup language.

!!! info "This is a binding, not a fork"

    The package contains no parser logic. Everything under
    `cooklang/_generated/` is produced by [UniFFI][uniffi] from the interface
    upstream already maintains — the same interface behind their Swift and
    Kotlin bindings — and the rest is a thin Pythonic layer over that output.
    See [Relationship to cooklang-rs](upstream.md).

Install as `cooklang-bindings`, import as `cooklang`:

```sh
pip install cooklang-bindings
```

## In one screen

```pycon
>>> import cooklang
>>> recipe = cooklang.parse("""
... ---
... title: Test
... servings: 4
... ---
...
... == Prep ==
...
... Chop the @onion{1}.
...
... > A note that is not a step.
...
... Fry it in a #pan{} for ~{5%minutes}.
... """)
>>> recipe.title
'Test'
>>> recipe.servings
4
>>> recipe.method
('Chop the onion.', 'Fry it in a pan for 5 minutes.')
>>> recipe.sections[0].name
'Prep'
>>> recipe.notes[0].text
'A note that is not a step.'
>>> recipe.ingredients[0]
Ingredient(name='onion', quantity=Quantity(value=1, unit=None, text='1'), note=None, recipe_reference=None)
>>> recipe.cookware[0].name
'pan'
>>> str(recipe.timers[0])
'5 minutes'

```

<div class="grid cards" markdown>

-   __Install it__

    ---

    Wheels carry a prebuilt native library, so no Rust toolchain is needed.

    [:octicons-arrow-right-24: Installation](installation.md)

-   __Use it__

    ---

    Parse a recipe, walk its steps, total its ingredients.

    [:octicons-arrow-right-24: Getting started](getting-started.md)

-   __Look things up__

    ---

    Every exported name, with the type it returns.

    [:octicons-arrow-right-24: API reference](api/index.md)

-   __Build it__

    ---

    The native library is generated, not committed.

    [:octicons-arrow-right-24: Contributing](contributing.md)

</div>

## What is covered

The package wraps the whole of upstream's exported UniFFI surface — all 28
functions — not just the recipe parser.

| Area | Entry point | Guide |
| --- | --- | --- |
| Recipes | [`parse`][cooklang.parser.parse] | [Working with recipes](guide/recipes.md) |
| Totalling ingredients | [`combine_ingredients`][cooklang.parser.combine_ingredients] | [Working with recipes](guide/recipes.md#totalling-ingredients) |
| Aisle configuration and common names | [`parse_aisle_config`][cooklang.aisle.parse_aisle_config] | [Aisle configuration](guide/aisle.md) |
| Shopping lists | [`parse_shopping_list`][cooklang.shopping.parse_shopping_list] | [Shopping lists](guide/shopping.md) |
| The checked log | [`parse_checked_log`][cooklang.shopping.parse_checked_log] | [Shopping lists](guide/shopping.md#the-checked-log) |
| Quantity values | [`parse_value`][cooklang.values.parse_value], [`format_value`][cooklang.values.format_value] | [Quantity values](guide/values.md) |

## Canonical Cooklang only

`cooklang-rs` parses a [superset][ext] of canonical Cooklang. These bindings
parse the canonical spec only, and the extensions cannot be switched on —
upstream's UniFFI layer hardcodes the canonical parser. Because Cooklang reads
unrecognised syntax as text rather than rejecting it, extended markup ends up
inside your data rather than raising. If you ingest recipes you did not write,
read [Syntax extensions](extensions.md) first.

## Design notes

- **The model is plain data.** Every type in
  [`cooklang.models`](api/models.md) is a frozen dataclass with no FFI object
  inside it, so instances compare, hash, pickle and hand to a template without
  surprises.

    ```pycon
    >>> import cooklang
    >>> one = cooklang.parse("@salt{1%tsp}").ingredients[0]
    >>> two = cooklang.parse("@salt{1%tsp}").ingredients[0]
    >>> one == two
    True
    >>> len({one, two})
    1

    ```

- **Display text comes from upstream.** A `Quantity` carries both a `value`
  for arithmetic and a `text` that preserves how the recipe wrote it — `1/2`
  stays `1/2` rather than becoming `0.5`.

    ```pycon
    >>> quantity = cooklang.parse("@butter{1/2%cup}").ingredients[0].quantity
    >>> quantity.value
    0.5
    >>> quantity.text
    '1/2 cup'

    ```

- **Sections and notes are first class.** They are types upstream models
  directly, not something reconstructed from rendered text.

    ```pycon
    >>> recipe = cooklang.parse("One.\n\n> A note.\n\nTwo.\n")
    >>> [type(block).__name__ for block in recipe.sections[0].blocks]
    ['Step', 'Note', 'Step']

    ```

## Licence

MIT, matching upstream. Distributed wheels contain a compiled copy of the
MIT-licensed cooklang-rs. See [Relationship to cooklang-rs](upstream.md).

[ext]: https://github.com/cooklang/cooklang-rs/blob/main/extensions.md
[upstream]: https://github.com/cooklang/cooklang-rs
[cooklang]: https://cooklang.org
[uniffi]: https://mozilla.github.io/uniffi-rs/
