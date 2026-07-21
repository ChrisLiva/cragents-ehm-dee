# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single-purpose tool that renders one Jinja template into **both** user-level agent
instruction files, so an edit can't land in `~/.claude/CLAUDE.md` and silently miss
`~/.codex/AGENTS.md`. Read `README.md` for the user-facing contract (usage, drift
guard, rollback semantics) before changing behavior — it is the spec.

**Do not confuse this file with `rendered/CLAUDE.md`.** This file is repo guidance
(root `CLAUDE.md` is a symlink to this `AGENTS.md`, per the convention in the README);
`rendered/` holds generated artifacts destined for `~/.claude/` and `~/.codex/`, and
is overwritten on every `sync.py` run. To change what agents are told, edit
`template/instructions.md.j2` — never `rendered/`.

## Commands

```sh
.venv/bin/pytest -q                     # full suite
.venv/bin/pytest -q -k force_discards   # single test by name substring
uvx ruff check . && uvx ruff format .   # lint / format (ruff is not on PATH)
./sync.py --dry-run                     # safe: writes nothing
```

`uv run pytest` does **not** work — `pyproject.toml` has only a `[tool.pyright]`
table, no `[project]`. Use the committed `.venv`, or
`uvx --with jinja2 --with pyyaml pytest`.

`sync.py` is a PEP 723 self-contained script (`uv run --script` shebang) that
declares its own `jinja2`/`pyyaml` deps, so it runs standalone regardless of `.venv`.

## Architecture

`sync.py` is one file, and its whole design is the pipeline in `main()`:

1. `load_targets(root)` — parse `targets.yaml` into `Target` objects. Every path is
   resolved from **cwd**, not from the script location; run from the repo root.
   Each target carries its destination, its `rendered/<basename>` file, and its
   `.last-deployed/<name>.md` drift baseline.
2. `render()` — Jinja with `StrictUndefined`, so a template var missing from
   `targets.yaml` is a hard `ConfigError`, not a silent blank.
3. `classify(target, new)` — the core state machine, and the place to start when
   changing behavior. Returns one of `no-file`, `no-snapshot`, `drifted`,
   `converged`, `pending`, `clean` from the three-way comparison of *baseline* vs
   *destination on disk* vs *new render*. `dry_run()` and `sync()` are both thin
   dispatchers over these states; add a state here and both must handle it.
4. `deploy()` — copy `rendered/` → destination, then re-stamp the baseline.

Key invariants worth preserving:

- **Targets are independent.** A refusal or write failure on one target must not
  stop the others; `sync()` accumulates `refused`/`failed` flags and continues.
- **The baseline is gitignored on purpose** (`.last-deployed/`). It is local machine
  state; comparing against `rendered/` at HEAD would make every rollback look like drift.
- **`converged`** exists so a hand-edit that was back-ported into the template is
  accepted rather than refused — there is nothing to discard.
- **`sync.py` never runs git** and never runs automatically. Keep it that way.
- Exit codes are part of the contract: `0` clean, `1` a target was refused,
  `2` config/render/write error.

## Tests

`test_sync.py` drives the real `./sync.py` as a **subprocess** against a throwaway
repo in `tmp_path`, with destinations inside that tmp dir. Nothing imports the
script and nothing touches the real `~/.claude` / `~/.codex` — preserve both
properties. Tests assert on stdout wording and exit codes, so user-facing message
changes will (correctly) break them.
