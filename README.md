# cragents-ehm-dee

One Jinja template renders both user-level agent instruction files, so an edit
can't reach `~/.claude/CLAUDE.md` and silently miss `~/.codex/AGENTS.md`.

```
template/instructions.md.j2   the master instructions
targets.yaml                  per-target output path + template vars
rendered/                     committed render of each target
.last-deployed/               drift baselines (gitignored, local machine state)
sync.py                       render -> drift-guard -> copy
```

## Usage

Run everything from the repo root — all paths resolve from the cwd.

```sh
./sync.py             # render, guard, copy to both destinations
./sync.py --dry-run   # report drifted / pending / up to date; write nothing
./sync.py --adopt     # bless each destination's current content as its baseline
./sync.py --force     # print the drift being discarded, then overwrite
```

Editing instructions: change `template/instructions.md.j2` (or a var in
`targets.yaml`), run `./sync.py --dry-run` to read the diff, then `./sync.py`.
Commit `rendered/` alongside the template so history shows what each
destination was rendered as — note that `rendered/` is refreshed on every run,
including one where a copy was refused, so commit after a run that succeeded.

Exit codes: `0` clean, `1` at least one target refused, `2` config, render, or
write error.

## Drift guard

`.last-deployed/<target>.md` is a full copy of what `sync` last wrote. If a
destination no longer matches its baseline someone hand-edited it (an in-session
rewrite, a `#`-memory append), so `sync` refuses that target and prints the
diff. Back-port the edit into the template by hand, then sync again — once the
render matches what's on disk the guard accepts it and re-stamps the baseline.
Or discard the edit with `--force`. Targets are independent: a drifted
CLAUDE.md never blocks AGENTS.md.

`--force` applies to every target in the run, so back-port first when only one
target drifted rather than forcing past both.

The baseline lives outside git on purpose. Comparing against `rendered/` at HEAD
would make every rollback look like drift.

## Rollback

```sh
git checkout <ref> -- template/ targets.yaml rendered/
./sync.py
```

The destinations still match their baselines, so this applies cleanly with no
drift flag. `template/` and `targets.yaml` are what drive the rollback —
`rendered/` is regenerated from them on every run, so restoring it alone
changes nothing.

## Scope

User-level files only. Project repos keep the existing convention of a
`CLAUDE.md` → `AGENTS.md` symlink; nothing here touches them.

`sync.py` never runs git — no commits, tags, or pushes, and nothing runs
automatically. Drift is caught at the next `sync`, not live.
