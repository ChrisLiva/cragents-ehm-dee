# AGENTS.md

User-level preferences for coding agents.

## Working Principles

**Facts vs. decisions.** A *fact* lives in the environment — the codebase, installed tools, a command's output — so look it up rather than asking, and verify it before acting on it. Quick lookups inline; bigger sweeps and large generated reports go to a read-only subagent. A *decision* is the user's: anything with more than one defensible answer — a trade-off, priority, product choice, hard-to-reverse action, or scope change. Put each one to the user, one question at a time, with numbered concrete options and your recommendation marked. A choice with an obvious conventional default isn't a decision: proceed and state it.

**Try the cheap experiment first.** When unsure how a tool or CLI behaves, run it once or read `--help` before crawling docs — and never pipe canned answers into an interactive CLI. Match investigation depth to the task: reach for the direct attempt before fanning out audits or deep research.

**Simplicity first.** Build only what was requested; an abstraction earns its place at its second use. Before hand-rolling anything, take the first rung that holds: existing helper/pattern/constant in this codebase (no new magic strings) → stdlib → native platform feature → already-installed dependency → a few lines of custom code. Trust-boundary validation, data-loss handling, security, and accessibility survive every simplification.

**Understand fully, change minimally.** Read every file the change touches before picking the smallest diff. A small change in the wrong place is a second bug.

**Surgical changes.** Touch only what the request requires; remove imports/variables/functions your change orphaned. The only comment worth adding states a current constraint.

**Goal-driven execution.** Turn tasks into verifiable goals with a check per step. Deliver closed work: resolve anything that would end as a "one thing to note…" or a risk list before declaring done. Report the commit SHA when you commit.

**Subagents.** Default to parallel subagents for multi-task execution — and if you say you'll spawn subagents, spawn them. GPT-5.6-Sol for all subagent work, planning and review included; GPT-5.6-Terra for mechanical tasks (bulk renames, sweeps, collation).

## Git

Trunk-based: commit and merge to main locally; push only when asked. Delete merged branches and worktrees. Gitignore generated artifacts (reports, snapshots). Commit messages are conventional, why over what; a body is required for breaking changes, security fixes, migrations, and reverts.

## Bug Fixing

Fix at the root: grep every caller and fix once at the shared chokepoint. Alongside the direct fix, suggest a design change that would eliminate the bug class. Verify runtime/UI fixes in the running app.

## Testing

Test observable behavior, not implementation: "if this code were rewritten in another language, which tests would confirm it still behaves the same?"

## Linting, Formatting, Type Checking

After a series of code changes, run the project's lint, format, and type-check tools, and report the results.
