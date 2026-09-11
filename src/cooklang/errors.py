"""The base exception for everything this package raises about its input.

Each format has its own error --
:class:`~cooklang.parser.ParseError` for recipes,
:class:`~cooklang.shopping.ShoppingListError` for shopping lists -- and both
derive from :class:`CooklangError`, so one ``except`` covers the package.

``CooklangError`` itself subclasses ``ValueError``, because every error it
covers is a problem with a value the caller passed in. Existing
``except ValueError`` handlers keep working.

A wrong *type* is different: passing ``None`` where text belongs is a bug in
the calling code, not bad input, and raises a plain ``TypeError``.
"""

from __future__ import annotations

__all__ = ["CooklangError"]


class CooklangError(ValueError):
    """Base class for every error this package raises about its input.

    Example:
        >>> import cooklang
        >>> issubclass(cooklang.ParseError, cooklang.CooklangError)
        True
        >>> issubclass(cooklang.ShoppingListError, cooklang.CooklangError)
        True
    """
