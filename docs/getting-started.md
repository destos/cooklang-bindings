# Getting started

This page walks one recipe from source text to a fully explored model. Every
block below is a real session — copy it into a REPL and you will see the same
output.

## Parse something

[`parse`][cooklang.parser.parse] is the entry point. It takes Cooklang source
and returns a [`Recipe`][cooklang.models.Recipe].

```pycon
>>> import cooklang
>>> recipe = cooklang.parse("Chop the @onion{1}.")
>>> recipe.steps[0].text
'Chop the onion.'
>>> recipe.ingredients[0].name
'onion'

```

Cooklang is forgiving: nearly any text is a valid recipe. Empty input is an
empty recipe rather than an error.

```pycon
>>> cooklang.parse("")
Recipe(metadata={}, sections=(), ingredients=(), cookware=(), timers=(), author=None, source=None, time=None)

```

Non-string input is the one thing that is rejected outright:

```pycon
>>> cooklang.parse(None)
Traceback (most recent call last):
    ...
TypeError: text must be str, not NoneType

```

## A recipe with everything in it

The rest of this page uses one source string:

```pycon
>>> SOURCE = """
... ---
... title: Sourdough
... servings: 2
... author: Ada Lovelace
... source: https://example.com/sourdough
... prep time: 20
... cook time: 40
... tags: [bread, slow]
... mood: patient
... ---
...
... == Levain ==
...
... Mix @flour{500%g} with @water{350%ml} in a #large bowl{}.
...
... > Use a warm room.
...
... == Bake ==
...
... Bake for ~{40%minutes} at 240C.
... """
>>> recipe = cooklang.parse(SOURCE)

```

### Metadata

Standard keys are exposed under Python-friendly names; custom keys come
through exactly as written.

```pycon
>>> recipe.title
'Sourdough'
>>> recipe.servings
2
>>> recipe.tags
('bread', 'slow')
>>> recipe.metadata["mood"]
'patient'
>>> sorted(recipe.metadata)
['author', 'mood', 'servings', 'source', 'tags', 'title']

```

`metadata` is read-only, like the rest of the recipe, and list values such as
`tags` come back as tuples. That is what lets a `Recipe` be hashed, used as a
dict key and pickled. `dict(recipe.metadata)` gives you a mutable copy:

```pycon
>>> recipe.metadata["tags"]
('bread', 'slow')
>>> recipe.metadata["mood"] = "rushed"
Traceback (most recent call last):
    ...
TypeError: '_Metadata' object does not support item assignment
>>> copy = dict(recipe.metadata)
>>> copy["mood"] = "rushed"

```

`description` is `None` when the recipe gave none — the accessors never raise
for a missing key:

```pycon
>>> recipe.description is None
True

```

### Credits and timing

`author` and `source` come back as [`NameAndUrl`][cooklang.models.NameAndUrl],
which lets either half stand alone: a recipe may credit a name, a bare URL, or
a name linked to one.

```pycon
>>> recipe.author
NameAndUrl(name='Ada Lovelace', url=None)
>>> recipe.source
NameAndUrl(name=None, url='https://example.com/sourdough')
>>> str(recipe.author)
'Ada Lovelace'

```

[`RecipeTime`][cooklang.models.RecipeTime] flattens upstream's two shapes — a
single `time:` or a `prep time:`/`cook time:` split — into one type, so
`.total` is always readable without first asking which form the recipe used.

```pycon
>>> recipe.time
RecipeTime(total=60, prep=20, cook=40)
>>> str(recipe.time)
'60 minutes'

```

### Sections, steps and notes

`== Heading ==` produces a [`Section`][cooklang.models.Section].

```pycon
>>> [section.name for section in recipe.sections]
['Levain', 'Bake']

```

Step numbers run across sections, so they match how a cook counts them:

```pycon
>>> for step in recipe.steps:
...     print(step.number, step.text)
1 Mix flour with water in a large bowl.
2 Bake for 40 minutes at 240C.

```

`method` is a shortcut for just the text:

```pycon
>>> recipe.method
('Mix flour with water in a large bowl.', 'Bake for 40 minutes at 240C.')

```

A `> note` line is a [`Note`][cooklang.models.Note], never a numbered step:

```pycon
>>> recipe.notes
(Note(text='Use a warm room.'),)

```

A section's `blocks` holds steps and notes together in document order:

```pycon
>>> [type(block).__name__ for block in recipe.sections[0].blocks]
['Step', 'Note']

```

### Components

Ingredients, cookware and timers are listed at the recipe level in document
order, and attached to the individual step that uses them.

```pycon
>>> [ingredient.name for ingredient in recipe.ingredients]
['flour', 'water']
>>> recipe.cookware
(Cookware(name='large bowl', quantity=None),)
>>> recipe.timers
(Timer(name=None, quantity=Quantity(value=40, unit='minutes', text='40 minutes')),)
>>> [ingredient.name for ingredient in recipe.steps[0].ingredients]
['flour', 'water']
>>> recipe.steps[0].timers
()

```

## Scaling

`scale` multiplies every quantity. It is keyword-only.

```pycon
>>> doubled = cooklang.parse(SOURCE, scale=2.0)
>>> [(i.name, i.quantity.text) for i in doubled.ingredients]
[('flour', '1000 g'), ('water', '700 ml')]
>>> halved = cooklang.parse(SOURCE, scale=0.5)
>>> [(i.name, i.quantity.text) for i in halved.ingredients]
[('flour', '250 g'), ('water', '175 ml')]

```

## Rendering a recipe

Because the model is plain data, printing it is unremarkable:

```pycon
>>> print(recipe.title)
Sourdough
>>> for section in recipe.sections:
...     print(f"## {section}")
...     for block in section.blocks:
...         if isinstance(block, cooklang.Step):
...             print(f"{block.number}. {block.text}")
...         else:
...             print(f"> {block.text}")
## Levain
1. Mix flour with water in a large bowl.
> Use a warm room.
## Bake
2. Bake for 40 minutes at 240C.

```

## Where to next

- [Working with recipes](guide/recipes.md) — quantities, references, totalling
- [Aisle configuration](guide/aisle.md) — categories and common names
- [Shopping lists](guide/shopping.md) — lists and the checked log
- [Quantity values](guide/values.md) — reading and rendering amounts
- [API reference](api/index.md) — every name, with its return type
