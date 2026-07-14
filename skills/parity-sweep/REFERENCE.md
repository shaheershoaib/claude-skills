# parity-sweep — design spec (2026-06-08)

A standalone, project-agnostic skill that catches **granular, interaction-level UI parity
gaps** between a source-of-truth prototype and a built app — the class of detail (e.g. a
customer-row dropdown that reveals a clickable per-account list in the prototype but a flat
layout in the app) that source-diff audits repeatedly miss.

## 1. Problem it solves

Prior parity passes diffed **source code** and **summarized** surfaces. That structurally misses:
- **Behind-a-click state** — what a dropdown/expander/tab/modal/hover/row-click *reveals*, which is conditionally rendered and glossed by a top-down read.
- **Leaf attributes** — is a cell a link? where does it route? what is the exact column set *inside* an expander? — averaged out by section-level rollups.
- **Coverage was unprovable** — no per-element checklist with a verdict, so "we looked at it" was indistinguishable from "we checked every leaf," and unexamined nooks passed silently.
- **Browser side-by-side was deferred/representative** — the one method that definitively catches behind-a-click gaps (driving both UIs) was skipped.

**Core principle:** interaction- and leaf-level parity cannot be caught by reading code alone.
It requires (a) enumerating every interactive affordance *and its revealed state* for the
source-of-truth, and (b) **driving both running UIs through that enumeration and diffing the
revealed states**. Code-reading builds the checklist; the live browser is the ground-truth
catch-net. Neither alone suffices. This is inherently multi-agent and multi-pass.

## 2. Scope & non-goals

- **In:** detection-only. Produces a coverage artifact + findings. Project-agnostic; standalone.
- **Out:** fixing the gaps (a separate fix-pass), and any project-specific config file (there is
  none — see Reusability). The prototype is always treated as the source of truth.
- **Reusable with no adapter:** project specifics arrive as runtime inputs + are auto-discovered;
  the robustness lives in the method, not config.

## 3. Invocation & inputs

`parity-sweep <prototype-location> <app-location + running-URL> [scope: a surface/area]`

