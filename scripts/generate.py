#!/usr/bin/env python3
"""Build the upstream cooklang-bindings cdylib and generate its Python bindings.

This is a *code generation* step, not a build of hand-written glue: everything
under src/cooklang_rs/_generated/ comes straight out of `uniffi-bindgen` run
against the pinned upstream crate in vendor/cooklang-rs. Nothing here patches,
vendors or reimplements parser logic.

Run from the repo root:  python scripts/generate.py
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "vendor" / "cooklang-rs"
BINDINGS = UPSTREAM / "bindings"
OUT = ROOT / "src" / "cooklang_rs" / "_generated"

# Base name of the upstream cdylib, per bindings/Cargo.toml `name`.
LIB_STEM = "cooklang_bindings"


def shared_library_name() -> str:
    if sys.platform == "darwin":
        return f"lib{LIB_STEM}.dylib"
    if sys.platform.startswith("win"):
        return f"{LIB_STEM}.dll"
    return f"lib{LIB_STEM}.so"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        help="Rust target triple to build for (defaults to the host target). "
        "uniffi-bindgen reads the built library, so cross-compiling here is "
        "only safe when the host can load the result.",
    )
    args = parser.parse_args()

    if not (BINDINGS / "Cargo.toml").exists():
        sys.exit(
            "vendor/cooklang-rs is empty. Run:\n"
            "    git submodule update --init --recursive"
        )

    build = ["cargo", "build", "--release"]
    if args.target:
        build += ["--target", args.target]
    run(build, cwd=BINDINGS)

    target_dir = UPSTREAM / "target"
    lib_dir = target_dir / args.target / "release" if args.target else target_dir / "release"
    lib_path = lib_dir / shared_library_name()
    if not lib_path.exists():
        sys.exit(f"expected library not found: {lib_path}")

    OUT.mkdir(parents=True, exist_ok=True)

    # Drop any library left behind by a build for another platform. Without
    # this, generating on macOS and then in a Linux container leaves both a
    # .dylib and a .so in place and the wheel ships the pair.
    for stale in (*OUT.glob("*.so"), *OUT.glob("*.dylib"), *OUT.glob("*.dll")):
        print(f"removing stale {stale.name}")
        stale.unlink()
    run(
        [
            "cargo",
            "run",
            "--quiet",
            "--features=uniffi/cli",
            "--bin",
            "uniffi-bindgen",
            "generate",
            "--config",
            str(BINDINGS / "uniffi.toml"),
            "--library",
            str(lib_path),
            "--language",
            "python",
            "--out-dir",
            str(OUT),
        ],
        cwd=BINDINGS,
    )

    shutil.copy2(lib_path, OUT / lib_path.name)

    generated = OUT / f"{LIB_STEM}.py"
    if not generated.exists():
        sys.exit(f"uniffi-bindgen produced no {generated.name}")

    print(f"\nGenerated {generated.relative_to(ROOT)}")
    print(f"Copied    {(OUT / lib_path.name).relative_to(ROOT)}")
    print(f"Host      {platform.platform()} / {platform.machine()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
