PYTHON ?= python3.14
export MACOSX_DEPLOYMENT_TARGET ?= 11.0

.PHONY: help bootstrap generate test wheel wheel-linux clean distclean

help:
	@echo "bootstrap    fetch the pinned upstream submodule"
	@echo "generate     build the Rust cdylib and generate the Python bindings"
	@echo "test         run the test suite against the working tree"
	@echo "wheel        build a wheel for this machine"
	@echo "wheel-linux  build the manylinux x86_64 wheel via Docker"
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
	rm -f src/cooklang_rs/_generated/cooklang_bindings.py
	rm -f src/cooklang_rs/_generated/*.so src/cooklang_rs/_generated/*.dylib
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

distclean: clean
	rm -rf vendor/cooklang-rs/target .cargo-container .rustup-container
