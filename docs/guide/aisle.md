# Aisle configuration

An aisle configuration maps ingredient names — and their aliases — to shopping
categories, and gives each group a single canonical name. It is what makes it
possible to reconcile one recipe writing `@onions{2}` with another writing
`@brown onion{1}` before totalling them.

## The format

Upstream parses a simple sectioned format: a category in square brackets, then
one line per ingredient, with `|`-separated aliases.

```pycon
>>> import cooklang
>>> AISLE = """
... [produce]
... onion|onions|brown onion
... fennel
...
... [dairy]
... butter|unsalted butter
... """
>>> config = cooklang.parse_aisle_config(AISLE)
>>> config
<AisleConfig 2 categories>

```

The first name on a line is the canonical one; the rest are aliases for it.

```pycon
>>> config.categories
(AisleCategory(name='produce', ingredients=(AisleIngredient(name='onion', aliases=('onions', 'brown onion')), AisleIngredient(name='fennel', aliases=()))), AisleCategory(name='dairy', ingredients=(AisleIngredient(name='butter', aliases=('unsalted butter',)),)))
>>> [category.name for category in config.categories]
['produce', 'dairy']
>>> config.categories[0].ingredients[0].aliases
('onions', 'brown onion')

```

Categories come back in the order the file listed them, which is usually the
order you want to render a shopping list in.

## Common names

[`common_name_for`][cooklang.aisle.AisleConfig.common_name_for] is the heart of
the aisle config. It resolves any name or alias to the canonical name for its
group, **case-insensitively**.

```pycon
>>> config.common_name_for("onions")
'onion'
>>> config.common_name_for("brown onion")
'onion'
>>> config.common_name_for("Onions")
'onion'
>>> config.common_name_for("unsalted butter")
'butter'

```

It never returns `None`. An ingredient the config does not mention comes back
unchanged, which makes it safe to map over a whole list without filtering
first:

```pycon
>>> config.common_name_for("kale")
'kale'
>>> [config.common_name_for(name) for name in ("Onions", "brown onion", "kale")]
['onion', 'onion', 'kale']

```

## Categories

[`category_for`][cooklang.aisle.AisleConfig.category_for] answers which aisle
an ingredient belongs to, or `None` if the config does not list it. It matches
the way `common_name_for` does, case-insensitively and through aliases:

```pycon
>>> config.category_for("onion")
'produce'
>>> config.category_for("Onions")
'produce'
>>> config.category_for("Unsalted Butter")
'dairy'
>>> config.category_for("kale") is None
True

```

The two methods agree because they answer the same question: is this
ingredient in the config? Upstream's category lookup is exact-match only, so on
its own it would call `"Onions"` unlisted even though `common_name_for`
resolves it to `"onion"`. A shopping list would then file the same ingredient
under "other" or under produce depending on how a recipe capitalised it.
`category_for` tries upstream's exact match first, then looks up the category
of the common name, so user-entered text needs no normalising first.

## Laying out a shopping list

[`group_by_category`][cooklang.aisle.AisleConfig.group_by_category] buckets
names for display. Categories appear in config order, and anything unlisted is
grouped under `None` so it can be rendered as "other" rather than dropped.

```pycon
>>> config.group_by_category(["butter", "onions", "kale"])
{'produce': ('onions',), 'dairy': ('butter',), None: ('kale',)}

```

Because it goes through `category_for`, a capitalised or aliased name lands in
its aisle too, rather than under `None`:

```pycon
>>> config.group_by_category(["Onions", "Unsalted Butter"])
{'produce': ('Onions',), 'dairy': ('Unsalted Butter',)}

```

Rendering that is a plain loop:

```pycon
>>> for category, names in config.group_by_category(["butter", "onions", "kale"]).items():
...     print(f"{category or 'other'}: {', '.join(names)}")
produce: onions
dairy: butter
other: kale

```

Note that the *input* names come back, not their common names — so pass names
you already resolved if you want canonical labels.

## Totalling under common names

This is where it pays off. Without a config, two spellings of onion are two
separate entries:

```pycon
>>> recipe = cooklang.parse("Dice @onions{2} and @brown onion{1}. Melt @butter{30%g}.")
>>> totals = cooklang.combine_ingredients(recipe.ingredients)
>>> sorted(totals)
['brown onion', 'butter', 'onions']

```

Pass `aisle=` and upstream resolves the names *before* totalling, so the two
onions merge into one entry with the quantities actually added up:

```pycon
>>> combined = cooklang.combine_ingredients(recipe.ingredients, aisle=config)
>>> sorted(combined)
['butter', 'onion']
>>> combined["onion"]
(Quantity(value=3, unit=None, text='3'),)

```

### Applying common names afterwards

If you already have totals in hand,
[`apply_common_names`][cooklang.aisle.AisleConfig.apply_common_names] does the
same rewrite on an existing mapping. It is not a plain key rename: entries that
collapse onto the same common name have their quantities merged by upstream.

```pycon
>>> normalized = config.apply_common_names(totals)
>>> sorted(normalized)
['butter', 'onion']
>>> normalized["onion"]
(Quantity(value=3, unit=None, text='3'),)

```

Use `combine_ingredients(..., aisle=...)` when you are totalling from scratch,
and `apply_common_names` when the totals arrived from somewhere else.

## Reusing a config

An `AisleConfig` is immutable, so parse it once at startup and reuse it across
every recipe.

```pycon
>>> config.common_name_for("Onions"), config.common_name_for("onions")
('onion', 'onion')

```

`parse_aisle_config(text)`, `AisleConfig(text)` and
`AisleConfig.from_text(text)` do the same thing; use whichever reads best in
your code.

```pycon
>>> cooklang.AisleConfig(AISLE) == cooklang.AisleConfig.from_text(AISLE) == config
True

```

It holds a native FFI object, so unlike the recipe model it is not a
dataclass, but it still behaves as a value. Two configs with the same
categories compare equal and hash alike, so a config can key a cache. Pickling
a config stores its source text and re-parses it when unpickled, instead of
storing a native pointer that would dangle in another process. That makes it
safe to send a config to a worker pool:

```pycon
>>> import pickle
>>> restored = pickle.loads(pickle.dumps(config))
>>> restored == config, hash(restored) == hash(config)
(True, True)
>>> restored.category_for("Onions")
'produce'

```

Non-string input is rejected the same way `parse` rejects it:

```pycon
>>> cooklang.parse_aisle_config(None)
Traceback (most recent call last):
    ...
TypeError: text must be str, not NoneType

```
