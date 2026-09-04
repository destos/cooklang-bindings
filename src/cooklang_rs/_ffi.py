"""Loads the generated UniFFI module and applies binding-layer fixups.

Everything in here is about making the *generated* Python usable. It does not
change parser behaviour.
"""

from __future__ import annotations

try:
    from ._generated import cooklang_bindings as ffi
except ImportError as exc:  # pragma: no cover - depends on install method
    raise ImportError(
        "cooklang_rs could not load its compiled bindings. If you are working "
        "from a source checkout, build them first:\n"
        "    git submodule update --init --recursive\n"
        "    python scripts/generate.py\n"
        "Otherwise install a wheel built for your platform."
    ) from exc


def _restore_record_hashing() -> None:
    """Make `GroupedQuantityKey` hashable again.

    UniFFI's Python backend emits records as plain classes with a generated
    `__eq__` and no `__hash__`, which Python turns into `__hash__ = None`.
    Upstream uses `HashMap<GroupedQuantityKey, Value>` as a return type, so the
    generated converter tries to use an unhashable object as a dict key and
    `combine_ingredients()` / `use_common_names()` die with:

        TypeError: cannot use 'GroupedQuantityKey' as a dict key

    The Rust type derives Hash + Eq, so restoring a consistent `__hash__` here
    matches upstream's own contract. Kotlin and Swift are unaffected because
    their record types get structural hashing for free, which is why this only
    shows up on the Python target.

    Tracked upstream: see README, "Known upstream gaps".
    """
    key = getattr(ffi, "GroupedQuantityKey", None)
    if key is not None and key.__hash__ is None:
        key.__hash__ = lambda self: hash((self.name, self.unit_type))


_restore_record_hashing()

__all__ = ["ffi"]
