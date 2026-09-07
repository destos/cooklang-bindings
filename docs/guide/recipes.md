# Working with recipes

## Quantities

A [`Quantity`][cooklang.models.Quantity] carries three things: a `value` for
arithmetic, a `unit`, and the `text` upstream rendered — which preserves how
the recipe wrote the amount.

Whole numbers come back as `int`, not `float`:

```pycon
>>> import cooklang
>>> quantity = cooklang.parse("@flour{500%g}").ingredients[0].quantity
>>> quantity
Quantity(value=500, unit='g', text='500 g')
>>> isinstance(quantity.value, int)
True

```

Fractions keep their written form in `text` while `value` is a number:

```pycon
>>> cooklang.parse("@butter{1/2%cup}").ingredients[0].quantity
Quantity(value=0.5, unit='cup', text='1/2 cup')

```

Free-text amounts stay text — Cooklang tolerates them rather than erroring:

```pycon
>>> cooklang.parse("@salt{a pinch}").ingredients[0].quantity
Quantity(value='a pinch', unit=None, text='a pinch')

```

An ingredient with no amount at all has no quantity:

```pycon
>>> cooklang.parse("@salt").ingredients[0].quantity is None
True
>>> cooklang.parse("@salt{}").ingredients[0].quantity is None
True

```

Use `str()` — or `.text` — for display. Note that upstream normalizes a
decimal into the fraction a cook would write, which is exactly why `text`
exists as a separate field from `value`:

```pycon
>>> quantity = cooklang.parse("@milk{2.5%cups}").ingredients[0].quantity
>>> quantity.value
2.5
>>> str(quantity)
'2 1/2 cups'

```

!!! warning "Ranges are an extension, not canonical"

    Upstream's `CooklangParser::canonical()` has range extensions switched off,
    so `@onion{1-2}` parses as the *text* amount `"1-2"`, not a
    [`Range`][cooklang.models.Range]:

    ```pycon
    >>> cooklang.parse("@onion{1-2}").ingredients[0].quantity
    Quantity(value='1-2', unit=None, text='1-2')

    ```

    The `Range` type stays in the model because the FFI can express it, and
    [`parse_value`](values.md) does return one. A test pins the current
    behaviour so an upstream change surfaces here rather than silently
    changing a consumer's types.

## Ingredient notes and recipe references

A parenthesised descriptor becomes `note`:

```pycon
>>> cooklang.parse("Add @unsalted butter{2%tbsp}(softened).").ingredients[0]
Ingredient(name='unsalted butter', quantity=Quantity(value=2, unit='tbsp', text='2 tbsp'), note='softened', recipe_reference=None)

```

An ingredient that points at another recipe records the path it referred to:

```pycon
>>> cooklang.parse("Use @./pasta/dough{}.").ingredients[0]
Ingredient(name='dough', quantity=None, note=None, recipe_reference='./pasta/dough')

```

## Cookware and timers

Cookware is straightforward:

```pycon
>>> cooklang.parse("Fry it in a #pan{}.").cookware[0]
Cookware(name='pan', quantity=None)

```

Timers render inline as their **duration**, not their name, because that is
what reads correctly in prose:

```pycon
>>> recipe = cooklang.parse("Boil for ~eggs{3%minutes}.")
>>> recipe.timers[0].name
'eggs'
>>> recipe.steps[0].text
'Boil for 3 minutes.'

```

The name is the fallback for a timer written without a duration:

```pycon
>>> recipe = cooklang.parse("Wait for the ~oven{}.")
>>> recipe.steps[0].text
'Wait for the oven.'
>>> recipe.timers[0]
Timer(name='oven', quantity=None)

```

## Totalling ingredients

[`combine_ingredients`][cooklang.parser.combine_ingredients] sums repeated
ingredients, letting upstream do the unit arithmetic. It returns a mapping of
name to a tuple of totals.

