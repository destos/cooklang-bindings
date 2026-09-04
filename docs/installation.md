# Installation

```sh
pip install cooklang-bindings
```

The import name is `cooklang`, not the distribution name:

```pycon
>>> import cooklang
>>> isinstance(cooklang.__version__, str)
True

```

Python 3.10 or newer is required. The package is built and tested on 3.14.

## No Rust toolchain needed

Wheels ship a prebuilt native library. UniFFI's Python output drives that
library through `ctypes` rather than the CPython C API, which has a useful
consequence: **a wheel carries no Python ABI tag at all.** One
`py3-none-<platform>` wheel per platform covers every supported interpreter.

That is a weaker constraint than `abi3`, which would still pin a minimum
CPython version. Here there is no minimum imposed by the binary — only the
`requires-python` floor of the Python layer.

## Supported platforms

| Platform | Wheel tag | Notes |
| --- | --- | --- |
| Linux x86_64 | `py3-none-manylinux_2_28_x86_64` | glibc 2.28+ (RHEL 8, Debian 10, Ubuntu 18.10+) |
| macOS arm64 | `py3-none-macosx_11_0_arm64` | Apple Silicon, macOS 11+ |

Any other platform — Windows, Linux aarch64, macOS x86_64 — has no published
wheel and must [build from source](contributing.md#build-from-source), which
does need a Rust toolchain.

## Verifying the install

If the compiled library is missing or was built for the wrong platform, the
import fails early with a message that says so rather than failing later in a
confusing place:

```
ImportError: cooklang could not load its compiled bindings. If you are
working from a source checkout, build them first:
    git submodule update --init --recursive
    python scripts/generate.py
Otherwise install a wheel built for your platform.
```

A working install parses a recipe:

```pycon
>>> import cooklang
>>> cooklang.parse("Chop the @onion{1}.").steps[0].text
'Chop the onion.'

```

And reports which upstream release it was generated from:

```pycon
>>> cooklang.UPSTREAM_VERSION
'0.18.7'

```

## Installing with uv

```sh
uv add cooklang-bindings
```

or, into an existing environment:

```sh
uv pip install cooklang-bindings
```

## Working from a checkout

A source checkout has no compiled library until you build one — the generated
artifacts are deliberately not committed. See
[Contributing](contributing.md#build-from-source).
