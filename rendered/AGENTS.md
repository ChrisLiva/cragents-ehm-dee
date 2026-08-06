# AGENTS.md

User-level preferences for coding agents.

## Working Principles

**Facts vs. decisions.** A *fact* can be found by exploring the environment — the codebase, installed tools, a command's output — so look it up and confirm it rather than asking the user, and act only on facts you've verified. Quick lookups inline; bigger sweeps and large generated reports go to a read-only subagent. A *decision* is the user's: a trade-off, priority, product choice, hard-to-reverse action, or scope change — anything with more than one defensible answer. Put each one to the user and wait — one question at a time, numbered concrete options, your recommendation marked. A choice with an obvious conventional default isn't a decision: proceed and state it.

**Try the cheap experiment first.** When unsure how a tool or CLI behaves, run it once or read `--help` before crawling docs — and never pipe canned answers into an interactive CLI. Match investigation depth to the task: reach for the direct attempt before fanning out audits or deep research.

**Simplicity first.** Build only what was requested; an abstraction earns its place at its second use. Before hand-rolling anything, check in order: existing helper/pattern/constant in this codebase (no new magic strings) → stdlib → native platform feature → already-installed dependency → a few lines of custom code. Never simplify away trust-boundary validation, data-loss handling, security, or accessibility.

**Surgical changes.** Touch only what the request requires; remove imports/variables/functions your change orphaned. Comments describe current state only — never history ("formerly X") or process references.

**Goal-driven execution.** Turn tasks into verifiable goals with a check per step. Deliver closed work: if you'd end with "one thing to note…" or a risk list, resolve those items before declaring done. Report the commit SHA when you commit.

**Subagents.** Default to parallel subagents for multi-task execution — and if you say you'll spawn subagents, spawn them. GPT-5.6-Sol for all subagent work, planning and review included; GPT-5.6-Terra for mechanical tasks (bulk renames, sweeps, collation).

## Git

Trunk-based: commit and merge to main locally; push only when asked — commit and push are separately authorized. Delete merged branches and worktrees. Gitignore generated artifacts (reports, snapshots).

## Bug Fixing

Fix at the root: grep callers and fix once at the shared chokepoint, not just the reported path. Suggest a design change that would eliminate the bug class alongside the direct fix. For runtime/UI bugs, verify the fix in the running app, not just the test suite.

## Testing

Test observable behavior, not implementation: "if this code were rewritten in another language, which tests would confirm it still behaves the same?"

## Linting, Formatting, Type Checking

After a series of code changes, run the project's lint, format, and type-check tools using its preferred method, and report the results.
