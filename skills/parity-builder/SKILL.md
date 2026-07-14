---
name: parity-builder
description: Use when building or porting a surface, page, module, or feature FROM a prototype or design source of truth - "port the X page from the prototype", "build module N to match the proto", net-new screens where a runnable/readable prototype exists and testers will compare the build against it leaf by leaf. NOT for fixing tickets on an existing surface (ship) and NOT for verifying an already-built surface (parity-sweep).
---

# parity-builder

## Overview

Builds a surface to **leaf-level parity** with its prototype by making the
prototype's exhaustive leaf inventory the SPEC before any code is written,
and refusing to call a leaf done without an implementation pointer and a
verdict.

**The failure this prevents (validated baseline):** builds ported from a
prototype "by looking at it" ship as **leaner cuts** - internally correct,
visibly similar, missing the prototype's richness (columns inside expanders,
revealed states, drill-down links, per-cell routes). Testers then file the
missing leaves one ticket at a time. Proof: a blind prototype-parity audit
(module-audit, lens 2) independently rediscovered **3/3** of a tester's
just-filed bugs - all pure parity gaps - on a module an 89-agent correctness
audit had already passed. Correct-but-leaner is the default outcome of
building from a glance; this skill exists to make it impossible.

**Shared machinery (reuse by PATH - never copy):**
- Cartographer prompt: `~/.claude/skills/parity-sweep/subagents/prototype-cartographer.md`
  (dispatch as a READ-ONLY agent; its reveal-recursion + loop-until-dry rules
  are the spec-completeness guarantee).
- Per-leaf artifact format + verdict taxonomy: `~/.claude/skills/parity-sweep/SKILL.md`
  (one `parity/<surface>.yaml` entry per leaf).
- Proto-capture cache: `<project>/parity/proto-cache/<surface>/`, keyed by the
  proto commit with the dirty-tree guard (see parity-sweep) - a surface
  cartographed here needs no re-cartography in the finishing sweep.

## Flow

1. **Cartograph the prototype surface FIRST** (or load a clean-key proto
   cache). The leaf inventory IS the spec. No implementation code before the
   inventory exists - the written story may be thinner than the prototype;
   the prototype is the richer spec, trust it.
2. **Plan from the inventory.** Group leaves into components/routes; for each
   leaf that needs data, check the backend serves it (cross-repo contract
   check, the way module-audit pairs frontend surfaces with backend
   contracts). Backend gaps become explicit work items or `BACKEND-GATED`
   leaves - never silent drops. If the `trajectory-kb` MCP is available,
   `query_trajectory({ surface })` for this surface's history before planning -
   a prior build's `what_failed` (a parity gap that came back as a ticket, a
   backend contract that 404'd at runtime) is spec input you'd otherwise
   rediscover the hard way.

   Then, BEFORE implementing any leaf, plan the fan-out with the `fanout`
   skill (file-disjoint parallel vs shared-file serial clusters) and tag each leaf's model tier by RISK - top-tier
   for the project's high-risk leaves, cheap only for mechanical
   fully-specified leaves (the project skill supplies the risk-markers; see
   ship's batching section).
3. **Implement leaf-by-leaf in a worktree.** As each leaf lands, record an
   implementation pointer (`impl: file:line`) on its artifact entry. Fan out
   subagents ONLY on disjoint files, per ship's batching rule,
   and demand its subagent output contract (`file:line - claim - evidence`,
   `totals:`) - you review diffs, run gates, and commit yourself.

   For any leaf that adds a backend endpoint, add its client-side wiring (proxy /
   route handler, generated client) in the SAME integration pass and run the
   project's cross-repo contract check before opening the PR - a new endpoint with
   no client wiring 404s at runtime. Ship via the PR + CI-green gate
   (ship step 7), never direct-push.
4. **Self-verify runtime leaves as they're built** with parity-sweep's scoped
   mode: drive the running app to the leaf, assert by VALUE, cover each
   state behind a toggle/expander. Catching a divergent leaf while its code
   is open is 10x cheaper than after the surface "looks done".
5. **Finish with a parity-sweep over the built surface(s)** - full
   discipline (per-leaf verdicts + browser evidence; the proto side comes
   from the shared cache), scoped to what was built, writing verdicts onto
   the SAME artifact the build maintained. At close-out, if `trajectory-kb` is
   available, `append_trajectory({ repo, surface, outcome, files, what_worked,
   what_failed })` - `outcome: "fixed"` when the sweep passes - with any parity
   gap you hit (and how you closed it) in `what_failed`, so the next port of a
   sibling surface inherits it.

## Completion gate

A surface is "built" only when, in `parity/<surface>.yaml`:
- **100% of leaves** carry an implementation pointer AND a verdict;
- **every interactive/runtime leaf** carries browser evidence;
- **for a multi-step workflow: EVERY step exists, the flow ADVANCES Step-1 -> terminal on SEEDED data, and the terminal action persists.** A multi-step workflow is ONE build unit - never a per-field or single-step slice. A half-built wizard (the M5 Return-Payment "stuck at Step 1, Steps 2-7 absent" miss) is NOT built even if Step 1's leaves all carry pointers;
- **the surface is EXERCISABLE**: realistic seed data exists for every path incl. failure branches (returned/declined/over-limit/blocked) and the prototype's example count - seed it as part of the build (the backend's `seed_*` command / equivalent). An un-seedable surface cannot be sweep-verified and ships as a tester's seed-ticket;
- `EXTRA` (build exceeds proto) is noted, `BACKEND-GATED` and `SCOPED-OUT`
  leaves are listed with reasons - nothing is dropped silently.

