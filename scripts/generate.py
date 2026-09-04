#!/usr/bin/env python3
"""Build the upstream cooklang-bindings cdylib and generate its Python bindings.

This is a *code generation* step, not a build of hand-written glue: everything
under src/cooklang/_generated/ comes straight out of `uniffi-bindgen` run
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
OUT = ROOT / "src" / "cooklang" / "_generated"

# Base name of the upstream cdylib, per bindings/Cargo.toml `name`.
LIB_STEM = "cooklang_bindings"


def shared_library_name() -> str:
    if sys.platform == "darwin":
        return f"lib{LIB_STEM}.dylib"
    if sys.platform.startswith("win"):
        return f"{LIB_STEM}.dll"
    return f"lib{LIB_STEM}.so"


def host_target() -> str:
    """The Rust target triple for this machine, per `rustc -vV`."""
    out = subprocess.run(
        ["rustc", "--version", "--verbose"], capture_output=True, text=True, check=True
    ).stdout
    for line in out.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    sys.exit("could not determine the host target triple from `rustc -vV`")


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        help="Rust target triple to build for (defaults to this host's triple). "
        "uniffi-bindgen reads the built library, so cross-compiling here is "
        "only safe when the host can load the result.",
    )
    args = parser.parse_args()

    if not (BINDINGS / "Cargo.toml").exists():
        sys.exit(
            "vendor/cooklang-rs is empty. Run:\n"
            "    git submodule update --init --recursive"
        )

    # The target triple is always passed explicitly, even for a plain host
    # build. Without it, cargo puts the release cdylib and the debug
    # uniffi-bindgen binary in the same target/ tree, and library-mode bindgen
    # then silently generates nothing -- exiting 0 and writing no file. With a
    # triple, host and target artifacts live in separate trees and it works.
    # Upstream's own build-swift.sh always passes --target for the same reason.
    target = args.target or host_target()

    # Upstream's root Cargo.toml sets `[profile.release] strip = true`. On ELF
    # that strips .symtab, which is where uniffi-bindgen's library mode reads
    # the UNIFFI_META_* symbols from, so on Linux it finds no components and
    # generates nothing -- while exiting 0. (.dynsym survives, so the library
    # itself still loads and works, which is what made this so quiet.) Mach-O
    # keeps its exported symbols through the same setting, which is why macOS
    # was unaffected.
    #
    # Overridden here rather than by patching the vendored crate, so upstream
    # stays byte-for-byte unmodified.
    run(
        [
            "cargo",
            "build",
            "--release",
            "--target",
            target,
            "--config",
            "profile.release.strip=false",
        ],
        cwd=BINDINGS,
    )

    lib_dir = UPSTREAM / "target" / target / "release"
    lib_path = lib_dir / shared_library_name()
    if not lib_path.exists():
        sys.exit(f"expected library not found: {lib_path}")

    OUT.mkdir(parents=True, exist_ok=True)

    # Clear everything a previous run produced, on any platform, before
    # generating. Two reasons:
    #
    #   * a library from another platform would be packaged alongside this
    #     one, shipping a wheel with a library it can never load;
    #   * leaving the previous cooklang_bindings.py in place lets a failed
    #     generation look like a successful one. uniffi-bindgen exits 0 when
    #     it generates nothing, so a stale file is indistinguishable from a
    #     fresh one -- which is exactly how a broken Linux build went
    #     unnoticed while producing working wheels, because the .py left by a
    #     macOS run got packaged instead.
    stale_files = [
        *OUT.glob("*.so"),
        *OUT.glob("*.dylib"),
        *OUT.glob("*.dll"),
        *OUT.glob(f"{LIB_STEM}.py"),
    ]
    for stale in stale_files:
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
        # uniffi-bindgen exits 0 even when it generates nothing, so this check
        # is the only thing standing between a silent failure and a wheel with
        # no bindings in it. Print enough to diagnose it from a CI log.
        print("\nuniffi-bindgen exited 0 but generated nothing.", file=sys.stderr)
        print(f"  library:  {lib_path} ({lib_path.stat().st_size} bytes)", file=sys.stderr)
        print(f"  out-dir:  {OUT}", file=sys.stderr)
        print(f"  contains: {sorted(p.name for p in OUT.iterdir())}", file=sys.stderr)
        sys.exit(f"uniffi-bindgen produced no {generated.name}")

    print(f"\nGenerated {generated.relative_to(ROOT)}")
    print(f"Copied    {(OUT / lib_path.name).relative_to(ROOT)}")
    print(f"Target    {target}")
    print(f"Host      {platform.platform()} / {platform.machine()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
