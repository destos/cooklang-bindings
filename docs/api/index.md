# API reference

Everything listed here is re-exported from the top-level `cooklang`
package, so `from cooklang import parse, Recipe` works regardless of which
submodule a name is defined in. The submodule pages below exist to group the
API, not to describe an import path you have to use.

## The whole surface at a glance

| Group | Names |
| --- | --- |
| [Parsing](parser.md) | `parse`, `combine_ingredients`, `ParseError` |
| [Recipe model](models.md) | `Recipe`, `Section`, `Step`, `Note`, `Ingredient`, `Cookware`, `Timer`, `Quantity`, `Range`, `NameAndUrl`, `RecipeTime` |
| [Aisle configuration](aisle.md) | `parse_aisle_config`, `AisleConfig`, `AisleCategory`, `AisleIngredient` |
| [Shopping lists](shopping.md) | `parse_shopping_list`, `ShoppingList`, `RecipeItem`, `IngredientItem`, `ShoppingListError` |
| [Checked log](shopping.md#the-checked-log) | `parse_checked_log`, `checked_names`, `compact_checked_log`, `CheckEntry`, `Checked`, `Unchecked` |
| [Value helpers](values.md) | `parse_value`, `format_value` |
| [Errors](errors.md) | `CooklangError`, the base of `ParseError` and `ShoppingListError` |

Every error raised about the input is a `CooklangError`, and so a `ValueError`.
Passing an argument of the wrong type raises a plain `TypeError` instead, such
as `text must be str, not NoneType`, because that is a bug in the calling code
rather than bad input.

## What each function gives you back

| Call | Returns |
| --- | --- |
| `parse(text, *, scale=1.0)` | [`Recipe`][cooklang.models.Recipe] |
| `combine_ingredients(ingredients, *, indices=None, aisle=None)` | `dict[str, tuple[`[`Quantity`][cooklang.models.Quantity]`, ...]]` |
| `parse_aisle_config(text)` | [`AisleConfig`][cooklang.aisle.AisleConfig] |
| `AisleConfig.categories` | `tuple[`[`AisleCategory`][cooklang.aisle.AisleCategory]`, ...]` |
| `AisleConfig.category_for(name)` | `str | None` |
| `AisleConfig.common_name_for(name)` | `str` |
| `AisleConfig.group_by_category(names)` | `dict[str | None, tuple[str, ...]]` |
| `AisleConfig.apply_common_names(totals)` | `dict[str, tuple[`[`Quantity`][cooklang.models.Quantity]`, ...]]` |
| `parse_shopping_list(text)` | [`ShoppingList`][cooklang.shopping.ShoppingList] |
| `ShoppingList.to_text()` | `str` |
| `parse_checked_log(text)` | `tuple[`[`CheckEntry`][cooklang.shopping.CheckEntry]`, ...]` |
| `checked_names(entries)` | `tuple[str, ...]` |
| `compact_checked_log(entries, current_ingredients)` | `tuple[`[`CheckEntry`][cooklang.shopping.CheckEntry]`, ...]` |
| `parse_value(text)` | `int | float | str | `[`Range`][cooklang.models.Range] |
| `format_value(value)` | `str` |

## Package metadata

::: cooklang
    options:
      members: []
      show_root_heading: false
      show_root_toc_entry: false

`cooklang.__version__` is the version of these bindings.
`cooklang.UPSTREAM_VERSION` is the cooklang-rs release they were generated
from — see [Relationship to cooklang-rs](../upstream.md).

```pycon
>>> import cooklang
>>> isinstance(cooklang.__version__, str)
True
>>> cooklang.UPSTREAM_VERSION
'0.18.7'

```
