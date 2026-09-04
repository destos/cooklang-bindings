"""Wheel packaging for cooklang-rs.

UniFFI's Python backend talks to the Rust library through `ctypes`, not the
CPython C API. That means the wheel contains no CPython extension module, so it
is:

  * platform specific  - it ships a native .so/.dylib, so it needs a plat tag;
  * Python ABI neutral - it works on any CPython that can run the generated
    module, so it is tagged `py3-none-<platform>` rather than `cp314-...`.

This is strictly better than abi3 for our purposes: abi3 would still pin a
minimum CPython, whereas ctypes pins nothing. The one wheel per platform covers
every supported interpreter.
"""

import os
import pathlib
import re

from setuptools import setup
from setuptools.dist import Distribution

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:  # setuptools >= 70 vendors it here
    from setuptools.command.bdist_wheel import bdist_wheel


# The lowest macOS we build for. Rust's aarch64-apple-darwin target defaults to
# a minimum of 11.0, which is what `otool -l` reports on the built dylib.
MACOS_DEPLOYMENT_TARGET = os.environ.get("MACOSX_DEPLOYMENT_TARGET", "11.0")


def _retarget_macos(platform: str) -> str:
    """Tag macOS wheels by what the library actually needs.

    `bdist_wheel` derives the macOS version in the tag from the *interpreter's*
    build settings. A Homebrew Python built against a current SDK yields e.g.
    `macosx_26_0_arm64`, which would make pip refuse the wheel on any older
    macOS even though the dylib runs happily on 11.0.
    """
    match = re.fullmatch(r"macosx_\d+_\d+_(?P<arch>.+)", platform)
    if not match:
        return platform
    major, _, minor = MACOS_DEPLOYMENT_TARGET.partition(".")
    return f"macosx_{major}_{minor or 0}_{match.group('arch')}"


class BinaryDistribution(Distribution):
    """Marks the distribution as platform specific despite having no ext modules."""

    def has_ext_modules(self) -> bool:
        return True

    def is_pure(self) -> bool:
        return False


def _check_single_native_library() -> None:
    """Fail the build if `_generated/` holds libraries for more than one platform.

    Generating on macOS and then in a Linux container leaves both a .dylib and
    a .so behind, and the package-data glob would happily ship the pair -- a
    silently bloated wheel carrying a library it can never load. Cheap to
    check, and it turns a quiet packaging bug into a build failure.
    """
    generated = pathlib.Path(__file__).parent / "src" / "cooklang_rs" / "_generated"
    libraries = sorted(
        p.name
        for pattern in ("*.so", "*.dylib", "*.dll")
        for p in generated.glob(pattern)
    )
    if not libraries:
        raise SystemExit(
            "No native library in src/cooklang_rs/_generated/.\n"
            "Run `python scripts/generate.py` before building a wheel."
        )
    if len(libraries) > 1:
        raise SystemExit(
            f"Multiple native libraries found: {', '.join(libraries)}.\n"
            "A wheel targets one platform. Run `make clean` and regenerate."
        )


class PlatformWheel(bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False
        _check_single_native_library()

    def get_tag(self) -> tuple[str, str, str]:
        _python, _abi, platform = super().get_tag()
        return "py3", "none", _retarget_macos(platform)


setup(distclass=BinaryDistribution, cmdclass={"bdist_wheel": PlatformWheel})
