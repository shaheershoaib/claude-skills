---
name: pre-commit
description: >-
  Run the project's REAL quality gates before committing or claiming work
  done: discover the actual gate commands (CLAUDE.md, project skills, memory,
  package.json/Makefile/CI config), run them all, plus any custom project
  gates. Optional deploy-gate mode for pre-deployment validation (build, env
  vars, dependency vulnerabilities). Use before any commit, before claiming
  "green", or when asked to "run the gates" / "pre-commit" / "pre-deploy".
---

# Pre-commit gates

Gate = the project's actual commands, all green, before commit. Never a
generic checklist when a real one exists.

**Fail-closed.** A gate counts as PASSED only when it actually ran to completion
and you read GREEN in its fresh output. A gate that was skipped, couldn't run
(missing command, unset env var, wrong directory), errored before reaching its
assertions, timed out, or whose output you did not actually read is a FAIL - not
an "assumed pass". Resolve it or mark the run BLOCKED. The absence of a red is
not the presence of a green; "no test passed unless it ran green" is the rule.

Where CI enforces a required check on the PR, CI is the AUTHORITATIVE gate and
this local run is the fast pre-check - run locally for speed, but the PR does not
merge until the required check is green (never admin-bypass it).

## Step 1 - Discover the project's gates (in priority order)

1. **Project skill / CLAUDE.md / auto-memory** - many projects document exact
   gate commands (e.g. `npx tsc --noEmit && npx next lint && npx jest`, or a
   Django `manage.py test --noinput` with a no-`--parallel` rule).
2. **CI config** (`.github/workflows/*`, etc.) - what CI runs IS the gate.
3. **Manifest scripts** - `package.json` (`typecheck`/`lint`/`test`),
   `Makefile`, `pyproject.toml`, pre-commit hooks config.
4. Found nothing? Ask, or fall back to the stack's standard trio
   (typecheck + lint + tests) and say you guessed.

**Custom gates count.** Projects accrete non-obvious gates - e.g. ASCII-only
changed lines (`git diff <base>..HEAD | grep -E '^\+' | grep -P
'[^\x00-\x7F]'` must be empty), migration checks (`makemigrations --check`),
schema drift, bundle budgets. Check project docs/memory for these; they fail
CI just as hard as a type error.

Cross-repo contract: when a diff adds/changes a backend endpoint, the client-side
wiring that reaches it (proxy / route handler, generated client, typed SDK) must
exist or calls 404/break at runtime. Mechanize this for your stack (the project
skill names the command) and run it whenever a diff touches the API surface.

**Mechanize prose gates.** A gate that exists only as a documented one-liner
someone re-types each run is a gate that gets skipped, mistyped, or run
against the wrong base. When you meet one, materialize it as a small script
in the repo (`scripts/check-<thing>.sh`), wire it into the gate command
(package.json script, Makefile target, or the project skill's gate line),
and - if CI exists - into CI, so agents, humans, and CI all run the SAME
check. If a convention can be enforced by regex/script, automate it and save
the prose for judgment calls. Flag (don't silently fix) gates that CI claims
to require but every push bypasses - a required check that never blocks is a
single point of failure on whoever runs gates locally.

## Step 2 - Run them ALL

- Run every gate even after the first failure (one pass = full picture).
- Fix and re-run until green. Do not claim green without fresh output
  (`superpowers:verification-before-completion`).
- A gate that errors out BEFORE it reaches its checks (compile error in the test
  harness, missing dep, DB not up) is RED, not "skip and continue" - the suite
  did not pass, it failed to run. Fix the harness, then re-run (fail-closed).
- New/changed test files run as part of the suite, not instead of it - a
  targeted run first is fine for iteration speed, but the full suite gates.

## Step 3 - Qualitative pass (optional, for substantial diffs)

Spawn the standalone `code-auditor` agent on the changed files (obvious bugs,
`any` types, empty catches, debug logging) and/or `test-runner` for an
isolated suite run when the main context is busy. For an independent second
opinion on a risky diff, use `/codex` cross-model review or the built-in
`/code-review`.

## Deploy-gate mode (pre-deploy)

Before a production deployment (not needed for push-to-staging flows where CI
is the gate), spawn in parallel:

| Agent | Focus |
|---|---|
| `deploy-checker` | Production build succeeds, bundle size, prod config |
| `env-validator` | Required env vars present, no secrets in code |
| `dep-auditor` | Vulnerability scan, critically outdated packages |

Any failure = BLOCKED, with the specific blockers listed.

## Output

```markdown
# Gates: PASS / FAIL
- [x] <gate command 1> - pass
- [ ] <gate command 2> - FAIL: <first error>
Verdict: ready to commit / fix first
```
