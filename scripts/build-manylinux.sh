#!/usr/bin/env bash
# Build the linux x86_64 manylinux wheel inside the official manylinux image.
#
# This is the same recipe CI runs (.github/workflows/wheels.yml), kept here so
# it can be reproduced locally. On an arm64 host it runs under emulation, which
# is slow but correct.
#
# Usage: scripts/build-manylinux.sh
# Output: wheelhouse/cooklang_rs-*-py3-none-manylinux_*_x86_64.whl

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="quay.io/pypa/manylinux_2_28_x86_64"
PYTHON="/opt/python/cp314-cp314/bin/python"

mkdir -p "$ROOT/wheelhouse"

docker run --rm --platform linux/amd64 \
  -v "$ROOT":/work \
  -w /work \
  -e CARGO_HOME=/work/.cargo-container \
  -e RUSTUP_HOME=/work/.rustup-container \
  -e HOME=/tmp \
  --user "$(id -u):$(id -g)" \
  "$IMAGE" bash -euxo pipefail -c "
    export PATH=/work/.cargo-container/bin:\$PATH
    if ! command -v cargo >/dev/null; then
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain stable
    fi

    $PYTHON scripts/generate.py --target x86_64-unknown-linux-gnu

    $PYTHON -m pip install --quiet --upgrade pip build auditwheel
    rm -rf build dist
    $PYTHON -m build --wheel

    auditwheel repair dist/*.whl -w wheelhouse/
    $PYTHON -m pip install --quiet wheelhouse/*.whl pytest
    cd /tmp && $PYTHON -m pytest /work/tests -q
  "

echo
echo "Built:"
ls -la "$ROOT/wheelhouse"
