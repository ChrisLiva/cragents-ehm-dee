# AGENTS.md

User-level preferences for coding agents.

## Working Principles

Aim for the code a careful senior engineer would write. Bias toward caution over speed; for trivial tasks (single file, no new dependencies, no behavior change), skip the ceremony and just do them.

**Answer your own questions first.** Before asking the user something the codebase could tell you ("how does X work," "where is Y handled," "what calls Z"), find out yourself: handle quick lookups you can resolve in one or two reads inline, and delegate anything bigger to a read-only Explore/research subagent so the main context stays clean. Reserve questions for what only the user knows — intent, priorities, preferences, and external context.

**When to ask vs. proceed.** Ask before acting when requirements admit competing interpretations, an action is hard to reverse, the work diverges from an agreed plan (say whether the plan was wrong, ambiguous, or vague; proceed without asking only when the right move is unambiguous), or scope would change — including a modest increase that would materially improve correctness or avoid near-term rework; that trade-off is the user's call. First apply *Answer your own questions first*; otherwise proceed on sensible defaults and state them as you go. Whenever you do ask, include your recommendation.

**Think before coding.** Push back when a request conflicts with these principles or rests on a fact you can't verify.

**Simplicity first.** Write the minimum code that solves the problem: build only what was requested, let an abstraction earn its place at its second use, handle only errors that can actually occur. If 200 lines could be 50, rewrite it. Would a senior engineer call it overcomplicated? Then simplify.

Climb the reuse ladder before writing custom code, stopping at the first rung that holds:
(1) does it need to exist? — skip if speculative;
(2) does a helper, util, type, or pattern already in this codebase do it? reuse it — re-implementing what's a few files over is the most common slop;
(3) stdlib;
(4) native platform feature (`<input type="date">` over a picker lib, CSS over JS, a DB constraint over app code);
(5) an already-installed dependency — never add one for what a few lines do;
(6) one line;
(7) only then the minimum that works. The ladder runs *after* you understand the problem, not instead of it. Never simplify away trust-boundary validation, data-loss handling, security, or accessibility — those are not on the chopping block.

**Surgical changes.** Touch only what the request requires — every changed line should trace to it. Remove imports/variables/functions your changes orphaned. Mention unrelated dead code, but ask before deleting it.

**Goal-driven execution.** Turn tasks into verifiable goals ("fix the bug" → "write a failing test that reproduces it, then make it pass"). For multi-step work, state a brief plan with a verification check per step. Strong success criteria let you work independently; vague ones force constant clarification.

**Subagents.** Use GPT-5.6-Terra-High for exploration and research subagents, GPT-5.6-Luna-High for simple mechanical tasks; let subagents doing work that needs real judgment (planning, review) inherit the session model.

## Bug Fixing

Fix bugs at the root, not the symptom: a report names a symptom, so before editing a function, grep its callers and fix once at the shared chokepoint — a guard in the shared function is a smaller diff than a guard in every caller, and patching only the path the report names leaves sibling callers broken. Then consider whether a design change would eliminate a whole class of future bugs in that area, and suggest it alongside the direct fix.

## Testing

Test observable behavior, not implementation details: "if this code were rewritten in another language, which tests would confirm it still behaves the same?"

Proactively invoke the "tdd" skill when writing tests, to follow best practices and avoid anti-patterns.

## Code Review

Coding agents often oscillate — a fix from one review gets reversed by the next. A careful senior engineer settles the question instead of relitigating it: when you notice oscillation (recent commits reverting the same change), stop and ask how to proceed, with your recommendation, and offer to record the decision in an ADR so future reviews don't reopen it.

## Linting, Formatting, Type Checking

When you finish a series of code changes, run the project's lint, format, and type-check tools when available, using its preferred method and packages.
