"""Griffe extension: render the reST roles used in the source docstrings.

The `cooklang` docstrings are written with reST roles (`:func:`, `:class:`,
`:meth:`, `:mod:`) and reST links, because they read well in an editor and in
`help()`. mkdocstrings renders Markdown, so this extension rewrites those
constructs into mkdocstrings cross-reference syntax before rendering.

Resolution is entirely static -- it walks the scopes Griffe already collected
(the object's own members, its parent's, its module's, its package's), so
building the docs never imports `cooklang` and therefore never needs the
compiled native library. A target that resolves to nothing degrades to plain
inline code rather than becoming a dangling link, which keeps `--strict`
builds clean.
"""

from __future__ import annotations

import re

from griffe import Alias, Extension, Object

# `:role:`~some.dotted.Target`` and `:role:`Target``
_ROLE = re.compile(r":(?:class|func|meth|mod|attr|data|obj|exc):`(~?)([^`]+)`")
# ``text <https://url>``_
_LINK = re.compile(r"`([^`<]+?)\s*<([^`>]+)>`_")


def _path_of(member: Object | Alias) -> str | None:
    """The canonical path of a member, following one level of aliasing."""
    if isinstance(member, Alias):
        try:
            return member.target_path
        except Exception:  # pragma: no cover - defensive
            return None
    return member.path


def _scopes(obj: Object):
    """The scopes a bare name in `obj`'s docstring could refer to, nearest first."""
    seen: set[int] = set()
    current: Object | None = obj
    while current is not None:
        if id(current) not in seen:
            seen.add(id(current))
            yield current
        current = current.parent if isinstance(current.parent, Object) else None


class SphinxRoles(Extension):
    """Rewrite reST roles and links in docstrings into Markdown."""

    def _resolve(self, obj: Object, target: str) -> str | None:
        # Fully-qualified already (`cooklang.models.Recipe`): trust it.
        if target.count(".") >= 2:
            return target

        head, _, rest = target.partition(".")
        for scope in _scopes(obj):
            members = getattr(scope, "members", None)
            if not members:
                continue
            member = members.get(head)
            if member is None:
                continue
            path = _path_of(member)
            if path is None:
                continue
            return f"{path}.{rest}" if rest else path

        # `cooklang.parse` where the package itself was not in scope.
        package = obj.package
        if package is not None and head == package.name and rest:
            member = package.members.get(rest)
            if member is not None:
                return _path_of(member)
        return None

    def _replace_role(self, match: re.Match[str], obj: Object) -> str:
        short, target = match.group(1), match.group(2)
        display = target.rsplit(".", 1)[-1] if short else target
        resolved = self._resolve(obj, target)
        if resolved is None:
            return f"`{display}`"
        return f"[`{display}`][{resolved}]"

    def on_instance(self, *, obj: Object, **kwargs: object) -> None:
        """Rewrite this object's docstring in place."""
        docstring = obj.docstring
        if docstring is None:
            return
        text = _ROLE.sub(lambda m: self._replace_role(m, obj), docstring.value)
        docstring.value = _LINK.sub(r"[\1](\2)", text)
