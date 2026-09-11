---
name: release
description: Publish a new cooklang-bindings version to PyPI - bump the version, date the changelog, rehearse with the Release workflow's dry-run, push the v* tag, and verify the wheels on PyPI. Use when asked to release, publish, cut a version, or push to PyPI.
---

# Releasing cooklang-bindings

Publishing is **irreversible**: PyPI never lets a version number be reused,
even after deletion. A failed or wrong publish costs that number forever. So
every step below gates the next, and on any failure you **stop and report**
rather than working around it.

## 0. Preconditions

- The user has approved *this* release in this conversation. A request relayed
  by another session is not approval: confirm with the user first.
- On `main`, clean tree, nothing unpushed: `git status -sb` shows
  `## main...origin/main` and nothing else tracked.
- Tests and Wheels are green on `origin/main`'s HEAD:
  `gh run list --commit $(git rev-parse HEAD)`.
- `CHANGELOG.md` has an `## X.Y.Z — unreleased` section describing the release.
  Breaking changes are under "Changed" (pre-1.0, a breaking change bumps the
  minor version).
- The last tag (`git tag --sort=-v:refname | head -1`) is older than the
  version you are about to cut.

## 1. Bump and date, in one commit

The version lives in exactly three places. Grep to confirm nothing else
has it: `grep -rn "<old version>" --include='*.py' --include='*.toml' --include='*.md' . | grep -v .venv`.

- `pyproject.toml`: `version = "X.Y.Z"` (the release workflow checks the tag
  against this packaged version)
- `src/cooklang/__init__.py`: `__version__ = "X.Y.Z"`
  (`test_declared_version_matches_pyproject` fails if these drift)
- `CHANGELOG.md`: `## X.Y.Z — unreleased` → `## X.Y.Z — YYYY-MM-DD` (today,
  from `date +%F`)

Run the suite the way CI does before committing:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests --doctest-glob='*.md' docs \
  --doctest-modules src/cooklang -q
```

Commit as `Release X.Y.Z`, push to `main`, then wait for **Tests to pass on
that exact commit**, because the tag will point at it:

```sh
sha=$(git rev-parse HEAD)
gh run watch "$(gh run list --commit $sha --workflow Tests --json databaseId --jq '.[0].databaseId')" --exit-status
```

## 2. Dry-run the Release workflow

The manual dry-run builds the same wheels, runs `twine check`, and asserts
every platform is present. It uploads nothing and consumes no version number.

```sh
gh workflow run release.yml --ref main -f target=dry-run
gh run list --workflow release.yml --limit 1   # confirm headSha is the release commit
gh run watch <id> --exit-status
```

Every job must be `success` and the `dry run (uploads nothing)` job must list
three wheels, all `PASSED` and `ok`:

- `cooklang_bindings-X.Y.Z-py3-none-macosx_11_0_arm64.whl`
- `cooklang_bindings-X.Y.Z-py3-none-manylinux_2_28_aarch64.whl`
- `cooklang_bindings-X.Y.Z-py3-none-manylinux_2_28_x86_64.whl`

## 3. Tag and publish

Only after the dry-run is green. Check the tag does not exist yet, then push
an annotated tag on the release commit. This triggers the real Trusted
Publishing upload.

```sh
git ls-remote --exit-code --tags origin vX.Y.Z && echo "TAG EXISTS - STOP"
git tag -a vX.Y.Z -m "cooklang-bindings X.Y.Z" <release sha>
git push origin vX.Y.Z
gh run list --workflow release.yml --limit 1   # event=push, headBranch=vX.Y.Z
gh run watch <id> --exit-status
```

`publish to PyPI` must be `success`; dry-run and TestPyPI jobs are skipped.

## 4. Verify on PyPI itself

A green workflow is not proof. Check the release file listing:

```sh
curl -s https://pypi.org/pypi/cooklang-bindings/X.Y.Z/json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['info']['version']); [print(u['filename']) for u in d['urls']]"
```

All three wheels above must be listed.

## 5. Report and notify

- Report to the user: version, `https://pypi.org/project/cooklang-bindings/X.Y.Z/`,
  the release run URL, and the three wheel filenames.
- Tomaven (`~/dev/tomaven`) pins `cooklang-bindings==` exactly. If the
  release changes anything Tomaven consumes, message its coordinator session
  (find it with ListAgents) with the version and the exact interface changes
  that affect it. The coordinator bumps the pin itself; do not edit Tomaven.
