---
name: fanout
description: Use whenever 2+ work-items are on the table in one session - a board with several Open tickets, a multi-finding fix wave, several asks in one or successive user messages - BEFORE starting any of them, and AGAIN when new items arrive mid-session (re-batch; do not queue new asks behind the current item). Not just for when a fan-out is already decided - this tool is HOW you decide: it computes parallel vs serialize clusters, the wave schedule (honoring declared `after` dependencies), and per-item risk tier from the items' edited files (+ an optional graphify graph for coupling hints). Consumed by ship (step 0) and parity-builder (plan step). The project supplies the risk-marker taxonomy and any graph path; this tool bakes in no project paths.
---

# fanout

Turn "fan out only on disjoint files" from manual judgment into a computed plan.

**Boundary: fanout writes the schedule; `ship` runs the job.** This tool plans
(clusters/waves/tiers, in seconds, deterministic) and NEVER executes - it spawns
no agents, touches no git, ships nothing. The actual fan-out (dispatching build
agents per wave, the gated spine, verification, close-outs) is the CONSUMER's
job - `ship` for work-sets, `parity-builder` for ports.

## Use it
`python3 ~/.claude/skills/fanout/fanout.py --items <items.json> [--graph <graph.json>] --risk-markers <a,b,c> [--trajectories <store.jsonl> | --no-trajectories]`

