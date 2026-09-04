PYTHON ?= python3.14
export MACOSX_DEPLOYMENT_TARGET ?= 11.0

.PHONY: help bootstrap generate test wheel wheel-linux docs docs-serve clean distclean

help:
	@echo "bootstrap    fetch the pinned upstream submodule"
	@echo "generate     build the Rust cdylib and generate the Python bindings"
	@echo "test         run the test suite against the working tree"
	@echo "wheel        build a wheel for this machine"
	@echo "wheel-linux  build the manylinux x86_64 wheel via Docker"
	@echo "docs         build the documentation site into build/site"
	@echo "docs-serve   serve the documentation with live reload"
	@echo "clean        remove build output, keep the cargo target dir"
	@echo "distclean    also remove the cargo target dir"

bootstrap:
	git submodule update --init --recursive

generate: bootstrap
	$(PYTHON) scripts/generate.py

test: generate
	PYTHONPATH=src $(PYTHON) -m pytest tests -q

wheel: generate
	rm -rf build dist
	$(PYTHON) -m build --wheel

wheel-linux:
	./scripts/build-manylinux.sh

clean:
	rm -rf build dist wheelhouse .pytest_cache
	rm -f src/cooklang/_generated/cooklang_bindings.py
	rm -f src/cooklang/_generated/*.so src/cooklang/_generated/*.dylib
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

distclean: clean
	rm -rf vendor/cooklang-rs/target .cargo-container .rustup-container

# The docs build does NOT depend on `generate`: mkdocstrings reads
# src/cooklang statically with Griffe and never imports the package, so no
# Rust toolchain or generated cdylib is needed. The runnable examples in the
# docs do need one -- run `make generate` first if you want to check those.
#
# Everything lives under build/, which is already gitignored and removed by
# `make clean`.
DOCS_VENV ?= build/docs-venv

$(DOCS_VENV)/bin/mkdocs: docs/requirements.txt
	uv venv --quiet $(DOCS_VENV)
	VIRTUAL_ENV=$(DOCS_VENV) uv pip install --quiet -r docs/requirements.txt
	@touch $@

docs: $(DOCS_VENV)/bin/mkdocs
	$(DOCS_VENV)/bin/mkdocs build --strict

docs-serve: $(DOCS_VENV)/bin/mkdocs
	$(DOCS_VENV)/bin/mkdocs serve
