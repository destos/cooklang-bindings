# cooklang-bindings

Python bindings for cooklang-rs: UniFFI-generated code under
`src/cooklang/_generated/` plus a thin Pythonic layer over it.

- **[STYLEGUIDE.md](STYLEGUIDE.md) is the contract for code under
  `src/cooklang/`.** Read it before changing the public API, and run its
  section 10 checklist before opening a PR.
- Never edit `src/cooklang/_generated/`; `make generate` recreates it.
- Run the suite the way CI does:

  ```sh
  PYTHONPATH=src .venv/bin/python -m pytest tests --doctest-glob='*.md' docs \
    --doctest-modules src/cooklang -q
  make docs   # mkdocs build --strict
  ```

  The docs are doctests, so a changed message or repr fails the suite until
  the docs match.
- Any change to a public name or signature gets a `CHANGELOG.md` entry under
  "Changed" in the same commit.
- Releasing is irreversible (a PyPI version can never be reused): rehearse
  with the Release workflow's dry-run before pushing a `v*` tag.
