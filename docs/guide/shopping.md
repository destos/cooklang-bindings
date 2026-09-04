# Shopping lists

Upstream parses two related file formats, and both are wrapped here.

`.shopping-list`
:   Recipe references and free-hand ingredients, nested by indentation.

`.shopping-checked`
:   An append-only log of what has been picked up.

## Parsing a list

A line beginning `./` is a recipe reference; anything else is a free-hand
ingredient. A `{...}` suffix is a multiplier on a recipe and a quantity on an
ingredient. Children are indented by **two spaces per level**.

```pycon
>>> import cooklang
>>> LIST = """./Breakfast/Pancakes{2}
...   ./Toppings/Syrup
...   milk{500%ml}
... bread
... eggs{6}
... """
>>> shopping = cooklang.parse_shopping_list(LIST)
>>> len(shopping)
3

```

The top-level items keep document order, and the two views split them by kind:

```pycon
>>> [str(item) for item in shopping]
['./Breakfast/Pancakes{2}', 'bread', 'eggs{6}']
>>> shopping.recipes[0].path
'Breakfast/Pancakes'
>>> shopping.recipes[0].multiplier
2.0
>>> shopping.ingredients
(IngredientItem(name='bread', quantity=None), IngredientItem(name='eggs', quantity='6'))

```

`path` is stored without the leading `./` that marked the line as a reference.

Nested lines become that recipe's `children`, recursively:

```pycon
>>> shopping.recipes[0].children
(RecipeItem(path='Toppings/Syrup', multiplier=None, children=()), IngredientItem(name='milk', quantity='500%ml'))

```

An ingredient's `quantity` is kept as the raw string the file gave, unparsed.
[`parse_value`](values.md) will read it if you need a number:

```pycon
>>> cooklang.parse_value(shopping.ingredients[1].quantity)
6

```

## Writing a list back out

[`to_text`][cooklang.shopping.ShoppingList.to_text] serializes back to the same
format, so an edited list round-trips:

```pycon
>>> print(shopping.to_text(), end="")
./Breakfast/Pancakes{2}
  ./Toppings/Syrup
  milk{500%ml}
bread
eggs{6}
>>> shopping.to_text() == LIST
True

```

Because the model is a frozen dataclass, "editing" means building a new one:

```pycon
>>> extended = cooklang.ShoppingList(
...     items=shopping.items + (cooklang.IngredientItem(name="butter", quantity="250%g"),)
... )
>>> print(extended.to_text(), end="")
./Breakfast/Pancakes{2}
  ./Toppings/Syrup
  milk{500%ml}
bread
eggs{6}
butter{250%g}

```

## Errors

[`ShoppingListError`][cooklang.shopping.ShoppingListError] covers a list that
cannot be parsed or serialized. Indentation that is not a clean two-space level
is the common one:

```pycon
>>> cooklang.parse_shopping_list("./a\n   bad\n")
Traceback (most recent call last):
    ...
cooklang.shopping.ShoppingListError: reason='Invalid indentation at line'

```

It subclasses `ValueError`:

```pycon
>>> issubclass(cooklang.ShoppingListError, ValueError)
True

```

## The checked log

A `.shopping-checked` file records what has been picked up, one entry per line:
`+ name` for checked, `- name` for put back. It is append-only, so the same
ingredient may appear more than once and later entries win.

```pycon
>>> LOG = "+ milk\n+ bread\n- milk\n+ Eggs\n"
>>> entries = cooklang.parse_checked_log(LOG)
>>> entries
(Checked(name='milk', checked=True), Checked(name='bread', checked=True), Unchecked(name='milk', checked=False), Checked(name='Eggs', checked=True))

```

[`Checked`][cooklang.shopping.Checked] and
[`Unchecked`][cooklang.shopping.Unchecked] differ only in their fixed `checked`
flag, which is not settable — the type *is* the state.

```pycon
>>> cooklang.Checked("milk").checked
True
>>> cooklang.Unchecked("milk").checked
False

```

### Replaying a log

[`checked_names`][cooklang.shopping.checked_names] replays the entries and
returns what is currently checked, lowercased and sorted. Milk was checked then
unchecked, so it is absent; `Eggs` is normalized to `eggs`.

```pycon
>>> cooklang.checked_names(entries)
('bread', 'eggs')

```

### Compacting a log

An append-only log grows forever and accumulates entries for ingredients that
are no longer on the list.
[`compact_checked_log`][cooklang.shopping.compact_checked_log] collapses it so
each ingredient appears at most once, and drops entries for anything not in the
current ingredient set.

```pycon
>>> cooklang.compact_checked_log(entries, ["milk", "bread", "eggs"])
(Checked(name='bread', checked=True), Checked(name='eggs', checked=True))

```

!!! warning "Pass the aggregated ingredients, not the list's own lines"

    `current_ingredients` must be the fully-expanded ingredient names as shown
    to the user. A `.shopping-list` on disk holds mostly recipe *references*,
    so passing its own item names would discard every entry as stale:

    ```pycon
    >>> cooklang.compact_checked_log(entries, ["Breakfast/Pancakes", "bread", "eggs"])
    (Checked(name='bread', checked=True), Checked(name='eggs', checked=True))
    >>> cooklang.compact_checked_log(entries, [])
    ()

    ```

### Writing entries back out

Each entry serializes itself, newline included, so a log is the concatenation
of its entries:

```pycon
>>> cooklang.Checked("milk").to_text()
'+ milk\n'
>>> cooklang.Unchecked("milk").to_text()
'- milk\n'
>>> print("".join(e.to_text() for e in cooklang.compact_checked_log(entries, ["milk", "bread", "eggs"])), end="")
+ bread
+ eggs

```

## Putting it together

Expand a list's recipes, total the ingredients, group them by aisle, and mark
off what is already checked:

```pycon
>>> config = cooklang.parse_aisle_config("[dairy]\nmilk\n\n[bakery]\nbread\n")
>>> recipe = cooklang.parse("Warm @milk{500%ml}. Toast @bread{2%slices}.")
>>> totals = cooklang.combine_ingredients(recipe.ingredients, aisle=config)
>>> done = set(cooklang.checked_names(entries))
>>> for category, names in config.group_by_category(sorted(totals)).items():
...     print(f"[{category or 'other'}]")
...     for name in names:
...         mark = "x" if name in done else " "
...         print(f"  [{mark}] {name} {totals[name][0].text}")
[dairy]
  [ ] milk 500
[bakery]
  [x] bread 2

```
