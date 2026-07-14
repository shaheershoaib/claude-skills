---
name: ship
description: >-
  The work-set execution loop - the single entry point for landing a set of
  changes end to end under verification guardrails. Any task set, from any
  source: a list of asks in chat ("here are 5 things"), tracker tickets
  (Notion, Jira, GitHub issues, Linear), a plan/handoff/audit document on
  disk - single task or a batch, mixed work types, on any project shape (web
  app, API service, CLI, library). Use for "fix this ticket", "fix these",
  "address the comments on #NN", "the tester reopened X", "run the loop",
  "work the board", or any "make these changes and ship them" request.
  Project facts (repos, branches, verification target, optional ticket board,
  commit identities) come from the project's own skill/CLAUDE.md/memory - this
  skill is the project-agnostic skeleton plus the guardrails that prevent
  false "fixed" claims.
---

# Ship (the work-set loop)

The standard pipeline for turning a WORK-SET - however it arrives: a list of
asks in chat, tracker tickets, a reporter's follow-up comment, a plan/handoff
document on disk - into shipped, verified, closed changes. The mechanical steps
are easy; the guardrails are the point. Every one of them exists because
skipping it has shipped a wrong or unverified "fix" at least once.

**Boundary: `fanout` writes the schedule; ship runs the job.** The planner is a
deterministic tool this loop CALLS at step 0 (clusters/waves/tiers in seconds);
everything that acts - dispatching agents, worktrees, gates, PRs, merges,
verification, close-outs - happens HERE, orchestrator-owned.

**Vocabulary (used throughout):** a WORK-ITEM is one actionable ask, whatever
its source (a ticket, a chat ask, a document line-item). The REPORTER is
whoever's experience defines done for an item: the ticket filer, the user in
chat, the document's author - for a mechanical sweep, the pattern spec itself.
A CLUSTER is a set of items that MUST serialize (shared edited files or one
declared contract - `fanout` computes it). An MSP (minimum shippable
product) is the unit that ships as ONE PR - see "MSPs" below. A LEAF is one
dispatched unit of build work inside an MSP. WAVES are the execution schedule:
everything in a wave runs concurrently; integrate between waves.

**Project facts live elsewhere.** Before running, load the project's facts from
(in order): a project-level skill (e.g. `<project>/.claude/skills/*`), the
project CLAUDE.md, and auto-memory. You need: repo paths + integration
branches, gate commands, commit identity rules, the VERIFICATION TARGET, and -
IF the project has one - the tracker layer (ticket board + status taxonomy).
Two of these are project-SHAPED, never assumptions:
- **The tracker is an EXTENSION, not a requirement**: with no board, tasks
  arrive as text and close out as an evidence-cited report instead of a ticket
  move.
- **The VERIFICATION TARGET is whatever artifact a real user runs**, and every
  "deployed build" in this skill means THAT target: a deployed web build
  (staging URL, browser drive), a released/installed package (build/install
  the artifact FROM the merged sha, run the command), or a service endpoint
  (staging API call). A CLI/library with no deploy is NOT exempt - its target
  is the built artifact at the merged sha; only the observation tool changes
  (run the command / call the endpoint instead of driving a browser).
