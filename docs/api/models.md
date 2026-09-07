# Recipe model

Every type on this page is a frozen dataclass holding no FFI objects, so
instances compare, hash and pickle like any other Python value.

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
        - Note
        - Ingredient
        - Cookware
        - Timer
        - Quantity
        - Range
        - NameAndUrl
        - RecipeTime
