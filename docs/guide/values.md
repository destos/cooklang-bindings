# Quantity values

[`parse_value`][cooklang.values.parse_value] and
[`format_value`][cooklang.values.format_value] expose upstream's own number
handling on its own, without a recipe around it.

They matter because Cooklang's notion of a "value" is not Python's: it
round-trips fractions, and it treats an unreadable amount as text rather than
an error. If you accept a quantity from a user — a shopping-list app letting
someone edit `1 1/2` — you want upstream's reading of it, not `float()`'s.

## Reading a value

```pycon
>>> import cooklang
>>> cooklang.parse_value("2")
2
>>> cooklang.parse_value("0.25")
0.25

```

Whole numbers come back as `int`:

```pycon
>>> isinstance(cooklang.parse_value("2"), int)
True

```

Fractions and mixed numbers are understood:

```pycon
>>> cooklang.parse_value("1/2")
0.5
>>> cooklang.parse_value("1 1/2")
1.5

```

A range becomes a [`Range`][cooklang.models.Range]:

```pycon
>>> cooklang.parse_value("1/2 - 3/4")
Range(start=0.5, end=0.75)

```

!!! note

    This is the one place a `Range` appears. Ranges written *inside a recipe*
    are a cooklang-rs extension that the canonical parser leaves off, so
    `@onion{1-2}` parses as text — see
    [Working with recipes](recipes.md#quantities).

Anything unreadable comes back as the original string rather than raising,
matching Cooklang's tolerance of free-text amounts:

```pycon
>>> cooklang.parse_value("a pinch")
'a pinch'

```

Non-string input is rejected:

```pycon
>>> cooklang.parse_value(1.5)
Traceback (most recent call last):
    ...
TypeError: text must be str, not float

```

## Rendering a value

`format_value` is upstream's renderer, and it restores fractions:

```pycon
>>> cooklang.format_value(0.5)
'1/2'
>>> cooklang.format_value(1.5)
'1 1/2'
>>> cooklang.format_value(2)
'2'

```

Text passes through, `None` renders as the empty string, and a `Range` renders
with its separator:

```pycon
>>> cooklang.format_value("a pinch")
'a pinch'
>>> cooklang.format_value(None)
''
>>> cooklang.format_value(cooklang.Range(start=1.0, end=2.0))
'1 - 2'

```

## Round-tripping

Reading then rendering gives back an equivalent value, though not always the
identical string — `format_value` normalizes spacing and fraction form:

```pycon
>>> for written in ("2", "1/2", "1 1/2", "a pinch"):
...     print(f"{written!r:12} -> {cooklang.parse_value(written)!r:10} -> {cooklang.format_value(cooklang.parse_value(written))!r}")
'2'          -> 2          -> '2'
'1/2'        -> 0.5        -> '1/2'
'1 1/2'      -> 1.5        -> '1 1/2'
'a pinch'    -> 'a pinch'  -> 'a pinch'

```

This is exactly the pair a quantity editor needs: `parse_value` on the way in,
`format_value` on the way back out to the field.

## Relationship to `Quantity.text`

A parsed recipe already gives you the rendered form on
[`Quantity.text`][cooklang.models.Quantity], produced by upstream at parse
time. These helpers are for values that did not come from a recipe — an
ingredient line in a `.shopping-list`, or something a user typed.

```pycon
>>> cooklang.parse("@butter{1/2%cup}").ingredients[0].quantity.text
'1/2 cup'
>>> cooklang.format_value(cooklang.parse_value("1/2")) + " cup"
'1/2 cup'

```
