---
name: parity-sweep
description: Use when verifying a built UI matches a source-of-truth prototype or design and you cannot afford to miss granular behind-a-click details (dropdowns, expanders, tabs, modals, row-click destinations, cell-level links, revealed lists) - e.g. before sign-off, after porting a prototype, when testers keep filing interaction-level parity gaps, or when prior reviews "looked at it" but missed leaf details.
---

# parity-sweep

## Overview

Parity bugs hide in two places a code-read or a quick look glosses over: the **revealed state** (what a dropdown/expander/tab/modal/hover/row-click shows) and the **leaf attribute** (is this revealed cell a link? where does it route? what is the exact column set *inside* the expander?).

**Core principle:** catch them by (1) enumerating every interactive affordance of the source-of-truth **down to the leaf**, (2) **driving both running UIs through that enumeration and diffing the revealed states**, and (3) recording **a verdict per leaf** so coverage is a number, not a claim. Code-reading builds the checklist; the live browser is the ground-truth catch-net; the per-leaf artifact prevents burial. None of the three is optional.

This is inherently **multi-agent and multi-pass**. There is no cheap shortcut to "never miss a behind-a-click detail."

## Why looking isn't enough (the failure this prevents)

A real miss: a reviewer noted "customer row expands to a per-account view; the app's expansion is structurally different" - tagged it *medium*, and the triage **rolled it up** into a bigger item, **losing the leaf** (in the prototype each revealed account row is a **link into that account**; the app's isn't). It was never browser-confirmed. Result: shipped wrong, filed by a tester later.