Coverage is a number, not a claim. "All the important parts are done" with
leaves missing pointers is NOT done - the unpointed leaf is where the
tester's ticket comes from.

## Failure modes (red flags - STOP)

| Rationalization | Reality |
|---|---|
| "I can see the proto, I'll just build it" | A glance ships the leaner cut. Inventory first - it IS the spec. |
| "Cartography is overkill for this small page" | The 3/3 rediscovered bugs were on 'simple' surfaces. Small pages have revealed states too. |
| "I'll inventory afterwards to check my work" | Inventory-after grades your own homework against your own memory. Spec precedes code. |
| "Leaf's done - I know where I implemented it" | No `impl: file:line` on the artifact = not done. Memory is not a pointer. |
| "It renders fine, skip the browser pass" | Behind-a-click leaves are only proven by driving them (parity-sweep G1). |
| "The user story covers it" | The prototype is the richer spec - stories omit leaves the proto has. |
| "95% of leaves are done, close it out" | The remaining 5% are exactly the tickets testers will file. 100% or it's open. |
| "Built Step 1 + the fields, the rest of the wizard is similar" | A multi-step workflow is ONE unit: build every step + the Step-1 -> terminal progression + the cross-step persistence, and drive it end-to-end. "Stuck at Step 1" was the M5 wave's #1 blocker. |
| "The surface renders, the queue's just empty for now" | An un-seeded surface cannot be verified and IS a tester ticket waiting. Seed every path (incl. failure branches + the proto's example count) as part of the build. |
| "The proto does X differently, I'll just match it" | If the build deliberately diverges (real backend vs proto mock, richer status set) that's a CONFLICT, not a gap - keep the app, NOTE it, and let the USER decide. Build only MISSING/DIVERGENT gaps; never silently down-build to a leaner/mock proto. |

## Related

- `parity-sweep` - verification sibling; source of the shared cartographer,
  artifact format, verdict taxonomy, and proto-cache.
- `fanout` - plan the leaf fan-out from file-disjointness + risk tiering.
- `trajectory-kb` (MCP) - surface history: query prior build/parity traps at planning, append the sweep outcome at close-out.
- `ship` - ticket-driven fixes on EXISTING surfaces; its
  batching rule + subagent output contract govern this skill's fan-out.
- `module-audit` - the cross-repo contract-check pattern step 2 borrows,
  and the lens-2 evidence behind this skill's baseline.
- `superpowers:writing-plans` - for multi-surface efforts, plan the surface
  sequence there; this skill governs each surface's build.