```pycon
>>> recipe = cooklang.parse("Add @salt{2%tsp} then @salt{3%tsp}.")
>>> cooklang.combine_ingredients(recipe.ingredients)
{'salt': (Quantity(value=5, unit='tsp', text='5 tsp'),)}

```

Amounts in units that cannot be added stay as separate entries under one name
— this is why the value is a tuple rather than a single quantity:

```pycon
>>> recipe = cooklang.parse("Add @salt{1%tsp} then @salt{2%pinches}.")
>>> totals = cooklang.combine_ingredients(recipe.ingredients)
>>> sorted((q.unit, q.value) for q in totals["salt"])
[('pinches', 2), ('tsp', 1)]

```

Ingredients with no amount are still listed, so nothing silently disappears
from a shopping list:

```pycon
>>> recipe = cooklang.parse("Add @salt{} and @pepper.")
>>> sorted(cooklang.combine_ingredients(recipe.ingredients))
['pepper', 'salt']

```

### What it does not reconcile

`combine_ingredients` groups by name and adds amounts **that share a unit
string**. It does not reconcile beyond that, and the tuple is how it says so.

It does not convert within a dimension, because the canonical parser is built
with an empty unit converter and has no knowledge of units at all:

```pycon
>>> recipe = cooklang.parse("Add @flour{500%g} then @flour{1%kg}.")
>>> sorted((q.unit, q.value) for q in cooklang.combine_ingredients(recipe.ingredients)["flour"])
[('g', 500), ('kg', 1)]

```

It does not normalise plurals, since units are compared as strings:

```pycon
>>> recipe = cooklang.parse("Add @corn{2%ears} then @corn{1%ear}.")
>>> sorted((q.unit, q.value) for q in cooklang.combine_ingredients(recipe.ingredients)["corn"])
[('ear', 1), ('ears', 2)]

```

And an unquantified mention alongside a quantified one does not appear in the
tuple. The ingredient is kept, and the quantified total is exact, but the fact
that a further "and more to taste" mention existed is not represented:

```pycon
>>> recipe = cooklang.parse("Add @salt{2%tsp}.\n\nSeason with @salt.\n")
>>> cooklang.combine_ingredients(recipe.ingredients)
{'salt': (Quantity(value=2, unit='tsp', text='2 tsp'),)}

```

!!! note "Reconciliation is the caller's job"

    This is a deliberate division rather than a gap: totalling what is
    unambiguous is the parser's job, and deciding that 500 g plus 1 kg should
    be shown as "1.5 kg" is a domain decision about your reader. An app that
    wants one actionable number should layer that on top.

### Totalling a subset

`indices` selects which occurrences to include — the steps a user has ticked,
say. Positions refer to the sequence you passed in.

```pycon
>>> recipe = cooklang.parse("Add @salt{2%tsp}, @pepper{1%tsp} then @salt{3%tsp}.")
>>> cooklang.combine_ingredients(recipe.ingredients, indices=[0, 2])
{'salt': (Quantity(value=5, unit='tsp', text='5 tsp'),)}

```

An out-of-range index is an error rather than a silent skip:

```pycon
>>> cooklang.combine_ingredients(recipe.ingredients, indices=[9])
Traceback (most recent call last):
    ...
IndexError: index 9 out of range for 3 ingredients

```

### Totalling under common names

