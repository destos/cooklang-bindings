# Recipe model

Every class on this page is a frozen dataclass holding no FFI objects, so
instances compare, hash and pickle like any other Python value. `Item` and
`Block` are type aliases for the unions a step's `items` and a section's
`blocks` hold.

::: cooklang.models
    options:
      heading_level: 2
      members:
        - Recipe
        - Section
        - Step
        - TextItem
        - IngredientRef
        - CookwareRef
        - TimerRef
        - Item
        - Note
        - Block
        - Ingredient
        - Cookware
        - Timer
        - Quantity
        - Range
        - NameAndUrl
        - RecipeTime
