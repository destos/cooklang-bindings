# What this project adds

Almost everything in the `cooklang` namespace maps onto something cooklang-rs
already does. [`parse`][cooklang.parser.parse] is upstream's parser,
[`combine_ingredients`][cooklang.parser.combine_ingredients] is upstream's
totalling, the model types are its data. This page covers the exceptions: the
parts that are **ours**, with no upstream function behind them.

The distinction matters for two reasons. Upstream cannot change these, so a
cooklang-rs release will not alter their behaviour. And they encode opinions
about how an application should read a recipe, which is not the same as a fact
about Cooklang.

## The `contrib` namespace

Helpers that are pure additions live in `cooklang.contrib`, named after
`django.contrib` for the same reason: to keep opinionated extras from being
mistaken for the core contract.

```pycon
>>> import cooklang
>>> from cooklang import contrib

```

::: cooklang.contrib
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - unquantified_mentions
        - is_declaration_only
        - timer_duration

### Why `timer_duration` is not on `Timer`

A timer's unit is free text, and the canonical parser has no unit knowledge, so
`min`, `mins` and `Minutes` arrive as three unrelated strings. Turning those
into a duration means choosing which spellings to recognise and what an
unlabelled `~{20}` means — decisions about your corpus, not facts about
Cooklang. Putting them on `Timer` would make a lossy normalisation look like
parsed data, so the raw number and unit stay there and the interpretation lives
here.

It returns `None` rather than guessing whenever the timer is not a definite
length of time, so a caller can tell "no duration" from a wrong one.

## Conveniences in the main namespace

`contrib` is not the whole story. Several things on the model types are also
derived rather than reported — they stay in the main namespace because they are
how you read a recipe at all, not optional policy:

| What | Why it is ours |
| --- | --- |
| `Step.text` | Upstream gives a step as a list of items — text fragments and component references. Rendering those back to prose, with the components inline, is this layer's work. |
| `Step.number` | Upstream does not number steps. These are numbered across sections, skipping notes. |
| `Recipe.steps`, `Recipe.notes` | Flattened across sections, in document order. Upstream exposes blocks per section. |
| `Recipe.method` | Just the step text, for when you want the method as prose. |
| `Section.steps`, `Section.notes` | Filtered views over a section's blocks. |
| `Recipe.author`, `.source`, `.time` | Reshaped from upstream's separate getters into single values; `RecipeTime` also fills in `total` for a recipe that gave a prep/cook split. |
| `RecipeTime.total_duration`, `.prep_duration`, `.cook_duration` | Upstream reports whole minutes. These give the same values as `timedelta`, so they add to `contrib.timer_duration` without unit conversion. |
| `Recipe.metadata` | Assembled from upstream's standard-key getters plus its custom-key list, under Python-friendly names. |
| `Timer.__str__` | Renders a timer as its duration rather than its name, because that is what reads correctly inline. |
| `AisleConfig.group_by_category` | Buckets names by category in config order, collecting unlisted ones under `None`. |
| `AisleConfig.apply_common_names` | Reshapes upstream's `use_common_names` to work on totals you already computed. |
| `combine_ingredients(aisle=...)` | Resolves names through an aisle config *before* totalling, so aliases merge into one entry. |

## What is not ours

Everything else is upstream's, and its behaviour is upstream's to define — see
[Relationship to cooklang-rs](upstream.md) for the full coverage map. The
parsing rules, the totalling semantics, the shopping-list and aisle formats,
and the value parsing and formatting all come from cooklang-rs. If one of those
surprises you, the answer lives there rather than here.