- **prototype-location**: path to the source-of-truth UI (e.g. a prototype repo's pages dir) and/or a running URL.
- **app-location**: the built app's code path + its running URL (local or deployed).
- **scope** (optional): limit to one surface/area; default = all discovered surfaces.
- Auth: the skill **pauses and asks the user** when it hits a login/password wall on either running app; it never fabricates credentials. (Prohibited-actions rules apply.)
- If a required input is missing, the skill asks once, up front.

## 4. Method (pipeline)

`discover` → for each surface: `cartograph(prototype)` → `diff(app)` → `drive(browser, both)` → `verify` → `reconcile`.

1. **Discover surfaces.** Read the prototype's router/nav/pages to enumerate every surface; map
   each to the app counterpart by route + label, confirming against the app's running nav. Output:
   the surface list (proto path/route ↔ app path/route), persisted.
2. **Prototype Cartographer (per surface).** Produce an **exhaustive, leaf-granular interaction
   inventory** of the source of truth. **Reveal-recursion rule (non-negotiable):** an interactive
   element (row, dropdown, expander, tab, button, menu, hover, link, cell) is **not inventoried
   until what it reveals is captured to the leaf** — the revealed content's elements, columns,
   copy, and whether each revealed sub-element is itself interactive and where it routes. Recurse
   into modals/tabs/expansions. **Loop-until-dry:** re-run until a pass surfaces no new element or
   revealed-state. Output: the surface's inventory (the checklist), every node with a stable id.
3. **App Diff (per surface).** Inventory the app surface the same way; diff against the prototype
   checklist. Output: candidate verdict per leaf (provisional, from code).
4. **Browser Parity Driver (per surface).** Open **both running UIs**; for every inventory leaf,
   perform its interaction on both (click row/dropdown/tab/modal/link, hover), capture
   screenshot + DOM snapshot of each revealed state on both sides, and stamp the **ground-truth
   verdict**. It works the inventory checklist top to bottom; it does not free-roam. Captures
   evidence paths per leaf.
5. **Adversarial Verifier (per surface).** Re-check each non-PARITY leaf against prototype + app +
   evidence; kill false positives; finalize classification.
6. **Reconcile (run level).** Dedup cross-surface, produce the consolidated findings list + the
   coverage roll-up.

All cartographer/diff/verifier agents are **read-only**; the driver only interacts with running
UIs (no code mutation). Surfaces fan out in parallel; one surface = one pipeline.

## 5. Subagent roster (standalone prompts shipped in the skill)

| Agent | Input | Output | Tools |
|---|---|---|---|
| **discoverer** | proto + app locations | surface map (proto↔app) | Read/Grep/Glob (+ browser to read app nav) |
| **prototype-cartographer** | one prototype surface | leaf-granular inventory (checklist) w/ reveal-recursion + loop-until-dry | Read/Grep/Glob |
| **app-diff-cartographer** | the prototype inventory + app surface | app inventory + provisional per-leaf verdict | Read/Grep/Glob |
| **browser-parity-driver** | inventory + both running URLs | per-leaf ground-truth verdict + screenshot/DOM evidence | browser MCP (chrome-devtools / playwright) + Read |
| **parity-verifier** | findings + evidence | confirmed/killed + classification | Read/Grep/Glob (read-only) |

Orchestration is a deterministic pipeline (the skill's recipe), fanning surfaces out in parallel
and capping concurrency; per-surface artifacts make it resumable.

## 6. Coverage artifact (makes completeness provable — the missing piece)

One structured file per surface (`parity/<surface>.yaml` or similar), every leaf carrying:

```
- id: customer-ledger.row.expand.account-list.account-link
  kind: link            # static | row | dropdown | expander | tab | modal | button | hover | link | cell
  label: "Account row -> account detail"
  proto:  { revealed: "per-account list; each row links", route: "/account/:id", columns: [...] }
  app:    { revealed: "flat text list; not linked", route: null, columns: [...] }
  verdict: DIVERGENT
  evidence: { proto_shot: "...", app_shot: "...", proto_src: "file:line", app_src: "file:line" }
```

**Completion gate:** a surface is "audited" only when **100% of its leaves have a verdict** AND
**every interactive leaf has browser evidence**. A run-level roll-up reports surfaces × leaves ×
verdict counts — coverage is a number, not a claim. This is the antidote to "representative."

## 7. Verdict taxonomy

`PARITY` · `DIVERGENT` (present but different) · `MISSING` (in proto, absent in app) ·
`EXTRA` (app exceeds proto — noted, not a defect) · `CONFLICT` (proto contradicts a spec/story —
defer, don't auto-flag as gap) · `BACKEND-GATED` (UI present, data/endpoint absent) ·
`SCOPED-OUT` (explicitly out of scope per product).

## 8. Reusability mechanics (no committed adapter)

- **Surface discovery** is derived from the prototype's own routing/nav, not a hand-written map.
- **proto↔app mapping** uses route/label heuristics, confirmed against the app's live nav.
- All subagent prompts are **project-agnostic** — they reference "the prototype" / "the app" by the
  runtime inputs, never project specifics.
- The only per-run inputs are the invocation args (locations/URLs) + interactive auth. Nothing is
  committed per project. New project = run the skill with its locations; no code changes.

## 9. Resumability & cost (honest)

- **Resumable:** per-surface artifacts; a re-run skips any surface already 100%-verdicted. Survives
  interruption (spend limits, auth timeouts, crashes).
- **Cost:** exhaustive browser-driving of every interactive element across many surfaces is dozens
  of driver agents over a long run and **requires the user's login** when staging auth is hit. This
  is the deliberate price of "cannot miss details"; the skill front-loads the cheap code-inventory
  so the expensive browser pass only confirms a known checklist.

## 10. Standalone vs other skills

Built standalone (no hard skill dependency). It *uses* whatever browser MCP is available
(chrome-devtools-mcp / playwright) as a capability for the driver. It composes naturally **before**
a separate fix-pass (which would use `superpowers:using-git-worktrees` +
`verification-before-completion`), but the audit skill requires none of them to run.

## 11. Validation plan (how we prove it works)

Run `parity-sweep` on your project (prototype ↔ deployed app):
1. **Start with a surface where you already know a divergence exists** — it MUST catch + log that
   known miss (e.g. a per-row dropdown / clickable-list divergence). If it doesn't, the method is
   wrong; fix before scaling.
2. Sweep the remaining surfaces; feed confirmed findings into the parity backlog.
3. Misses caught here are added to the build backlog before resuming the backend pass.

## 12. Success criteria

- The Customer Ledger dropdown divergence is caught + logged with proto/app evidence.
- Every audited surface has a 100%-verdicted coverage artifact with browser evidence on interactive leaves.
- A second developer can run the skill on a *different* prototype↔app pair with only the invocation
  args — no edits to the skill.
