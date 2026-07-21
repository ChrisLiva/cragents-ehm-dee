#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2", "pyyaml"]
# ///
"""Render the master instruction template to each target and copy it into place.

Resolves targets.yaml, template/, rendered/ and .last-deployed/ from the cwd.
Never touches git.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from pathlib import Path

import jinja2
import yaml

TEMPLATE_NAME = "instructions.md.j2"

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2


class ConfigError(Exception):
    """targets.yaml is missing, malformed, or the render failed."""


class Target:
    def __init__(self, name: str, output: Path, variables: dict, root: Path):
        self.name = name
        self.output = output
        self.vars = variables
        self.rendered = root / "rendered" / output.name
        self.snapshot = root / ".last-deployed" / f"{name}.md"


def load_targets(root: Path) -> list[Target]:
    config_path = root / "targets.yaml"
    if not config_path.is_file():
        raise ConfigError(f"no targets.yaml in {root} — run from the repo root")

    try:
        raw = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"targets.yaml is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict) or not raw:
        raise ConfigError(
            "targets.yaml must be a non-empty mapping of target name to config"
        )

    targets = []
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise ConfigError(f"target {name!r}: expected a mapping")
        if "output" not in entry:
            raise ConfigError(f"target {name!r}: missing required key 'output'")
        variables = entry.get("vars") or {}
        if not isinstance(variables, dict):
            raise ConfigError(f"target {name!r}: 'vars' must be a mapping")
        output = Path(str(entry["output"])).expanduser()
        targets.append(Target(name, output, {**variables, "target": name}, root))
    return targets


def render(root: Path, target: Target) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(root / "template"),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )
    try:
        template = env.get_template(TEMPLATE_NAME)
    except jinja2.TemplateNotFound as exc:
        raise ConfigError(f"no template/{TEMPLATE_NAME} in {root}") from exc
    try:
        return template.render(**target.vars)
    except jinja2.UndefinedError as exc:
        raise ConfigError(f"target {target.name!r}: render failed: {exc}") from exc


def diff(before: str, after: str, from_label: str, to_label: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=from_label,
        tofile=to_label,
    )
    return "".join(lines)


def read(path: Path) -> str | None:
    return path.read_text() if path.is_file() else None


def adopt(targets: list[Target]) -> int:
    for target in targets:
        current = read(target.output)
        if current is None:
            print(f"{target.name}: no file at {target.output} — nothing to adopt")
            continue
        target.snapshot.parent.mkdir(parents=True, exist_ok=True)
        target.snapshot.write_text(current)
        print(f"{target.name}: adopted {target.output} as the drift baseline")
    return EXIT_OK


def classify(target: Target, new: str) -> tuple[str, str]:
    """Return (state, drift_diff) for a target against its snapshot and destination.

    States: 'no-file', 'no-snapshot', 'drifted', 'pending', 'clean'.
    """
    current = read(target.output)
    if current is None:
        return "no-file", ""
    snapshot = read(target.snapshot)
    if snapshot is None:
        return "no-snapshot", ""
    if snapshot != current:
        return "drifted", diff(
            snapshot,
            current,
            f"{target.name} (last deployed)",
            f"{target.name} (on disk)",
        )
    return ("clean" if current == new else "pending"), ""


def dry_run(targets: list[Target], renders: dict[str, str]) -> int:
    for target in targets:
        new = renders[target.name]
        state, drift_diff = classify(target, new)
        if state == "drifted":
            print(f"{target.name}: DRIFTED — sync would refuse\n{drift_diff}")
        elif state == "no-snapshot":
            print(
                f"{target.name}: no drift baseline — sync would refuse "
                f"(run --adopt to bless {target.output}, or --force)"
            )
        elif state == "no-file":
            print(f"{target.name}: would create {target.output}")
        elif state == "pending":
            print(
                f"{target.name}: PENDING\n"
                + diff(
                    read(target.output),
                    new,
                    f"{target.name} (on disk)",
                    f"{target.name} (new render)",
                )
            )
        else:
            print(f"{target.name}: up to date")
    return EXIT_OK


def deploy(target: Target, new: str) -> None:
    target.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(target.rendered, target.output)
    target.snapshot.parent.mkdir(parents=True, exist_ok=True)
    target.snapshot.write_text(new)


def sync(targets: list[Target], renders: dict[str, str], force: bool) -> int:
    refused = False
    for target in targets:
        new = renders[target.name]
        state, drift_diff = classify(target, new)

        if state in ("drifted", "no-snapshot") and not force:
            if state == "drifted":
                print(
                    f"{target.name}: REFUSED — {target.output} drifted from its baseline"
                )
                print(drift_diff, end="")
                print(
                    "back-port the edit into template/ by hand, or re-run with --force"
                )
            else:
                print(
                    f"{target.name}: REFUSED — no drift baseline for {target.output}\n"
                    "run --adopt to bless the current file, or --force to overwrite it"
                )
            refused = True
            continue

        if force and state == "drifted":
            print(f"{target.name}: --force, discarding this drift:")
            print(drift_diff, end="")

        if state == "clean":
            print(f"{target.name}: up to date")
            continue

        deploy(target, new)
        verb = "created" if state == "no-file" else "updated"
        print(f"{target.name}: {verb} {target.output}")

    return EXIT_REFUSED if refused else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the instruction template to each target and copy it into place."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--adopt",
        action="store_true",
        help="bless each destination's current content as its drift baseline; write nothing else",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="report what sync would do; write nothing",
    )
    mode.add_argument(
        "--force",
        action="store_true",
        help="overwrite drifted destinations, printing the diff",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    try:
        targets = load_targets(root)
        if args.adopt:
            return adopt(targets)
        renders = {t.name: render(root, t) for t in targets}
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.dry_run:
        return dry_run(targets, renders)

    for target in targets:
        target.rendered.parent.mkdir(parents=True, exist_ok=True)
        target.rendered.write_text(renders[target.name])

    return sync(targets, renders, args.force)


if __name__ == "__main__":
    sys.exit(main())
