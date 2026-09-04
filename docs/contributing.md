# Contributing

## Build from source

Requires a **Rust toolchain**, Python 3.10+, and git.

```sh
# Clone this repository (not cooklang-rs, which is vendored as a submodule).
git clone --recurse-submodules https://github.com/destos/cooklang-bindings.git
cd cooklang-bindings

make generate      # build the cdylib, generate the Python bindings
make test          # run the suite against the working tree
make wheel         # build a wheel for this machine
```

!!! important "Generated artifacts are not committed"

    A fresh checkout has **no compiled library**. Everything under
    `src/cooklang/_generated/` — the UniFFI-generated `cooklang_bindings.py`
    and the `libcooklang_bindings` shared library — is produced by
    `scripts/generate.py` and removed by `make clean`.

    Until you have run `make generate`, `import cooklang` fails with:

    ```
    ImportError: cooklang could not load its compiled bindings. If you are
    working from a source checkout, build them first:
        git submodule update --init --recursive
        python scripts/generate.py
    ```

`make wheel-linux` builds the manylinux x86_64 wheel in Docker, using the same
recipe as CI. On an Apple Silicon host it runs under emulation — correct, but
slow.

## Running the tests

```sh
make test
```

The suite is four files:

| File | What it covers |
| --- | --- |
| `tests/test_acceptance.py` | the end-to-end recipe from the project brief |
| `tests/test_api.py` | the Python layer — quantities, scaling, model types |
| `tests/test_defects.py` | one class per defect that drove this project |
| `tests/test_ffi_surface.py` | every function upstream exports, called at least once |

`tests/test_defects.py` uses the exact input that failed against the previous
parser for each of: `== Section ==` glued onto the following step, `> note`
lines rendered as numbered steps, YAML front matter silently discarded, and
consecutive `@ingredient` lines run together. The first two are structurally
impossible against this parser — upstream models sections and notes as
first-class types — but they are tested anyway, because the point is the
guarantee, not the mechanism.

`tests/test_ffi_surface.py` holds a coverage map of upstream's exported
functions and a test that fails when upstream adds or removes one. It is
mirrored in the docs as the [coverage table](upstream.md#coverage-of-upstreams-surface).

## Building the documentation

The docs are [MkDocs][mkdocs] with the [Material][material] theme, and the API
reference is generated from the source docstrings by
[mkdocstrings][mkdocstrings].

```sh
make docs          # build into build/site
make docs-serve    # live-reloading preview on http://127.0.0.1:8000
```

Both targets use [uv][uv] to provision a throwaway environment at
`build/docs-venv` from `docs/requirements.txt`. Everything they produce lives
under `build/`, so `make clean` removes it.

To drive it yourself:

```sh
uv venv build/docs-venv
VIRTUAL_ENV=build/docs-venv uv pip install -r docs/requirements.txt
build/docs-venv/bin/mkdocs build --strict
```

!!! note "Install `docs/requirements.txt`, not `.[docs]`"

    `pip install '.[docs]'` would also install the package itself, and *that*
    build compiles the Rust cdylib and runs `uniffi-bindgen`. The docs need
    none of it — see below. `pyproject.toml` still carries a `docs` extra for
    anyone who wants the toolchain listed alongside the other extras, and it
    mirrors `docs/requirements.txt` exactly.

### The one prerequisite

`mkdocstrings` reads the source with [Griffe][griffe], which analyses the AST
**statically** — it never imports `cooklang`. So the API reference builds fine
without a compiled library, and the docs build needs no Rust toolchain.

The **examples** are a different matter. Every code block in these docs is a
real session that is executed as part of verifying the docs, and running them
does need the bindings:

```sh
make generate      # once, before verifying the examples
```

If you are only editing prose and are content to leave the examples unchecked,
`make docs` works on a bare checkout.

### Verifying the examples

Every `pycon` block in `docs/` is a doctest. Run them all:

```sh
make generate      # the examples need the compiled bindings
PYTHONPATH=src build/docs-venv/bin/python -m doctest docs/*.md docs/guide/*.md docs/api/*.md
```

Silence means every example produced exactly the output shown. Add `-v` to see
each one run.

Please do not paste output you have not actually seen. If a block is meant to
be illustrative rather than executable, write it as a plain `python` or `sh`
block so the doctest runner skips it.

### Docstrings are the API reference

The pages under `docs/api/` are almost empty — they are `::: cooklang.module`
directives plus a list of members. The prose comes from the docstrings in
`src/cooklang/`. To improve the API reference, improve the docstring.

Docstrings use Google-style sections (`Args:`, `Returns:`, `Raises:`) and reST
roles (`:func:`, `:class:`) for cross-references. A small Griffe extension at
`docs/_extensions/sphinx_roles.py` rewrites those roles into mkdocstrings
cross-reference links at build time, and falls back to plain inline code for
anything it cannot resolve — so a role pointing at something undocumented will
not break the `--strict` build, but it will not become a link either.

## Moving to a new upstream release

1. Bump the `vendor/cooklang-rs` submodule to the new tag.
2. Update `UPSTREAM_VERSION` in `src/cooklang/__init__.py`.
3. `make test`.

CI fails if the constant and the submodule tag disagree. The suite is written
against parser behaviour, so a regression in the bump surfaces as a failing
test rather than as a surprise for a consumer. See
[Relationship to cooklang-rs](upstream.md#the-pinned-version).

## Read the Docs

`.readthedocs.yaml` builds the site on Read the Docs. It installs only
`docs/requirements.txt` and runs `mkdocs build --strict` — it does **not**
install the package, a Rust toolchain, or the generated bindings, because
Griffe does not need them.

[mkdocs]: https://www.mkdocs.org/
[material]: https://squidfunk.github.io/mkdocs-material/
[mkdocstrings]: https://mkdocstrings.github.io/
[griffe]: https://mkdocstrings.github.io/griffe/
[uv]: https://docs.astral.sh/uv/
