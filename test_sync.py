"""Behavior tests for sync.py.

Every test drives the real script as a subprocess against a throwaway repo in a
pytest tmp dir, with destinations inside that tmp dir too. Nothing here imports
the script, and nothing touches the real ~/.claude or ~/.codex.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SYNC = Path(__file__).parent / "sync.py"

TEMPLATE_V1 = "# {{ title }}\n\nHello, {{ audience }}.\n"
TEMPLATE_V2 = "# {{ title }}\n\nHello again, {{ audience }}.\n"

# home branch renders identically to TEMPLATE_V1, work branch is terse
TEMPLATE_PROFILED = (
    "# {{ title }}\n\n"
    "{% if work %}\n"
    "Terse, {{ audience }}.\n"
    "{% else %}\n"
    "Hello, {{ audience }}.\n"
    "{% endif %}\n"
)

CLAUDE_V1 = "# CLAUDE.md\n\nHello, Claude Code agents.\n"
CODEX_V1 = "# AGENTS.md\n\nHello, coding agents.\n"
CLAUDE_V2 = "# CLAUDE.md\n\nHello again, Claude Code agents.\n"
CODEX_V2 = "# AGENTS.md\n\nHello again, coding agents.\n"
CLAUDE_WORK = "# CLAUDE.md\n\nTerse, Claude Code agents.\n"
CODEX_WORK = "# AGENTS.md\n\nTerse, coding agents.\n"


class Repo:
    """A throwaway sync.py repo with both destinations inside the tmp dir."""

    def __init__(self, root: Path):
        self.root = root
        self.claude_dest = root / "dest" / "CLAUDE.md"
        self.codex_dest = root / "dest" / "AGENTS.md"

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SYNC), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_template(self, body: str) -> None:
        (self.root / "template" / "instructions.md.j2").write_text(body)

    def rendered(self, name: str) -> Path:
        return self.root / "rendered" / name

    def rendered_work(self, name: str) -> Path:
        return self.root / "rendered" / "work" / name

    def snapshot(self, name: str) -> Path:
        return self.root / ".last-deployed" / f"{name}.md"


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    (tmp_path / "template").mkdir()
    (tmp_path / "dest").mkdir()
    r.write_template(TEMPLATE_V1)
    (tmp_path / "targets.yaml").write_text(
        "claude:\n"
        f"  output: {r.claude_dest}\n"
        "  vars:\n"
        "    title: CLAUDE.md\n"
        "    audience: Claude Code agents\n"
        "codex:\n"
        f"  output: {r.codex_dest}\n"
        "  vars:\n"
        "    title: AGENTS.md\n"
        "    audience: coding agents\n"
    )
    return r


@pytest.fixture
def seeded(repo: Repo) -> Repo:
    """A repo whose destinations exist, are adopted, and are fully synced."""
    repo.claude_dest.write_text(CLAUDE_V1)
    repo.codex_dest.write_text(CODEX_V1)
    assert repo.run("--adopt").returncode == 0
    assert repo.run().returncode == 0
    return repo


def test_no_snapshot_refuses_and_hints_adopt(repo: Repo):
    repo.claude_dest.write_text("hand-written\n")
    repo.codex_dest.write_text("hand-written\n")

    result = repo.run()

    assert result.returncode == 1
    assert "--adopt" in result.stdout
    assert repo.claude_dest.read_text() == "hand-written\n"
    assert repo.codex_dest.read_text() == "hand-written\n"
    # rendered/ is written even when every copy is refused
    assert repo.rendered("CLAUDE.md").read_text() == CLAUDE_V1
    assert repo.rendered("AGENTS.md").read_text() == CODEX_V1


def test_adopt_snapshots_destinations_and_writes_nothing_else(repo: Repo):
    repo.claude_dest.write_text("current claude\n")
    repo.codex_dest.write_text("current codex\n")

    result = repo.run("--adopt")

    assert result.returncode == 0
    assert repo.snapshot("claude").read_text() == "current claude\n"
    assert repo.snapshot("codex").read_text() == "current codex\n"
    assert repo.claude_dest.read_text() == "current claude\n"
    assert repo.codex_dest.read_text() == "current codex\n"
    assert not repo.rendered("CLAUDE.md").exists()


def test_clean_sync_copies_and_stamps(repo: Repo):
    repo.claude_dest.write_text("old\n")
    repo.codex_dest.write_text("old\n")
    repo.run("--adopt")

    result = repo.run()

    assert result.returncode == 0
    assert repo.claude_dest.read_text() == CLAUDE_V1
    assert repo.codex_dest.read_text() == CODEX_V1
    assert repo.snapshot("claude").read_text() == CLAUDE_V1
    assert repo.snapshot("codex").read_text() == CODEX_V1


def test_second_sync_is_a_noop(seeded: Repo):
    before = {p: p.read_text() for p in (seeded.claude_dest, seeded.codex_dest)}

    result = seeded.run()

    assert result.returncode == 0
    assert "up to date" in result.stdout
    assert {p: p.read_text() for p in before} == before


def test_dry_run_on_pending_change_writes_nothing(seeded: Repo):
    seeded.write_template(TEMPLATE_V2)

    result = seeded.run("--dry-run")

    assert result.returncode == 0
    assert "PENDING" in result.stdout
    assert "-Hello, Claude Code agents." in result.stdout
    assert "+Hello again, Claude Code agents." in result.stdout
    # nothing written: destinations, rendered/ and snapshots all still v1
    assert seeded.claude_dest.read_text() == CLAUDE_V1
    assert seeded.rendered("CLAUDE.md").read_text() == CLAUDE_V1
    assert seeded.snapshot("claude").read_text() == CLAUDE_V1


def test_hand_edited_destination_is_refused_with_its_diff(seeded: Repo):
    seeded.claude_dest.write_text(CLAUDE_V1 + "\nHand-added memory line.\n")

    result = seeded.run()

    assert result.returncode == 1
    assert "+Hand-added memory line." in result.stdout
    assert "Hand-added memory line." in seeded.claude_dest.read_text()
    assert seeded.snapshot("claude").read_text() == CLAUDE_V1


def test_back_ported_edit_is_accepted_not_refused(repo: Repo):
    """The recovery path the refusal message advertises has to actually work."""
    repo.claude_dest.write_text(CLAUDE_V1)
    repo.codex_dest.write_text(CODEX_V1)
    repo.run("--adopt")
    # a hand-edit at the destination, then back-ported into the template
    repo.claude_dest.write_text(CLAUDE_V2)
    repo.write_template(TEMPLATE_V2)

    result = repo.run()

    assert result.returncode == 0
    assert "REFUSED" not in result.stdout
    assert repo.claude_dest.read_text() == CLAUDE_V2
    assert repo.snapshot("claude").read_text() == CLAUDE_V2
    # and the other target still gets its update
    assert repo.codex_dest.read_text() == CODEX_V2


def test_force_without_a_baseline_shows_what_it_discards(repo: Repo):
    precious = "hand-maintained instructions\n"
    repo.claude_dest.write_text(precious)
    repo.codex_dest.write_text(precious)

    result = repo.run("--force")

    assert result.returncode == 0
    assert "-hand-maintained instructions" in result.stdout
    assert repo.claude_dest.read_text() == CLAUDE_V1
    assert repo.snapshot("claude").read_text() == CLAUDE_V1


def test_write_failure_does_not_block_the_other_target(seeded: Repo):
    seeded.write_template(TEMPLATE_V2)
    # an unwritable destination: a directory where the file should be
    seeded.claude_dest.unlink()
    seeded.claude_dest.mkdir()

    result = seeded.run()

    assert result.returncode == 2
    assert "FAILED" in result.stderr
    assert seeded.codex_dest.read_text() == CODEX_V2
    assert seeded.snapshot("codex").read_text() == CODEX_V2


def test_force_discards_drift_overwrites_and_restamps(seeded: Repo):
    seeded.claude_dest.write_text(CLAUDE_V1 + "\nHand-added memory line.\n")
    seeded.write_template(TEMPLATE_V2)

    result = seeded.run("--force")

    assert result.returncode == 0
    assert "+Hand-added memory line." in result.stdout
    assert seeded.claude_dest.read_text() == CLAUDE_V2
    assert seeded.snapshot("claude").read_text() == CLAUDE_V2


def test_targets_are_independent(seeded: Repo):
    seeded.claude_dest.write_text("drifted by hand\n")
    seeded.write_template(TEMPLATE_V2)

    result = seeded.run()

    assert result.returncode == 1
    # the drifted target is untouched, the clean one still gets its update
    assert seeded.claude_dest.read_text() == "drifted by hand\n"
    assert seeded.codex_dest.read_text() == CODEX_V2
    assert seeded.snapshot("codex").read_text() == CODEX_V2


def test_rollback_does_not_false_flag_as_drift(seeded: Repo):
    seeded.write_template(TEMPLATE_V2)
    assert seeded.run().returncode == 0
    assert seeded.claude_dest.read_text() == CLAUDE_V2

    # `git checkout <ref> -- template/ rendered/` restores the v1 content. The
    # template is what actually drives the rollback; rendered/ is regenerated.
    seeded.write_template(TEMPLATE_V1)
    seeded.rendered("CLAUDE.md").write_text("stale, must be regenerated\n")

    result = seeded.run()

    assert result.returncode == 0
    assert "REFUSED" not in result.stdout
    assert seeded.claude_dest.read_text() == CLAUDE_V1
    assert seeded.codex_dest.read_text() == CODEX_V1
    assert seeded.rendered("CLAUDE.md").read_text() == CLAUDE_V1
    assert seeded.snapshot("claude").read_text() == CLAUDE_V1


def test_missing_template_var_fails_the_render(seeded: Repo):
    seeded.write_template(TEMPLATE_V1 + "\n{{ nonexistent_var }}\n")

    result = seeded.run()

    assert result.returncode == 2
    assert "nonexistent_var" in result.stderr
    assert seeded.claude_dest.read_text() == CLAUDE_V1
    assert seeded.rendered("CLAUDE.md").read_text() == CLAUDE_V1


def test_work_flag_deploys_the_work_profile(seeded: Repo):
    seeded.write_template(TEMPLATE_PROFILED)

    result = seeded.run("--work")

    assert result.returncode == 0
    assert seeded.claude_dest.read_text() == CLAUDE_WORK
    assert seeded.codex_dest.read_text() == CODEX_WORK
    assert seeded.snapshot("claude").read_text() == CLAUDE_WORK
    assert seeded.rendered_work("CLAUDE.md").read_text() == CLAUDE_WORK
    # the full-prose render is still written alongside
    assert seeded.rendered("CLAUDE.md").read_text() == CLAUDE_V1


def test_both_profiles_rendered_on_a_plain_run(seeded: Repo):
    seeded.write_template(TEMPLATE_PROFILED)

    result = seeded.run()

    assert result.returncode == 0
    # home branch matches what is deployed, so the destination is untouched
    assert "up to date" in result.stdout
    assert seeded.claude_dest.read_text() == CLAUDE_V1
    assert seeded.rendered_work("CLAUDE.md").read_text() == CLAUDE_WORK
    assert seeded.rendered_work("AGENTS.md").read_text() == CODEX_WORK


def test_switching_profiles_is_pending_not_drift(seeded: Repo):
    """A plain run after --work deploys the full-prose profile back (and vice
    versa) — a profile switch is a pending update, never a drift refusal."""
    seeded.write_template(TEMPLATE_PROFILED)
    assert seeded.run("--work").returncode == 0

    result = seeded.run()

    assert result.returncode == 0
    assert "REFUSED" not in result.stdout
    assert seeded.claude_dest.read_text() == CLAUDE_V1
    assert seeded.snapshot("claude").read_text() == CLAUDE_V1


def test_work_profile_still_guards_drift(seeded: Repo):
    seeded.write_template(TEMPLATE_PROFILED)
    assert seeded.run("--work").returncode == 0
    seeded.claude_dest.write_text(CLAUDE_WORK + "\nHand-added memory line.\n")

    result = seeded.run("--work")

    assert result.returncode == 1
    assert "+Hand-added memory line." in result.stdout
    assert "Hand-added memory line." in seeded.claude_dest.read_text()
    assert seeded.snapshot("claude").read_text() == CLAUDE_WORK


def test_template_without_profiles_ignores_work_flag(seeded: Repo):
    result = seeded.run("--work")

    assert result.returncode == 0
    assert "up to date" in result.stdout
    assert seeded.claude_dest.read_text() == CLAUDE_V1


def test_missing_targets_yaml_is_a_clear_error(tmp_path: Path):
    result = subprocess.run(
        [str(SYNC)], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode == 2
    assert "targets.yaml" in result.stderr
