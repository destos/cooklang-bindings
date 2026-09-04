# Upstream issues to file

Three gaps found while building these bindings. Both belong upstream rather than
here, because working around either locally would mean patching the vendored
crate — which would break the guarantee that what this package exposes is
exactly what upstream supports.

**Neither has been filed yet.** Drafts below, ready to submit.

---

## 1. UniFFI Python target: records used as map keys are unhashable

**Where:** `mozilla/uniffi-rs` (the Python backend), not `cooklang/cooklang-rs`.

**Status in this project:** worked around in `src/cooklang/_ffi.py`, covered by
`TestCombineIngredients` so an upstream fix will not break us silently.

> ### Python bindings: `Record` used as a `HashMap` key is unhashable
>
> **Summary**
>
> The Python backend emits records as classes with a generated `__eq__` and no
> `__hash__`. Python then sets `__hash__ = None`, making instances unhashable.
> Any exported function returning a `HashMap<SomeRecord, V>` therefore fails at
> runtime when the generated converter builds the dict.
>
> **Reproducer**
>
> A record used as a map key:
>
> ```rust
> #[derive(uniffi::Record, Debug, Clone, Hash, Eq, PartialEq)]
> pub struct GroupedQuantityKey {
>     pub name: String,
>     pub unit_type: QuantityType,
> }
>
> pub type GroupedQuantity = HashMap<GroupedQuantityKey, Value>;
>
> #[uniffi::export]
> pub fn combine_ingredients(ingredients: &[Ingredient]) -> HashMap<String, GroupedQuantity> { ... }
> ```
>
> Calling it from Python:
>
> ```
> TypeError: cannot use 'GroupedQuantityKey' as a dict key (unhashable type: 'GroupedQuantityKey')
> ```
>
> **Expected**
>
> The Rust type derives `Hash + Eq`, so the generated Python should be hashable
> too. Swift and Kotlin are unaffected — their generated record types get
> structural hashing for free — so this is Python-target specific.
>
> **Suggested fix**
>
> Emit a `__hash__` alongside the generated `__eq__` for record classes,
> hashing the same fields `__eq__` compares. A three-line monkeypatch on the
> generated class is enough to confirm it resolves the problem:
>
> ```python
> GroupedQuantityKey.__hash__ = lambda self: hash((self.name, self.unit_type))
> ```
>
> **Versions:** uniffi 0.28.3, Python 3.14, real-world case in
> `cooklang/cooklang-rs` (crate `cooklang-bindings` 0.18.7).

---

## 2. cooklang-rs bindings: no way to enable syntax extensions

**Where:** `cooklang/cooklang-rs`.

**Status in this project:** not worked around. Documented in
[`docs/extensions.md`](docs/extensions.md); the bindings are canonical-only.

> ### `parse_recipe` hardcodes `canonical()`, so bindings cannot use the extensions
>
> **Summary**
>
> `bindings/src/lib.rs` builds the parser as:
>
> ```rust
> let parser = cooklang::CooklangParser::canonical();
> ```
>
> `canonical()` is `Extensions::empty()` + `Converter::empty()`, and
> `parse_recipe` takes no parser-mode argument. No other exported function
> offers one either, so every consumer of the bindings — Swift, Kotlin and
> Python alike — is locked out of the extension superset that `extensions.md`
> documents, and out of unit conversion.
>
> **Why this is more than a missing feature**
>
> Cooklang is forgiving: unrecognised syntax is read as text rather than
> rejected. Extended markup is therefore absorbed into the parsed data instead
> of raising, which is difficult for a consumer to detect:
>
> | Input | Parsed as |
> | --- | --- |
> | `@onion\|onions{1}` | ingredient named `onion\|onions` |
> | `@&onion{1}` | ingredient named `&onion` |
> | `@?onion{1}` | ingredient named `?onion` |
> | `@flour{10 kg}` | text amount `"10 kg"`, not `10` + `kg` |
> | `@onion{1-2}` | text amount `"1-2"`, not a range |
>
> An ingredient named `&onion` is corrupt data, and nothing signals it. Any
> app ingesting recipes from the wider ecosystem will hit this.
>
> Separately, `Converter::empty()` means `combine_ingredients` cannot convert
> between compatible units, so `1%kg` and `500%g` stay as two entries.
>
> **Suggested fix**
>
> An additional exported function, leaving the existing one untouched for
> backwards compatibility:
>
> ```rust
> #[uniffi::export]
> pub fn parse_recipe_with_extensions(
>     input: String,
>     scaling_factor: f64,
>     extensions: u32,
> ) -> Arc<CooklangRecipe>
> ```
>
> Exposing `Extensions` as a UniFFI bitflags-style enum, or accepting a simple
> mode enum (`Canonical` / `Compat` / `Extended`), would both work. The model
> types carry no assumption about which mode produced them, so nothing else
> needs to change.
>
> Happy to open a PR if the approach sounds right.
>
> **Versions:** `cooklang-bindings` 0.18.7, uniffi 0.28.3.


---

## 3. cooklang-rs: `strip = true` silently breaks binding generation on Linux

**Where:** `cooklang/cooklang-rs`.

**Status in this project:** worked around in `scripts/generate.py`, which builds
with `--config profile.release.strip=false`. Verified in CI on Linux and macOS.

> ### `[profile.release] strip = true` makes library-mode bindgen generate nothing on Linux
>
> **Summary**
>
> The root `Cargo.toml` sets:
>
> ```toml
> [profile.release]
> codegen-units = 1
> strip = true
> ```
>
> On ELF targets this strips `.symtab`, which is where `uniffi-bindgen`'s
> library mode reads the `UNIFFI_META_*` symbols from. It therefore finds zero
> components and generates **no bindings at all** — while exiting 0.
>
> `.dynsym` survives stripping, so the built cdylib loads and works normally.
> That combination makes the failure very quiet: a working library that bindgen
> reads as empty, and a generator that reports success.
>
> **Reproducer** (clean `ubuntu:24.04`, stable Rust 1.98.1):
>
> ```console
> $ cargo build --release --target x86_64-unknown-linux-gnu
> $ nm -D target/x86_64-unknown-linux-gnu/release/libcooklang_bindings.so | grep -c UNIFFI_META
> 62
> $ nm target/x86_64-unknown-linux-gnu/release/libcooklang_bindings.so | grep -c UNIFFI_META
> 0
> $ cargo run --features=uniffi/cli --bin uniffi-bindgen -- print-repr <lib>
> []
> $ cargo run --features=uniffi/cli --bin uniffi-bindgen -- generate --library <lib> --language python --out-dir out
> $ ls out          # empty, exit code was 0
> ```
>
> macOS is unaffected: Mach-O keeps the exported symbols through the same
> setting, so `build-swift.sh` works and the problem only appears on Linux.
> This is not Python-specific — Kotlin generation on Linux fails the same way.
>
> **Suggested fix**
>
> Either drop `strip = true`, or set it only for profiles that do not feed
> `uniffi-bindgen`, or document that binding generation needs
> `--config profile.release.strip=false`. A one-line workaround for consumers:
>
> ```sh
> cargo build --release --config profile.release.strip=false
> ```
>
> It may also be worth having `uniffi-bindgen` warn rather than exit 0 when a
> library yields zero components, since that is indistinguishable from success
> — but that belongs in `mozilla/uniffi-rs`.
>
> **Versions:** `cooklang-bindings` 0.18.7, uniffi 0.28.3, cargo 1.98.1.