`aisle` resolves ingredient names through an
[aisle configuration](aisle.md) *before* totalling, so different spellings of
the same thing combine instead of sitting side by side. See
[Aisle configuration](aisle.md#totalling-under-common-names) for a worked
example.

## Marking components inline

`Step.text` renders a step as prose. `Step.items` gives the same step as a
sequence, so you can mark each component where it occurs rather than listing
them above the text:

```pycon
>>> import cooklang
>>> from cooklang import IngredientRef
>>> step = cooklang.parse("Whisk @flour{300%g} and @salt{1%tsp} in a #bowl{}.").steps[0]
>>> for item in step.items:
...     print(f"{type(item).__name__:15} {str(item)!r}")
TextItem        'Whisk '
IngredientRef   'flour'
TextItem        ' and '
IngredientRef   'salt'
TextItem        ' in a '
CookwareRef     'bowl'
TextItem        '.'

```

Joining the items reproduces the text, so the two never disagree:

```pycon
>>> "".join(str(item) for item in step.items).strip() == step.text
True

```

Each reference carries an `index` into the recipe's component list *and* the
resolved object — the same instance, not a copy:

```pycon
>>> recipe = cooklang.parse("Whisk @flour{300%g}.")
>>> ref = recipe.steps[0].items[1]
>>> (ref.index, ref.ingredient.name, ref.ingredient.quantity.text)
(0, 'flour', '300 g')
>>> ref.ingredient is recipe.ingredients[ref.index]
True

```

That matters when an ingredient appears more than once at different amounts.
`Step.ingredients` tells you what a step uses; `items` tells you which
occurrence sat where, so "roll on a floured surface" can show *its* amount
rather than the first one:

```pycon
>>> recipe = cooklang.parse(
...     "Rub @flour{300%g} into the butter.\n\nRoll on a @flour{30%g} surface.\n"
... )
>>> [
...     item.ingredient.quantity.text
...     for step in recipe.steps
...     for item in step.items
...     if isinstance(item, IngredientRef)
... ]
['300 g', '30 g']

```

## Blank lines delimit steps

Consecutive lines with no blank line between them are **one** step — that is a
paragraph, per the spec, not a list. A block of bare ingredient declarations
therefore parses as a single step whose text is the names in sequence:

```pycon
>>> import cooklang
>>> recipe = cooklang.parse("@lemongrass{2%stalks}\n@fennel{1}\n")
>>> [step.text for step in recipe.steps]
['lemongrass fennel']
>>> [i.name for i in recipe.ingredients]
['lemongrass', 'fennel']

```

The ingredients are extracted correctly either way, so this only affects how the
method reads. Insert blank lines to get one step per line:

```pycon
>>> import cooklang
>>> recipe = cooklang.parse("@lemongrass{2%stalks}\n\n@fennel{1}\n")
>>> [step.text for step in recipe.steps]
['lemongrass', 'fennel']

```

Worth knowing when importing recipes you did not author: tools that convert from
other formats often emit a bare declaration block like this, because they have
no prose to weave the ingredients into.

If you are rendering a corpus that already contains such recipes, you may want
to detect these steps rather than show them. A declaration-only step is exactly
one whose text is its own ingredient names in sequence:

```pycon
>>> import cooklang
>>> def is_declaration_only(step):
...     return bool(step.ingredients) and step.text == " ".join(
...         i.name for i in step.ingredients
...     )
...
>>> declarations = cooklang.parse("@olive oil{2%tbsp}\n@leeks{2}\n@potatoes{3}\n")
>>> [is_declaration_only(s) for s in declarations.steps]
[True]
>>> prose = cooklang.parse("Fry the @leeks{2} in @olive oil{2%tbsp}.")
>>> [is_declaration_only(s) for s in prose.steps]
[False]

```

This is deliberately left to the caller rather than built in: whether such a
step is noise or content depends on how you render, and the honest fix is to
edit the recipe. The ingredients are on `recipe.ingredients` regardless, so
filtering the step loses nothing.

## Extended syntax

Everything above is canonical Cooklang. `cooklang-rs` also defines a superset of
optional extensions, which these bindings cannot enable — and which are absorbed
into your data rather than rejected. See [Syntax extensions](../extensions.md).

## Errors

Malformed metadata and unclosed markup do not raise; they parse to whatever
upstream decides they mean.

```pycon
>>> cooklang.parse("@unclosed{1%g").ingredients[0].name
'unclosed'

```

[`CooklangError`][cooklang.parser.CooklangError] covers an outright parser
failure, which is rare. It subclasses `ValueError`, so
`except ValueError` catches it.

```pycon
>>> issubclass(cooklang.CooklangError, ValueError)
True

```