The three defenses below each target one part of that failure: **reveal-recursion** (don't lose the leaf), **per-leaf coverage** (don't roll up/bury), **mandatory browser confirmation** (don't ship un-verified).

## When to use

- Verifying a build against a prototype/design that is the source of truth, especially before sign-off or after a port.
- Prior audits keep missing details testers later catch.
- NOT for: greenfield UI with no source-of-truth reference; pure backend; performance/a11y (use dedicated skills).

## Inputs (standalone - no committed config)

Invoke with: the **prototype** source-of-truth (code path and/or running URL), the **app** (code path + running URL), and optionally a single surface to scope. Everything else is discovered. The skill **pauses and asks you** when it hits a login/auth wall on either running app - it never enters credentials itself.

### Scoped mode (single feature/fix, no fan-out)

When verifying ONE fix or feature (e.g. inside a ship run) rather than signing off a surface: skip the multi-agent pipeline and apply the discipline directly - (1) read the prototype source for that feature and extract the expected values/states (badge text, colors, formulas, routes - the proto code is the spec; do not ask for screenshots of it), (2) drive the app's exact flow to the leaf, (3) assert by VALUE (`input.value`, selected option, computed style, rendered number - never placeholder/presence), covering each state behind a toggle/expander (on -> edited -> reverted), (4) confirm the no-regression case on a sibling that should be unchanged, (5) if the fix sits inside a multi-step flow, drive the flow to its TERMINAL action (submit/activate/save) accepting pre-filled defaults - step-local checks miss the state-seam regressions that surface only at the final gate, and (6) when the fix changes a shared PATTERN (control, label, icon placement, mask, color convention), check the parallel surface that implements the same pattern - twins that diverge are a finding even when each looks fine alone. While there, glance at the console for new errors - a render that "works" while logging exceptions is a finding.

### Fanning out a full sweep? The parallelize rule lives in `fanout`

Full mode drives surfaces in parallel (below). The rule for WHICH verification may fan out is NOT a parity-sweep concept (it applies to greenfield and pure-backend verification too, which this skill explicitly does not cover) - it lives in `fanout`'s VERIFY-MODE, the same place the build fan-out is planned: data/by-value reads parallelize (session-less); authed deployed-UI drives serialize on the orchestrator (one authenticated session; a standalone/automation browser is unauthed); the gate-read + judgment never leave the orchestrator. Apply it to the surface-drivers below: a sweep of a LOCAL build can fan browsers out (per-agent seeded login); a sweep of a single authed DEPLOYED session cannot.

## Method (per-surface pipeline)

`discover` -> for each surface: `cartograph(prototype)` -> `diff(app)` -> `drive(browser, both)` -> `verify` -> `reconcile`. Surfaces fan out in parallel. Subagent prompts are in `subagents/` (dispatch each as its own agent):

1. **discoverer** - enumerate prototype surfaces from its router/nav; map each to the app counterpart. (`subagents/discoverer.md`)
2. **prototype-cartographer** - exhaustive leaf-granular interaction inventory of the source of truth. (`subagents/prototype-cartographer.md`)
3. **app-diff-cartographer** - inventory the app surface; diff vs the prototype checklist -> provisional per-leaf verdict. (`subagents/app-diff-cartographer.md`)
4. **browser-parity-driver** - drive BOTH running UIs through every inventory leaf; screenshot+DOM each revealed state; stamp the ground-truth verdict + evidence. (`subagents/browser-parity-driver.md`)
5. **parity-verifier** - adversarially re-check non-PARITY leaves; kill false positives; finalize. (`subagents/parity-verifier.md`)

### The reveal-recursion rule (non-negotiable)

An interactive element (row, dropdown, expander, tab, button, menu, hover, link, cell, **or a workflow Next/Continue/advance control**) is **NOT inventoried until what it reveals is captured to the leaf** - the revealed content's elements, columns, copy, AND for every revealed sub-element: *is it interactive, and where does it route?* Recurse into modals/tabs/expansions **AND through every STEP of a multi-step workflow**: follow Next/Continue/advance from Step 1 to the TERMINAL action, inventorying each step the prototype has and driving the app the WHOLE way. A step the prototype reaches but the app cannot (dead Next / "Validation failed" / "already generated" guard / a missing step) is a **MISSING/DIVERGENT leaf for that step AND every step downstream of it**, plus a top-severity blocker - never "Step 1 looks fine, pass." (This is precisely the M5 Return-Payment miss: the build was stuck at Step 1, so a Step-1-only look passed while Steps 2-7 were absent.) **Loop-until-dry:** re-run the cartographer until a pass adds no new element, revealed-state, or workflow step.

## Coverage artifact + completion gate

One file per surface (`parity/<surface>.yaml`), one entry per leaf:

```yaml
- id: customer-ledger.row.expand.account-row.link
  kind: link        # static|row|dropdown|expander|tab|modal|button|hover|link|cell
  label: "expanded account row -> account detail"
  proto: { revealed: "per-account rows, each links", route: "/account/:id", columns: [name,carrier,premium,policy,outstanding] }
  app:   { revealed: "By Account/By Policy sub-table, not linked", route: null, columns: [invoiced,collected,outstanding] }
  verdict: DIVERGENT
  evidence: { proto_shot, app_shot, proto_src: "file:line", app_src: "file:line" }
```

**A surface is "audited" only when 100% of its leaves carry a verdict AND every interactive leaf has browser evidence AND the surface was actually EXERCISABLE (seeded).** If a surface/queue is empty or sparse (0 rows, or 1 vs the prototype's N), you could not drive its flows - that is an INCOMPLETE sweep and a `seed-gap` finding, NOT a pass: seed it (or flag the seed-gap for a seed pass) and re-drive. A run-level roll-up reports surfaces x leaves x verdicts. Coverage is provable, not asserted.

## Verdict taxonomy

`PARITY` | `DIVERGENT` (present, different) | `MISSING` (in proto, absent in app) | `EXTRA` (app exceeds proto - note, not a defect) | `CONFLICT` (proto contradicts a shipped spec/story, OR the build is deliberately ahead of the proto - real backend vs proto mock, richer status set, etc.) | `BACKEND-GATED` (UI present, data/endpoint absent) | `SCOPED-OUT`.

**Conflicts are a USER decision, never an auto-pick.** When a leaf is CONFLICT, do NOT silently resolve it to either side (do not down-build the app to match a leaner/mock proto, and do not silently keep the app). Keep the app as-is for now, record the conflict on the artifact with both sides stated, and surface the list of conflicts for the user to decide which wins. Only `MISSING`/`DIVERGENT` gaps are built automatically; `CONFLICT` waits on a human call.

## Prototype-capture cache

The prototype side of a sweep is expensive to re-derive and rarely changes
between runs. Cache it: the cartographer's leaf inventory plus the driver's
PROTO-side captures (DOM snapshots, screenshots) are written once to
`<project>/parity/proto-cache/<surface>/`, keyed by the prototype's commit
(`git -C <proto> rev-parse HEAD`).

- **Reuse rule:** when the current proto commit matches the cache key and the
  proto working tree is CLEAN, skip proto-side cartography and driving - load
  the inventory + captures from cache and drive ONLY the app side. App-side
  browser verification stays FULL; the cache never reduces app evidence.
- **Dirty-tree guard:** if `git -C <proto> status --porcelain` is non-empty,
  the proto on disk is not the committed proto - capture fresh and tag the
  cache dir `-dirty`; a `-dirty` cache is never reused across runs. (Not
  hypothetical: the reference prototype has carried uncommitted edits
  mid-cycle.) A non-git prototype keys by a content hash of the surface's
  source files; when in doubt, recapture - a stale proto spec poisons every
  verdict downstream.
- The cache is shared with `parity-builder` (the build-side sibling): a
  surface cartographed for a build run needs no re-cartography when the
  post-build sweep runs, and vice versa.

## Resumability

Per-surface artifacts; a re-run skips any surface already 100%-verdicted.
Survives spend limits, auth timeouts, crashes. Always resume rather than
restart. The proto-cache above extends this across RUNS, not just within
one: any later sweep or builder run on the same surface at the same proto
commit starts with the proto side already captured and re-drives only the
app.

## Common mistakes (red flags - STOP)

| Rationalization | Reality |
|---|---|
| "The table matches, looks the same" | You compared the *visible* row. Expand it - the parity bug is in the revealed state. |
| "Captured the expanded columns, good enough" | Did you record whether each revealed cell is a LINK and where it routes? That's the leaf. |
| "I'll roll these small ones into the big finding" | Rollup buries leaves. Every leaf gets its OWN verdict in the artifact. |
| "Code looks equivalent, skip the browser" | Behind-a-click state is only proven by driving both UIs. No browser evidence = not verified. |
| "Audited the surface" (no per-leaf artifact) | "Audited" = 100% of leaves verdicted + browser evidence on interactive ones. Otherwise it's "glanced at." |
| "Representative sample is enough" | The miss is always in the element you didn't drive. Drive every interactive leaf. |
| "Queue's empty but the page renders - pass it" | An empty/sparse surface proves NOTHING about its flows. It is a `seed-gap` + an incomplete sweep. Seed every path (incl. failure branches) and drive it; never mark a surface audited you could not exercise. |
| "Step 1 renders correctly, the workflow's fine" | You verified one step. Drive Next -> ... -> terminal; a wizard stuck/missing past Step 1 is the #1 tester blocker, and a Step-1 look cannot see it. |

## Reference

Full rationale, subagent contracts, and validation plan: `REFERENCE.md`.

## Related

- `parity-builder` - the build-side sibling: ports a surface FROM the
  prototype to leaf parity, reusing this skill's prototype-cartographer,
  per-leaf artifact format, and proto-cache, then finishes by invoking this
  skill on the built surface.