- `--graph` (optional): a graphify `graph.json` (node-link). Per-repo, or the
  merged multi-repo graph (run graphify from the repos' common parent dir).
  Missing/absent graph = the plan loses ONLY the `import-adjacent` coupling
  signal; clustering, waves, tiers, and the marker/history signals all still
  compute - so a project with no graph runs the planner rather than skipping it
  (build the graph first when the stack supports it; it feeds better verdicts).
- `--items`: JSON `[{"name": "...", "files": ["path", ...], "contract_group": "tag", "after": ["producer", ...]}]` -
  one entry per work-item (leaf/ticket/ask) with the files it will edit. Two
  optional relationship fields, with OPPOSITE semantics:
  - `contract_group`: items sharing a tag are forced into one serialize-together
    cluster - declare it when two FILE-DISJOINT leaves are halves of ONE change
    (e.g. a backend split + the serializer that exposes it) so a single owner
    holds both. Deterministic "do not parallelize these; one MSP."
  - `after`: DIRECTIONAL producer->consumer ordering - "this item starts only
    after the named items INTEGRATE." It does NOT merge them into one owner:
    two consumers of one producer stay parallel with EACH OTHER (waves put the
    producer earlier, both consumers together later). Use it for cross-repo/API
    dependencies (BE endpoint -> the FE items that consume it) and design->impl
    chains; using contract_group there over-serializes independent consumers.
- `--risk-markers`: comma-separated path substrings that force the top model tier
  (the PROJECT supplies these - its own high-risk surfaces, e.g. financial, auth,
  migration, or contract paths).
- `--trajectories`: (optional) the `trajectory-kb` JSONL store. Defaults to the
  global store and is read automatically, so the gate is HISTORY-AWARE: a surface
  with a bad track record gets tiered up and surfaces known to break each other get
  a serialize hint. A missing/empty store - or `--no-trajectories` - yields the
  marker-only plan (identical output). History only ever ADDS caution; it never
  relaxes a tier or drops a signal.

Output JSON:
- `clusters`: lists of item names. Items in one cluster share an edited file OR a
  declared `contract_group` -> MUST serialize. Distinct clusters are disjoint ->
  safe to run in parallel.
- `waves`: ONE GLOBAL execution schedule over ALL items (the batch's ordered
  plan). Items in one wave are mutually conflict-free (no shared file, no shared
  contract_group) AND have no `after` path between them -> run concurrently;
  each wave starts from the INTEGRATED result of the waves before it
  (merge/rebase between waves, or one owner stepping through). `after` consumers
  always land in a later wave than their producers; hubs go early (the shared
  spine, e.g. a models.py contract, integrates before its dependents fan out). A
  big cluster is NOT a serialize-everything verdict - a real 92-item set
  decomposes to 18 waves with wave 1 running 25 items concurrently; only a
  clique tail (N items all editing one file) is irreducibly one-at-a-time. A
  cluster's internal order = the global waves filtered to its members.
- `coupling_review`: for each file-disjoint, NOT-co-clustered PAIR that carries a soft
  coupling signal, an entry `{pair, signals, default}`. Signals: `import-adjacent`
  (their files are one hop apart in the graph), `shared-risk-marker:<M>` (the SAME
  risk-marker matches a file in both), and `regression-history` (trajectory memory
  records a fix on one of these surfaces having BROKEN the other). `default` is
  `serialize` when they share a risk-marker OR have a regression history (same
  high-risk subsystem / known to break each other -> likely must serialize), else
  `parallel`. Signal-free pairs are omitted, and so are pairs already ORDERED by
  an `after` path (their verdict is declared, not pending). This FEEDS the
  mandatory verdict below; it does NOT decide - the orchestrator does.
- `tier`: per item, `top` or `cheap` (map to your models, e.g. top=Opus, cheap=Sonnet).
  A path-marker match forces `top`; trajectory memory ALSO forces `top` for a surface
  with a bad track record (a recorded revert, a speculative ship, a caused-regression,
  or >=2 prior wrong-surface traps).
- `tier_notes`: present ONLY when history bumped something - per bumped item, the
  reason (e.g. `"history: 1 reverted, 2 prior traps"`). Absent otherwise.

## Consuming the plan
- **Render the coupling verdict FIRST (mandatory, every fan-out).** For EVERY
  `coupling_review` pair, make an explicit parallelize-vs-serialize call with a
  one-line rationale BEFORE dispatch. This is deterministic - always done, on any
  fan-out, regardless of leaf count - and the ORCHESTRATOR renders it inline (no
  extra judge agent). Skeptical default: a `default:"serialize"` pair STAYS
  serialized under one owner unless you can state why the two are genuinely
  independent. The signals are a HINT; the failure this prevents is parallelizing
  coupled-but-file-disjoint halves of one contract (what file-overlap clustering
  misses) - catch them here, or declare them up front with `contract_group`.
- **Execute the `waves` schedule: everything in a wave runs CONCURRENTLY;
  integrate between waves** - parallel background agents, or the Workflow tool's
  `parallel()`/`pipeline()` with worktree isolation (skill-directed use of the
  Workflow tool is authorized; the schedule maps to a serial chain of
  `parallel()` wave steps). Do NOT run disjoint items one-at-a-time, and do NOT
  treat a big cluster as one serial lump - the waves ARE its internal
  parallelism. Sequential (e.g. subagent-driven) execution is for clique tails
  and coupled chains only. The speed win is real only if you actually fan out; a
  careful orchestrator defaults to serial and loses it otherwise. How clusters
  become MSPs/PRs and who ships them: the `ship` skill's "MSPs"
  section is canonical - a serialize-together cluster ships as ONE PR; `after`
  orders separate MSPs without merging them.
- Map `tier` to the model per leaf; the orchestrator + every review/gate/ship step
  stays top-tier.
- **VERIFY-MODE: fan out the verification the same way you fan out the build (the
  canonical rule, work-type-agnostic - fix, net-new feature, AND port all use it;
  it is the verify twin of the trust-boundary line above).** Read each leaf's
  verify-mode off the project's surface markers (same idea as the risk-markers): a
  leaf whose surface is authed deployed-UI verifies SERIALLY on the orchestrator
  (ONE authenticated session - parallel agents cannot each drive it; a
  standalone/automation browser is unauthed); a data / by-value leaf's verification
  OFFLOADS to a verifier-agent pool (session-less, cheap tier, one per leaf,
  returning `{leaf, observed_value, sha, pass, evidence}`). What NEVER fans out: the
  gate-read + judgment - the shipped "verified" claim (and any Stop verification
  hook) is keyed to the ORCHESTRATOR, whose transcript a subagent's read does not
  enter, so the orchestrator does the ONE cheap confirming read itself and cites the
  value. The project loop skill names the markers + the by-value channel. (NOTE:
  `fanout.py` computes the BUILD `clusters`/`tier`; verify-mode is read off the
  same markers at consume time - not yet a computed output field.)
- **Tier REVIEW depth by the same risk**, not just the model: `top` leaves get a
  full adversarial review, `cheap` leaves an orchestrator diff-glance. The
  orchestrator still reviews every diff and does all gating/shipping - parallelism
  never delegates the trust boundary.

## Caveats (it is a HINT, not a merge-safety oracle)
- **Clustering keys on edited-file overlap, NOT graph coupling - by design.**
  Graph-driven impact-set clustering was weighed and deliberately rejected:
  transitive coupling collapses a real codebase into one serial blob and kills
  parallelism. The graph stays advisory (the `coupling_review` signals feeding the
  mandatory verdict); the verdict + gate + orchestrator review catch logical breaks
  between file-disjoint items - and `contract_group` lets the scoper declare a known
  coupling outright (deterministic), without relying on the graph at all.
- **Producer->consumer dependency must be DECLARED - the graph cannot see it.**
  Two file-disjoint items where one needs the other's output first (a
  reasoning/design leaf that decides a contract, then impl leaves that build to
  it; a BE endpoint and its FE consumers) read as "parallel" unless you declare
  `after` on the consumers - recon/triage is where those edges are discovered,
  and declaring them is part of scaffolding the items JSON. With `after`
  declared, `waves` handles the rest (producer early, consumers together later -
  the Workflow serial `agent()` -> `parallel()` shape). Without it, conflict
  structure alone often approximates contract-first (hubs early) but is NOT
  semantic dependency - do not rely on the accident.
- File-level granularity: two agents editing different symbols in the SAME file still
  conflict - file is the safe parallel unit, not symbol.
- The graph can be stale (worktree commits may not rebuild it) - treat output as advisory.
- It is BLIND to the cross-repo API contract (per-repo graphs; a merged graph tags `repo`
  but does not model HTTP coupling) - cover that with the project's contract check.
- The orchestrator still reviews every diff before commit.
- **Trajectory matching is heuristic + strictly additive.** It joins history to items
  by edited-file overlap first, then surface/tag/name substring (for prose-only
  entries), so it can over-match - but the only effects are bumping a tier UP or
  adding a serialize HINT (the orchestrator still renders the verdict). It never
  relaxes anything, and an absent/empty store is a no-op. Populate `files` (and
  `regressed` when a fix breaks a twin) on `append_trajectory` for precise joins.

## Related
- `ship` (step 0 + batching), `parity-builder` (plan step) - the consumers.
- `graphify` - produces the `graph.json` this reads.
- `trajectory-kb` (MCP) - the history store this reads for history-aware tiering + the `regression-history` coupling signal.
