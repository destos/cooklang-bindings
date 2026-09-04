# cooklang-bindings

Python bindings for [cooklang-rs][upstream], the official Rust implementation
of the [Cooklang][cooklang] recipe markup language.

!!! info "This is a binding, not a fork"

    The package contains no parser logic. Everything under
    `cooklang_rs/_generated/` is produced by [UniFFI][uniffi] from the
    interface upstream already maintains — the same interface behind their
    Swift and Kotlin bindings — and the rest is a thin Pythonic layer over
    that output. See [Relationship to cooklang-rs](upstream.md).

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

## In one screen

```pycon
>>> import cooklang_rs
>>> recipe = cooklang_rs.parse("""
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

## What is covered

| Area | Entry point |
| --- | --- |
| Recipes | [`parse`][cooklang_rs.parser.parse], [`combine_ingredients`][cooklang_rs.parser.combine_ingredients] |
| Aisle configuration | [`parse_aisle_config`][cooklang_rs.aisle.parse_aisle_config] |
| Shopping lists | [`parse_shopping_list`][cooklang_rs.shopping.parse_shopping_list] |
| Checked log | [`parse_checked_log`][cooklang_rs.shopping.parse_checked_log] |
| Quantity values | [`parse_value`][cooklang_rs.values.parse_value], [`format_value`][cooklang_rs.values.format_value] |

## Design notes

- **The model is plain data.** Every type in
  [`cooklang_rs.models`](api/models.md) is a frozen dataclass with no FFI
  object inside it, so instances compare, hash, pickle and hand to a template
  without surprises.
- **Display text comes from upstream.** A `Quantity` carries both a `value`
  for arithmetic and a `text` that preserves how the recipe wrote it — `1/2`
  stays `1/2` rather than becoming `0.5`.
- **Sections and notes are first class.** They are types upstream models
  directly, not something reconstructed from rendered text.

## Licence

MIT, matching upstream. Distributed wheels contain a compiled copy of the
MIT-licensed cooklang-rs. See [Relationship to cooklang-rs](upstream.md).

[upstream]: https://github.com/cooklang/cooklang-rs
[cooklang]: https://cooklang.org
[uniffi]: https://mozilla.github.io/uniffi-rs/