If a needed fact is missing, ask - do not guess. **Bootstrapping a new project?** Copy
`references/project-facts-template.md` (in this skill's directory) to
`<project>/.claude/skills/<project>-loop/SKILL.md` and fill in the
placeholders - it carries the section skeleton this loop expects, including
the G5 terminal-action and G6 twin-surface hooks.

---

## The guardrails (more important than the steps)

### G0 - Pin the BEFORE-state FIRST; the acceptance observable IS your test
Before touching code, OBSERVE the target surface as it is and capture what you
saw - that observation is the exact thing your by-value check (G1, step 9) must
later show CHANGED. "My change is deployed/live" is NOT verification: your change
being live is not the same as the acceptance observable being true. (Proof: a
"modal cut off" report was read as a vertical footer-clip; a height cap was
built, gated, deployed, and "verified by value" that the cap was applied - all
green - while the real bug was the modal being too NARROW. The wrong axis
shipped; only the reporter caught it.)

G0 has TWO forms - pick by the work-item's shape:
- **REGRESSION / FIX (something is wrong):** reproduce the symptom. The observed
  failure IS the acceptance test; step 9 must show it GONE.
- **ADDITIVE / CHANGE (something new or different is wanted):** observe the
  surface WITHOUT the change (the before-state - same discipline, usually two
  minutes) and pre-register the NEW observable as the acceptance line
  ("Acceptance: a CSV Export button on /customers downloads the filtered
  rows"). "Nothing to reproduce" never means "nothing to pin": the before-state
  capture is what makes the after-check a diff instead of a vibe. A mechanical
  many-site sweep's before-state is the site CENSUS (grep/graph enumeration);
  its acceptance is census-zero plus sampled drives.

This gate is the OBSERVABLE side - pin it so step 9 can re-check it; finding WHY
a bug happens (so the fix addresses the cause, not the symptom) is a SEPARATE
discipline, `superpowers:systematic-debugging` at step 4, which REUSES this same
reproduction. Shorthand: G0 makes you verify the right thing;
systematic-debugging makes you fix the right thing - they share only the
reproduce step, not the job.

The escape hatches below REPLACE a hard rule with judgment, so each is defaulted-
STRICT and STRUCTURED (the skeptical-default shape you use in coupling_review) -
never a free-text afterthought, which is a loophole, not a gate. The litmus: could
someone reading the ticket in six weeks tell, without ambiguity, exactly what WAS and
was NOT verified and why, with a tracked path to close any gap? If not, you have not
implemented the gate.

**(A) Ambiguous ask** ("cut off", "broken", "weird", "thin", "slow", "doesn't
work", "improve X", "make it feel better") - pin the exact observable BEFORE
building: reproduce it, or ask ONE clarifying question. Never infer which
symptom they mean. If the ask stays SUBJECTIVE after that one question, it is
DESIGN work, not a fix: route it to `superpowers:brainstorming` with the
observations you gathered, and its output re-enters the work-set as specified
items (step 0's typing rule). Never enter the build path with an unpinnable
acceptance line.

**(B) Repro-gate: default = REPRODUCE; skipping is the recorded exception.**
- Skipping requires a one-line reason a reviewer can challenge - not a silent call.
- "Obvious enough to skip" = obvious CAUSE + an unambiguous, graphify-confirmed fix
  LOCATION, NOT an obvious-looking symptom. The classic wrong-fix is "looked obvious,
  patched the obvious thing, missed that the real cause was a different surface" (the
  G4 wrong-surface miss graphify exists to catch).
- Reporter/tester-sourced symptom -> repro is MANDATORY, never skipped (same rigor as
  read-the-full-thread / pin-the-exact-flow).
- Skipping end-to-end repro is NOT skipping evidence: a cheap regression/unit test
  that exercises the fixed code path is the substitute.

**(C) Can't reproduce - separate the two flavors; never blur them:**
- PRECONDITION before ANY downgrade - "can't observe" means you EXHAUSTED the available
  automation, NOT that your first method failed. Try the browser MCP against the user's
  LIVE authenticated session first (Claude-in-Chrome on their open tab), then Playwright /
  Chrome DevTools / the preview tools. A surface reachable by clicking a VISIBLE button
  (e.g. "Add Account" -> a 6-step wizard) is OBSERVABLE; shipping it `unverified-reasoned`
  because a grep or a viewport-resize didn't pan out is the escape hatch used as a first
  resort. Real miss: claimed a wizard "can't be driven", shipped unverified - it opened in
  ~6 clicks from the customer page in the user's own browser, and driving it showed the
  fix was correct AND surfaced a requirement-polarity question the static read had hidden.
- Can't OBSERVE (env limit, e.g. a viewport you can't shrink) BUT you have a REAL root
  cause + a test exercising the fixed path -> ship ONLY as a STRUCTURED DOWNGRADE,
  never a clean "fixed": a distinct status `unverified-reasoned`, a required reason,
  ROUTED to whoever can observe it (in the reporter's thread: "shipped; not
  reproducible in my env, please confirm on retest") + a tracked "verify-when-
  observable" item with a real DISPOSITION: either it lands in a NAMED, QUERYABLE
  destination (a board status / label / field, a saved view, the tester's retest
  queue), OR you surface it explicitly to a human in-session who decides how - or
  whether - to track it. The closed loop is the DECISION, not the medium: an in-chat
  flag counts ONLY if it forces that disposition and you do NOT treat the fix as done
  until the decision is made. A dropped FYI is not tracking - a chat line or a buried
  PR sentence that nobody acts on lets unverified fixes pile up SILENTLY, the exact
  debt this gate exists to surface.
- Can't observe AND no identified cause = guessing -> do NOT ship-as-fixed. Get more
  info from the reporter (repro steps / screenshot), or - only if truly forced - ship
  under a louder, DISTINCT `speculative - no root cause` flag - and HARD-GATE that path, because it is the
  closest thing to a legitimate "ship anyway" and so earns the TIGHTEST leash: NEVER
  silent; on money/auth/contract/migration NEVER without explicit HUMAN sign-off (the
  agent may NOT self-approve it - block and ask); and auto-listed in the SAME named
  destination for follow-up. It is a scarier thing than `unverified-reasoned`; never
  relabel one as the other.
- RISK-GATE the downgrade itself: on high-blast-radius surfaces (money/ledger, auth,
  service/API contract, destructive migration) "can't repro" stays close to a BLOCK or
  demands stronger compensating evidence (more tests, a second reviewer, a
  seeded/staged repro). The easy downgrade is for low-blast-radius ONLY.

**(D) Observation blocked at DIAGNOSIS time -> a code-inference is a HYPOTHESIS,
not a stated fact.** When you cannot drive the live surface, do NOT promote "the
code seems to show X" into "X is true." Two misses in one sitting on one ticket: a
narrow grep -> "this flow has no prospect concept" (false - the user could see the
selector); then "prospect = account_status" (false - tsc proved no such enum value;
the real field was `classification`). Both were inferences ASSERTED as fact about a
surface I could not watch. This is the diagnosis-phase twin of (C) (which governs the
SHIP claim); here the PREMISE is what's unverified. Guard:
- State the inference AS an inference ("from the schema it looks like X; I could not
  drive the UI to confirm"); on anything load-bearing, cross-check it against the
  AUTHORITATIVE definition (the enum / type / schema / contract), not one grep.
- Treat a failing gate as a PREMISE-check, not a nuisance: a tsc "no overlap" or a
  test that contradicts your assumption is REFUTING the diagnosis - stop and
  re-ground, don't just edit until the compiler goes quiet.
- If the premise still isn't confirmable from code, ASK the reporter/user (they can
  observe) before building on it. A cheap question beats a confident wrong build.
- **For a render-shaped symptom (wrong value / wrong label / missing or duplicated
  row), the AUTHORITATIVE source at diagnosis is the LIVE RENDERED build, not the
  enum/type/schema.** The contract can be correct while the bug lives in the render
  path (a mislabel, a branch-ordering short-circuit, a display-mapping collision),
  so reading the code/contract alone "confirms" the wrong conclusion. Drive the
  current deployed surface per (C)'s authed-session precondition and read the actual
  rendered value BEFORE writing the fix. Proof: a missing "Remittable fees" row was
  diagnosed from the schema as a pure data gap (fix = seed the data, no code change);
  the live build showed the data WAS present but the row rendered under the wrong
  label - an ordering bug in the display-label mapping - so the first fix was a no-op
  and the real fix needed a second PR + deploy cycle. Green CI + passing unit tests
  did not catch it (the fixtures used a label that dodged the ordering bug); one live
  read at diagnosis would have.
- **For a PROGRESSION / interaction symptom (won't advance, "stuck on a step",
  "can't proceed", nothing happens, a button errors on re-click) the authoritative
  source is DRIVING THE LIVE FLOW TO THE FAILING ACTION - and a DB query is NOT a
  substitute.** This is the render bullet's twin for behavior: the backend can be
  fully CORRECT while the FE fails to reflect it, so reading the DB row (a status,
  a step counter, an FK) "confirms" a phantom data/seed bug and hides the real FE
  one. "Verify by value" here means the value the REPORTER perceives - did the step
  advance, did the terminal action succeed - NOT a column value; the DB is only the
  backend half. Drive the reporter's exact click on the deployed build BEFORE
  writing the fix. Proof (2026-06-24): a Refund/Reissue "stuck on Step 3" blocker
  was diagnosed from the DB (workflows at current_step=3 with a replacement linked)
  as "inconsistent seed data" and a backend SEED fix was built + gated green;
  driving the live flow showed the backend Generate SUCCEEDS and the FE never
  advances past Step 3 (an FE off-by-one). The seed was the wrong surface and was
  reverted - one live drive at diagnosis would have skipped the whole detour.
- **A ticket's stated cause is a HYPOTHESIS, not the diagnosis - a ticket YOU
  authored earlier from inference is the most dangerous, because re-reading it
  launders your own guess into "fact".** Re-reproduce the symptom yourself per the
  class rules above before building the fix the ticket's framing implies. (The
  Step-3 detour above began from a ticket I had written from a DB inference, then
  executed without re-observing - the inference never got re-tested against the
  live surface it was about.)

### G1 - Assert the rendered VALUE, never presence or the placeholder
A grey placeholder showing the expected text is a FAIL. "An input exists" is
not a pass. Read `input.value` / the selected option / `checked` / the rendered
number via the DOM on the **deployed** build. Uncontrolled form libraries (e.g.
React Hook Form `defaultValues`) frequently paint correctly in dev + jsdom and
empty in production - "the test passes" and "the screenshot looks right" are
both insufficient. The `parity-sweep` skill is the methodology in depth; use
its scoped mode for single-fix verification.

### G2 - Pin the EXACT flow/component the reporter means
Apps grow parallel flows for the "same" feature (an onboarding wizard AND a
detail-page dialog; a summary card AND a drill-in page), each with its own copy
of the logic. Fixing or verifying the wrong one looks like progress and ships
nothing. Reproduce the reporter's path before touching code; when ambiguous,
ask.

### G3 - Verify on the build that contains your commit
Never verify against a stale deploy. Confirm the deployed artifact's commit sha
matches your push before driving the UI (step 8's polling procedure). A green
check on the old build proves nothing.

### G4 - The fix must land on the surface the reporter SEES
Code search finds *a* component that renders the words; the reporter's screen
may be a different one (Today-proof: a premium-type badge was first added to a
per-invoice expand panel when the visible surface was the page-level card).
After deploying, drive the reporter's actual screen - if your change isn't
visible there, you fixed the wrong surface. Revert the wrong-surface change
rather than leaving two competing copies.

### G5 - Drive the changed flow to its TERMINAL action
Changing one step of a multi-step flow (wizard, checkout, pipeline) is not
verified at that step. Drive the flow to its terminal action (Activate /
submit / save) on the deployed build, down the path a real user takes -
including ACCEPTING pre-filled defaults rather than re-typing them. The state
seams between steps (local form -> shared store -> final validator / submit
payload) are where fixed-one-broke-another lives: a step that validates its
own form while the final gate validates the shared store passes Next and fails
the terminal action (Proof: a restructure seeded a policy form's broker/agency
from earlier steps; they painted and passed Next but never synced to the
store, so Activate rejected "Required" fields the reporter could see filled -
filed as a new High blocker one day later). When hand-driving the whole flow
is slow or fragile, construct the state through the app's own API (create a
draft/record in the target state, resume it) and assert the persisted state
by value.

### G6 - Sweep the changed pattern's PARALLEL surfaces before closing
G2's twin problem, on the output side: apps implement the same affordance
separately in sibling flows (two wizards' preview cards, nav badges, contact
rows, input masks). A fix that changes a PATTERN on one surface - icon
placement, label, mask, color convention - creates a reporter-visible
inconsistency on every twin still carrying the old pattern, and that becomes
the next ticket (Proof: "add an Edit label" -> reopened "the account section
lacks it" -> reopened "now move it left to match the customer screen" - three
cycles for one affordance). Before closing: enumerate the pattern's parallel
instances (grep the component/icon/classname; if a graphify graph exists, ask
"what else renders this") and apply the same change or note the divergence in
the ticket reply as a conscious deferral. Prefer fixing consistency by SHARING
the implementation (extract the component) over copying the patch - twins that
share code cannot drift.

---

## The verification gate (the one step that keeps getting skipped)

The recurring, trust-destroying failure: claiming a ticket FIXED on the strength of
a PROXY - green CI, a passing unit test, a deployed sha, a DB row, a confident code
read - WITHOUT observing the reporter's symptom gone on the deployed build. The
tester catches it and resubmits. This gate is the one step with no external referee
(everything else has CI / the compiler / a hook), so it loses to the pull-to-finish.
Environments may back it with an external referee - see "Enforcement" below -
and the bar binds either way. Do not try to out-argue it.

- **Pin-FIRST, and pre-register the acceptance test (step 2 does this).** Before
  any code, drive the reporter's flow, OBSERVE the before-state (the symptom -
  or, for an additive item, the surface without the change), and write the exact
  observable-that-must-change into the ticket / work-set notes ("Acceptance:
  clicking Generate advances to Step 4"). No acceptance line recorded -> not
  allowed to build. This makes the end-check mechanical (re-run that exact
  step), not "looks right", and makes the end-drive nearly free (you are already
  on the surface).
- **Never write the bare word "fixed." State the EVIDENCE.** A close-out (and any
  "done" you say to the user) must carry: `before-state <X> -> on target sha
  <Y> -> <the acceptance observable now true, by value>` (for a fix that reads:
  reproduced symptom -> symptom GONE). If you cannot fill that line with a real
  observation, you have not earned the claim - downgrade it (below).
  "Deployed / CI-green / the test passes" never fills it.
- **Strictness by acceptance class (the bar):**
  - BEHAVIOR / UI / progression / render ("stuck", "won't advance", wrong value,
    missing row, new control) -> a LIVE DRIVE on the DEPLOYED build to the
    failing (or new) action. A DB query, a code read, CI, and a passing unit
    test are CORROBORATION, never the verification - the backend can be correct
    while the FE is broken (G0-(D)).
  - DATA / seed -> a by-value staging query (DB proxy / API) PLUS a sha-confirm
    that the deployed build is the one you checked.
  - ARTIFACT / API / CLI (a command's output, a library's return, a generated
    file, an endpoint's response) -> RUN the real artifact built FROM the merged
    sha (fresh install/build - never your worktree) and assert the output by
    value (stdout / exit code / response field / file content). The captured
    run output IS the artifact the screenshot would be for a UI close.
- **The escape hatch is a LAST resort, never a first one.** Only a genuine
  can't-observe - you EXHAUSTED the observation tools that fit the target
  (authed-browser / preview / devtools for a web surface; running the artifact
  itself for a CLI/library/API), and NEVER for a surface reachable by clicking a
  visible button or running a shell command - may ship as a LOUD, distinct
  `unverified-reasoned: <why unobservable + the unit test that covers the
  path>`, routed to the reporter ("please confirm on retest"). Quiet skips, and
  "my first method did not pan out", are the abuse this gate exists to stop.
- **Enforcement (the bar is yours; the referee is the environment's):** this
  bar is NORMATIVE - it binds with or without tooling. An environment MAY wire
  an external close-out referee (a Stop hook / CI check that blocks a
  fixed/verified claim lacking evidence); this skill neither requires nor names
  one - the project/environment layer declares the concrete referee, if any
  (see the project-facts template's "Close-out referee" slot). What a
  well-formed referee checks, and what you must show REGARDLESS: after the last
  merge, BOTH (1) a BINDING to the verification target (a navigate to the app
  host / a deployment read / a staging query / a fresh artifact run at the
  merged sha) AND (2) an OBSERVATION (a screenshot, a by-value DOM read, a
  by-value query, or captured run output). **A bare navigate or a lone
  deployment read is a touch, not an observation:** arriving at the build
  proves you got there, not that the acceptance observable is true. Where a
  referee exists it is a FLOOR, not the bar; where none exists (or its
  detection cannot see your close-out medium) the gate is refereed by NORMS
  ONLY - which is exactly when quiet skips creep back, so hold it harder, not
  softer. If a referee fires, do the verify or the honest downgrade - do not
  relabel an unverified fix to dodge it.

---

## The loop

0. **Enumerate the WORK-SET before starting any item (the step that was
   missing - serial-by-default died here).** The work-set is what EXISTS, not
   just what the message cited:
   - The loop's INPUT is a set of tasks, however they arrive. A plain list of
     asks in chat is the primary, first-class form - each ask is a work-item,
     no tracker needed; the loop runs end to end on text input alone. A
     plan/handoff/audit DOCUMENT on disk is the same thing in a file: its
     line-items/findings are the work-items and its author is their reporter -
     enumerate it like a message. Collect every actionable ask from the
     message(s)/document first. THEN, only when the project HAS a tracker layer
     (a project skill naming a board/queue - that layer is a project EXTENSION
     of this loop, not an assumption of it): a board-shaped ask ("run the
     loop", "work the board", "new items") expands the work-set with the
     board's FULL Open/reopened column, and multiple tickets sitting Open ARE
     the work-set even if the user named only one.
   - **TYPE each item; non-fix shapes ROUTE, but everything stays in ONE
     plan.** Fixes/regressions and small fully-specifiable additions run this
     loop natively (G0 picks the matching form). An item that needs real DESIGN
     (its shape is undecided) goes to `superpowers:brainstorming` /
     `superpowers:writing-plans` FIRST, and its output - specified items, an
     MSP-sliced plan - re-enters THIS work-set as items. A prototype/design
     -source port is a `parity-builder` MSP. A mechanical many-site sweep runs
     natively, sweep-shaped (census first - see G0). Routing changes WHO
     designs/builds an item, never the plan or the gates: every item, routed or
     native, appears in the same `fanout` items JSON (a design item is a
     wave-0 producer; its impl items declare `after` it) and crosses the same
     spine.
   - **2+ actionable items -> `fanout` is the MANDATORY next step, before
     any per-item work** (see Batching). Prep is itself a fan-out: refresh the
     graph NOW (`graphify update .` per touched repo - GitHub-side merges never
     fire the local post-commit rebuild, so the graph is otherwise weeks stale)
     and scaffold the items JSON with one cheap recon agent per work-item
     predicting its edited files + surfacing producer->consumer edges to
     declare as `after` - never hand-decompose (recorded failure: a hand split
     missed a shared test file and two same-file leaves collided). No graph?
     Build it now (`graphify .`) when the stack supports it; otherwise run
     fanout WITHOUT `--graph` - only the import-adjacency signal is lost.
     A missing graph is never a reason to skip the planner.
   - Exactly 1 item: proceed to step 1 - but the re-batch rule below stays armed
     for the whole session.
   - **RE-BATCH ON ARRIVAL (the standing rule):** a new ask or ticket landing
     mid-session JOINS the work-set immediately - triage it, re-run
     `fanout` over remaining+new, and if it is disjoint from in-flight
     work, dispatch its build in parallel NOW. Never queue it silently behind
     the current item's close-out; "I'll finish this first" is the serial trap.
     Your spine waits (CI polling, deploy polling) are exactly when the new
     item's build should be running.
1. **Triage the task AND everything attached to it.** For a tracker ticket
   that means the ticket AND every comment; for a text-input task the chat
   thread IS the ticket - triage the ask plus every prior correction or
   follow-up the user gave on it. A closed-pending ticket with a fresh
   reporter comment is REOPENED - comments are new requirements, not
   chatter. Separate: (a) actionable, (b) already-answered, (c) blocked on
   input you genuinely cannot recover (note: if a prototype/design source
   exists in the repo, extract the spec from it YOURSELF before declaring
   anything blocked - "needs a screenshot" is rarely true when the prototype
   code is on disk).
   **If triage GROWS the work-set past one actionable item (comments spawned
   new asks), step 0's rule applies NOW: run `fanout` before touching any
   fix, THEN run the per-item steps below per that plan.**
2. **Pin the flow** (G2). If the project has a graphify graph
   (`graphify-out/` exists - see `graphify`), query it FIRST to find which
   component renders the reporter's surface and whether parallel
   implementations of the feature exist (`graphify query "what renders
   <surface>"`, or read `graphify-out/GRAPH_REPORT.md`). **Also query
   trajectory memory FIRST** (the `trajectory-kb` MCP, if available):
   `query_trajectory({ surface, text: <symptom keyword> })` to see what was
   already tried on this surface and what failed - a prior `what_failed`
   ("capped height - wrong axis") is the G0 wrong-axis / G4 wrong-surface trap
   pre-recorded,
   surfaced before you spend a build on it. graphify answers "what renders X"
   (structure); trajectory-kb answers "what did we try on X and what happened"
   (history). Then identify the
   exact component/route, pin the G0 BEFORE-STATE live (reproduce the symptom,
   or capture the surface without the change), and **PRE-REGISTER the
   acceptance line** - write the exact observable-that-must-change into the
   ticket / work-set notes ("Acceptance: clicking Generate advances to Step
   4"). No acceptance line recorded -> not allowed to build; the verification
   gate reads this exact line back at step 9 (graph = hint, live app = truth).
3. **Isolated worktree.** `git worktree add -b <branch> <path> <integration>`;
   symlink untracked deps the build needs (node_modules, .env files, venvs).
   Keep work off the integration branch until gated. (A solo LITE-lane item may
   use a plain branch instead - see Proportionality; a batch always worktrees.)
4. **Implement.** For a non-trivial bug, run `superpowers:systematic-debugging`
   first - its Iron Law (no fix without root-cause investigation) is the one
   discipline the gates do NOT cover: G0 already reproduced the symptom for the
   acceptance test, so REUSE that as its Phase 1 (don't reproduce twice) and spend
   the effort on WHY - fix the cause, not the symptom. Recurring traps worth checking
   explicitly:
   - `'' ?? fallback === ''` but `'' || fallback === fallback` - empty-string
     defaults need `||`.
   - A form that errors with "required information" while every visible field
     is filled has a HIDDEN required field being stamped empty.
   - Prefer controlled inputs over uncontrolled defaultValues (G1's render gap).
   - Two-sources-of-truth divergence (G5's code shape): any value that enters a
     form WITHOUT a change event - seed, default, async hydration - must be
     explicitly synced to the shared store the final validator reads. When
     adding a seed/prefill, grep for the store's readers (final validation,
     submit payload) and add a test that runs the REAL final validator against
     the store as a user would leave it (defaults accepted, nothing re-typed).
   - Add a pure-logic unit test for any mapping/seeding/formatting helper.
5. **Gate** - run the `pre-commit` skill: the project's REAL commands
   (typecheck, lint, tests, plus any custom gates like ASCII-only diffs), all
   green before commit. Never claim green without running them
   (`superpowers:verification-before-completion`).
6. **Commit** - via the `git-commit` skill, honoring the project's per-repo
   commit identity + required trailers (never edit git config).
7. **Open a PR and merge only on green CI** (replaces any direct-push that
   admin-bypasses a required check; CI is the authoritative gate). Push the
   branch, open a PR against the integration branch, poll the required check to
   green (deploy-verify-style - do not hammer), then merge with a method that
   PRESERVES THE COMMIT AUTHOR where the deploy platform author-gates the HEAD
   (e.g. rebase-and-merge). NEVER merge red and NEVER admin-bypass the required
   check; on red, read the logs, fix on the branch, re-push. The local
   `pre-commit` gate stays as a fast pre-check. (Project facts - branch names, the
   required check's name, the merge method, the author-gate - come from the
   project skill.)
8. **Ship to the verification target + confirm it carries your sha** (G3 - the
   deploy-verify step). Web app: poll the platform's deployment status until it
   is READY **and** reports your merged sha. Deploys take time (roughly a
   minute to several), so background-wait and re-check instead of hammering -
   and never start verifying on hope: a green look at the PREVIOUS build proves
   nothing, and an evidence capture made before the new build is live binds
   your observation to the WRONG sha. The project skill names the platform, the
   exact alias/endpoint to poll, and the typical build time. CLI/library/
   service with no auto-deploy: build/install the artifact FROM the merged
   integration sha (fresh venv/install, never your worktree) - that artifact IS
   the "deployed build" the next step verifies.
9. **Verify by value on the target** (G1 + G4), driving the reporter's exact
   flow, then the flow's terminal action (G5) and the changed pattern's twins
   (G6). **Capture the proof as you verify - a required artifact, not a nicety
   (any wired close-out referee checks for it):** for a UI/behavior item, take a SCREENSHOT
   of the deployed surface AND read the rendered value via the DOM (the
   screenshot is the shareable proof you looked; the DOM read is the actual G1
   assertion - a screenshot alone can show a grey placeholder and pass the
   eye); for a data item, the by-value staging query output plus the
   deployment sha-confirm IS the artifact; for an artifact/API item, the
   captured command run / endpoint response (at the merged sha) IS it. Re-run
   the step-2 acceptance line verbatim. If you cannot re-check it, say so - do
   not assert "fixed". When UI-driving the repro is fragile or slow, construct
   the reporter's state via the app's own API and assert persisted state by
   value - a legitimate repro, often 10x faster.
10. **Close out**: move the ticket to the project's "fixed, pending retest"
    status with concise resolution notes (what changed + that it was
    browser-verified). No tracker (the task arrived as text)? Same close-out,
    different medium: report to the user per task with the SAME observed-value
    evidence - the verification gate, the evidence bar, and the trajectory
    append below apply identically. **The note MUST cite the OBSERVED VALUE, never the bare
    word "fixed" / "verified":** "verified live on the deployed build: the
    Resolved tile shows 3" or "by-value staging query returns resolved_count =
    3" - that observed value is the artifact the gate, the reporter, and the
    next retest all read; a note that says only "browser-verified" has not
    earned the claim. Then reply **in the reporter's comment thread**
    addressing each ask point by point. Net-new deliverables get their own
    ticket so they are tracked for retest - and so does any net-new BUG
    discovered while verifying: file/flag it, never scope-creep the current
    fix or silently drop it (no tracker? list it as a FLAGGED item in the
    close-out report for the user's disposition - same rule, different
    medium). **Then record the trajectory** - the append contract, the outcome
    enum, and the append-on-EVERY-exit rule live in "Trajectory memory" below
    (canonical). Short form: `append_trajectory(...)` with `outcome` = the
    exact G0 status you shipped, failures and blocked exits recorded too; the
    only exit that skips the append is a loop genuinely paused mid-flight.
11. **Clean up**: remove the worktree, delete the branch. If the project has a
    graphify graph and you changed code, run `graphify update .` to keep it
    current (AST-only, local, no API cost).
12. **Ratchet the project facts.** If this run taught you a durable mechanic -
    a state-construction shortcut (how to build a repro via the app's API), a
    twin-surface pair, a push/identity quirk, a browser-driving workaround, a
    flaky-looking-but-real gate behavior - write it into the PROJECT skill
    before ending, in the matching section. Auto-memory is for session state;
    mechanics that any future loop run needs belong in the skill, or every
    session re-learns them by trial and error (proof: an entire session's
    worth of click-scaling, push-mechanics, and repro-recipe discoveries sat
    only in memory until a manual audit moved them). One paragraph per fact,
    same style as the section it joins.

## Proportionality: the lane scales, the gates do not

Full ceremony on a one-line copy fix trains everyone to route AROUND the skill -
the worst outcome. The LITE LANE applies only when ALL hold: a single item; no
logic / contract / data-shape change (copy, a label, a comment, a style token,
docs); <= ~5 lines across 1-2 files; no high-risk-marker surface. When in
doubt -> standard lane.
- **LITE KEEPS (non-negotiable):** a branch + PR + CI-green (shared policy,
  never bypassed), the G0 before-state pin + a one-sentence acceptance line,
  ONE by-value check on the verification target, the G6 twin grep (labels and
  typos have twins), and an evidence-cited close-out.
- **LITE WAIVES:** fanout (it is a single item), recon scaffolding, the
  graphify/trajectory queries (a grep suffices), the isolated worktree when
  working SOLO (a branch on the main checkout is fine; a batch ALWAYS
  worktrees), systematic-debugging, the screenshot+DOM dual artifact (one
  observation suffices), the trajectory append (unless something SURPRISING
  happened - surprises always append), and the step-12 ratchet.
- **ANTI-STRETCH:** the lane is for changes whose entire diff a reviewer
  absorbs in one glance. The moment a lite item grows (a second concern, a
  conditional, a data shape), it upgrades to the standard lane MID-FLIGHT.
  Lane creep is how bypass starts.

## MSPs: how a work-set becomes PRs

An MSP (minimum shippable product) is the smallest INDEPENDENTLY-MERGEABLE
unit: CI-green on its own, deployable on its own, revertable on its own.
**The MSP is the PR: one MSP = one branch = one PR**, and MSPs are what run in
parallel. The mapping from a `fanout` output is mechanical:

- **Each serialize-together CLUSTER = one MSP.** Single-item clusters are the
  common case (one item, one PR). Items forced together by a shared file or a
  `contract_group` ship as ONE PR - their leaves build inside it and converge;
  never hold two open PRs that edit the same file.
- **`after` edges order MSPs without merging them.** A consumer MSP starts
  building when its producer INTEGRATES (merges) - or, when pipelining harder,
  branches off the producer's branch and rebases on its merge (state the risk).
  Two consumers of one producer stay parallel with each other.
- **The global `waves` ARE the MSP schedule:** wave N's MSPs build and ship
  concurrently; integrate between waves.
- **Too big for one PR?** A cluster whose diff a reviewer cannot hold (rule of
  thumb: > ~800 changed lines, or it crosses a high-risk boundary mid-way)
  splits at wave boundaries into STACKED MSPs - ordered PRs, each CI-green,
  each independently shippable; never a partial slice that leaves the
  integration branch broken.
- **Design-first items:** the design leaf (`brainstorming`/`writing-plans`
  output) is a wave-0 producer; its impl items declare `after` it.
  `writing-plans` slices a big feature INTO MSPs under these same rules.
- **Degenerate case:** a one-item work-set is one MSP - no planner run needed;
  the loop above IS that MSP's spine.

Two-level parallelism, explicitly: MSPs run in parallel, each shipping its OWN
PR; WITHIN an MSP, its file-disjoint leaves fan out and CONVERGE into that one
PR. Tiering lives in the build zone only; every MSP crosses the same spine
(review -> gate -> CI-green -> merge -> target-verify -> close), which stays
orchestrator-owned and top-tier.

## Batching a work-set (fan-out)

When one loop run covers 2+ actionable work-items, the FAN-OUT PLAN comes
first: run the `fanout` skill BEFORE dispatching any per-item agent - it
decides what parallelizes, in what order (`waves`), and on which model tier;
the MSPs section above maps its output to branches/PRs. Then execute: one
background build agent per MSP (leaves within a big MSP fan out too), each in
its OWN worktree (step 3) on its assigned tier, while you do the
trust-boundary work yourself - review each diff, re-run the gates fresh,
commit/push, merge, confirm each deploy/artifact. Verification is per-item in
SCOPE (G1/G4/G5 are never batched away) but PIPELINED in TIME - an item
verifies the moment ITS target is live, never saved for a serial end-sweep.
Items sharing files are ONE MSP in one worktree. Never let agents push, merge,
or close items themselves - implementation parallelizes; gating, shipping, and
verification judgment do not. Dispatch mechanics: use the Workflow tool
(`parallel()`/`pipeline()`, worktree isolation - skill-directed use is
authorized) when the batch shape is known up front - the script survives a long
session; use ad-hoc background agents when items trickle in or need
conversational steering. Either way, EXECUTE disjoint work CONCURRENTLY - the
speed win is real only if you actually fan out.

**Plan from file-disjointness + declared dependencies, never by feel.** Feed
`fanout` the work-items with their recon-predicted files, `after` edges,
and the project's risk-markers; consume its `clusters`/`waves`/`tier` per its
own skill doc (canonical for the tool's semantics). Two consumption rules are
non-negotiable: render an explicit parallelize-vs-serialize verdict on EVERY
`coupling_review` pair before dispatch (skeptical default = serialize), and
declare `contract_group` / `after` rather than eyeballing coupling - repo
-disjoint is NOT dependency-independent (a BE producer and its FE consumers
look parallel to a file view). File-level disjointness of the EDITED files is
the merge-safety unit - not symbol-level, not transitive import-coupling.

**Pipeline the SPINE - the orchestrator's wait states are the batch's schedule.**
The serial spine (review -> PR -> CI-green -> merge -> target-verify -> verify ->
close) is per-MSP and orchestrator-owned, and its waits dominate a batch's
wall-clock: a CI run is 10-20 minutes and a deploy poll is minutes, PER MSP.
Never sit idle in a spine wait: while MSP A's CI runs or its deploy builds,
dispatch/review MSP B's build, scaffold the next wave's items, or do the next
diff review - polling is a background activity, not a foreground task. And BATCH
the merges: when several PRs are CI-green together, merge them as a group so they
ride ONE deploy -> ONE deploy-verify sha-confirm -> per-item by-value checks
(G1/G4/G5 stay per-item; the deploy-confirm is per-DEPLOY). Exception: a
high-blast-radius change (money/ledger, auth, destructive migration) merges ALONE
so a revert stays clean - the orchestrator calls it.

**Tier the model by RISK, not role** (mechanics in `fanout`, canonical).
The orchestrator and every leaf touching a project-flagged HIGH-RISK surface
stay top-tier; only mechanical, fully-specified leaves with no high-risk
surface drop to a cheap model (in a Workflow: `agent(prompt, {model:'<cheap>'})`
for those, omit the override otherwise). Tier REVIEW depth the same way:
high-risk leaves get a full adversarial review, mechanical leaves an
orchestrator diff-glance - review rigor matches blast radius so review overhead
never exceeds the tiering saving.

**Batch the orchestrator's own labor - it is the real width ceiling.** Waits
are pipelined (above), but your ACTIVE serial work scales with fan-out width
too: review diffs in CONVERGENCE GROUPS as waves complete (not in arrival
order, one by one); write close-outs in a batch after each group-merge;
append trajectories at natural pause points (each entry still per-item). The
per-item gate-read stays per-item, but it is ONE cheap read each. Practical
batch width = what you can review and close without becoming the queue - when
the review backlog grows faster than builds land, stop dispatching and drain.

**Subagent output contract.** Every dispatched agent's final message is
injected into YOUR context verbatim - across a 10-agent fan-out, verbose
prose returns are the difference between finishing and compacting. Demand
contract-shaped returns in the dispatch prompt: one line per finding/change
as `file:line - claim - evidence`, a closing `totals:` count line, no prose
preamble or recap. Two hard rules: (1) evidence is never compressed away - a
bare verdict ("no issues", "done") without the supporting line/quote/output
fails verification and gets re-run; (2) the contract is for agent-to-you
returns ONLY - anything a human reads (ticket replies, commit bodies,
summaries to the user) stays full prose.

**Parallelize the verification LABOR** (the full rule set - the labor-vs-gate
split, the authed-UI single-session rule, per-leaf verify-modes - lives in
`fanout` VERIFY-MODE, canonical; note it is doctrine read off the
project's markers at consume time, NOT a computed plan field). The two moves:
PIPELINE build->verify (Workflow `pipeline(items, build, verify)`, no barrier)
so an item verifies the moment ITS target is live; and FAN OUT by-value / DATA
verification to a verifier-agent pool (cheap tier, session-less reads
returning `{item, observed_value, sha, pass, evidence}`). What never fans out:
the gate-satisfying observation + judgment (any wired Stop referee reads YOUR
transcript, not a subagent's - do the ONE cheap confirming read yourself and
cite the value) and
the authed deployed-UI live-drive (a single authenticated session). This shape
is work-type-agnostic - net-new builds and ports verify the same way.

## Trajectory memory (cross-loop learning)

The loop's two memory touchpoints, served by the `trajectory-kb` MCP (a global,
repo-tagged, append-only store - it aggregates across repos, so a trap recorded
on one project warns the next). This is the "agents learn from past
trajectories" idea, scoped to this pipeline's discipline instead of a generic
log:

- **Read at the start (step 2, with graphify):** `query_trajectory({ surface,
  text })`. graphify tells you what renders the surface; trajectory-kb tells you
  what was already tried on it and what failed. A past `what_failed` is the G4
  wrong-surface / G0 wrong-axis miss pre-recorded - the cheapest possible way to
  not repeat it.
- **Write at every loop EXIT (step 10), not just a clean close - after the
  by-value verify when there is one; the only exit that skips it is a loop
  genuinely paused mid-flight (not yet exited):** `append_trajectory({ repo,
  surface, surface_key, symptom, root_cause, outcome, what_worked, what_failed,
  files, regressed, tier })`. The `outcome`
  enum is deliberately the G0 ship ladder - `fixed` / `unverified-reasoned` /
  `speculative` / `reverted` - so the store doubles as a queryable history of
  which fixes shipped verified vs downgraded vs blocked, per surface. **Record
  the FAILURES, not just the wins:** a downgraded, reverted, or blocked exit
  (you could not verify and handed the ticket back) is the entry most worth
  keeping - it is what stops the next loop repeating the wall. A success-only
  store is survivorship bias (a recent sample read 100% `fixed`, so it could not
  surface any recurring pain). Record the root cause and, crucially, the dead
  ends in `what_failed`. Pass `surface_key` (the canonical primary file /
  component id) so the same surface GROUPS across loops - free-text `surface` is
  almost never written identically twice, so without the key recurrence is
  invisible (the server auto-derives one, but explicit is more reliable). Also
  pass `files` (the edited files) and, if the fix broke a twin surface (a G6
  miss), `regressed` (that surface) - these feed `fanout`'s history-aware
  tiering and its `regression-history` coupling signal, so a surface with a bad
  track record auto-bumps to the top tier the next time it is planned.

It does NOT replace the step-12 ratchet (durable MECHANICS still go into the
project skill) or auto-memory (session state). Trajectory-kb is the per-incident
"what we tried on this surface and how it turned out" layer - the thing that was
previously locked in a closed ticket nobody re-reads.

## Failure modes (red flags - STOP)

| Rationalization | Reality |
|---|---|
| "Tests pass, it's fixed" | jsdom != production render. Verify by value on the deploy (G1). |
| "My change is deployed, so it's fixed" | Deployed != the reported symptom is gone. Re-check the reproduced symptom (G0), not just that your change shipped. |
| "Can't reproduce it, but the code clearly shows the cause" | Reasoning != observation. Get a tool/info that CAN observe it, or downgrade the claim - never assert "fixed" against a symptom you never saw (G0). |
| "I found the component by grep" | Grep finds A component, not THE surface. Drive the reporter's screen (G2/G4). |
| "Can't open the surface, but the code clearly shows how it works" | Code-inference under blocked observation is a HYPOTHESIS, not a fact. Hedge it, cross-check the authoritative enum/type/contract (not one grep), and let a refuting gate (tsc/test) re-open the diagnosis (G0-D). |
| "Automation can't reach it, so ship unverified-reasoned" | Drive the user's LIVE session via Claude-in-Chrome first, then Playwright/DevTools/preview. A surface behind a visible button is observable - exhaust the tools before any can't-observe downgrade (G0-C precondition). |
| "The deploy is probably done" | Confirm the sha (G3). ~70s feels like forever; verify anyway. |
| "This needs the reporter's screenshot" | If a prototype/design source is on disk, extract the spec yourself first. |
| "I'll reply on the ticket page" | Reply in the reporter's THREAD or they won't see it in context. |
| "Auth wall - I'll log in" | Never enter credentials/OTP. Pause and ask the user to re-auth. |
| "My step works; the rest of the flow is unchanged" | The seam you changed feeds the terminal action. Drive it (G5). |
| "Fixed the exact card the reporter pointed at" | Its twin in the sibling flow still has the old pattern - the next ticket (G6). |
| "I'll just push direct, the bypass notice is normal" | A required check that never blocks is a single point of failure. Open a PR; merge on green (author-preserving). |
| "Starting fresh on this surface" | Maybe not - `query_trajectory({surface})` first; a past `what_failed` is the wrong-surface trap already paid for once (trajectory memory). |
| "I'll finish this ticket first, then look at the new ask" | Re-batch (step 0): the new item joins the work-set NOW; your CI/deploy waits are exactly when its build should run. Queueing it is the serial trap. |
| "The board has other Open tickets, but I was only asked about this one" | Board-shaped ask -> the full Open column IS the work-set (step 0). One-at-a-time drains a board at ~1 spine per ticket. |
| "One big cluster - it all serializes" | Read `waves`: a real 92-item work-set runs 25-wide in wave 1. Only clique tails (N items editing ONE file) are one-at-a-time. |
| "CI is running, I'll wait for it" | Polling is background work. Foreground = the next MSP's build/review (Pipeline the SPINE). |
| "It's additive - nothing to reproduce, so G0 doesn't apply" | G0's second form: capture the surface WITHOUT the change (the before-state) + pre-register the NEW observable. No acceptance line -> not allowed to build. |
| "No deploy on this project, so steps 8-9 don't apply" | The verification target is the built artifact at the merged sha (fresh install, run it, assert output by value). A CLI/library is never exempt. |
| "It's basically trivial" (it touches logic) | The lite lane is copy/docs/token-sized only, and it KEEPS PR+CI+the by-value check. Lane creep is how bypass starts (Proportionality). |
| "These two are in different repos, so they're parallel" | Repo-disjoint is not dependency-independent. Declare the `after` edge (BE producer -> FE consumers) and let waves order them. |

## Related skills
- `parity-sweep` - value-assertion methodology (G1 in depth) + scoped mode.
- `parity-builder` - prototype/design-source ports: it owns those MSPs; they
  still join this loop's plan and spine (step 0 typing rule).
- `superpowers:brainstorming` / `superpowers:writing-plans` - design-shaped
  items route there first; their output re-enters the work-set as specified
  items / an MSP-sliced plan (step 0 typing rule).
- `fanout` - clusters/waves/tiers + `after` dependency ordering; the MSPs
  section above maps its output to PRs.
- `trajectory-kb` (MCP) - cross-loop memory: query past trajectories at step 2, append the shipped outcome at close-out.
- `pre-commit` - project-real gates. `git-commit` - identity-aware commits.
- `superpowers:systematic-debugging`, `superpowers:verification-before-completion`.
- The project-level skill supplies all concrete facts (boards, repos, URLs).
