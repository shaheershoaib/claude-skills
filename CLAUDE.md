# graphify (the real graphifyy CLI + skill)
- `/graphify .` maps a project into `graphify-out/` (graph.json, GRAPH_REPORT.md,
  interactive graph.html) via local AST extraction - no API cost for code. The
  installed `graphify` skill handles queries; `/graphify` triggers it.
- If `graphify-out/` exists in a project, treat codebase/architecture questions
  as graphify queries FIRST (`graphify query "..."` / read GRAPH_REPORT.md)
  before grepping - this is what answers "what renders X / what else renders the
  same thing" (the wrong-surface + parallel-flow misses).
- After editing code in a session, run `graphify update .` to keep the graph
  current (AST-only, local). The graph is a hint - the live app is ground truth.

# Development pipeline (route work through skills - do not freestyle)

For any multi-step dev work, invoke the matching entry skill FIRST; each chains
its downstream skills. The user should never need to name the chain.

Slice work so each phase/PR is a MINIMUM SHIPPABLE PRODUCT - independently
mergeable, CI-green, and deployable on its own, never a partial slice that leaves
the integration branch broken (the mechanics live in `ship`'s MSPs section;
`writing-plans` slices net-new features into MSPs; `fanout` computes the
clusters/waves they come from).

A work-set can MIX types - each PR-cluster (MSP) goes down the pipeline matching ITS
type (feature / prototype port / bug fix / migration), and all converge on the one
shared gate (review -> PR -> CI-green -> rebase-merge -> deploy-verify).

- **Bug / ticket / tester feedback** ("fix #NN", "X commented", "run the
  loop") -> `ship`. It loads the project facts skill (the project's own
  `<project>-loop`) and chains its downstream skills itself.
- **New feature (net-new design)** -> `superpowers:brainstorming` first;
  `writing-plans` if multi-step; TDD for logic; the specified items re-enter
  the work-set and cross the shared gate.
- **Port/build a surface from an existing prototype or design source of
  truth** -> `proto-port` (translate-first: the proto CODE is the input,
  never stories/summaries/hand inventories; brainstorming is for net-new
  design, NOT ports). It self-finishes with a `parity-receipt`, then crosses
  the shared gate.
- **Large mechanical migration / sweep** (codemod, rename, API bump across many
  sites) -> scout the sites first, then `fanout` the per-site transforms,
  verify each, then cross the shared gate.
- **Parallel multi-item builds** (2+ actionable items EXIST or ARRIVE - tickets
  sitting Open on a board, several asks in one or successive messages; the
  trigger is the items existing, NOT a pre-made decision to parallelize) ->
  FIRST enumerate the full work-set (a plain list of asks in chat IS a
  work-set; a board-shaped ask additionally pulls the tracker's Open column)
  and run `fanout` over it BEFORE launching any per-item pipeline; an item
  arriving MID-SESSION re-batches into the work-set and dispatches in parallel
  if disjoint - it never silently queues behind the current item. THEN run the
  matching pipeline (`ship` / `proto-port`) per item, per that plan. The
  execution doctrine - waves, MSP mapping, model/review tiering, coupling
  verdicts, spine pipelining, verify fan-out - lives in `ship` (MSPs +
  Batching sections) and `fanout`'s own doc, not here.
- **"Is this surface/module done?"** -> `parity-receipt` (full). **Proactive
  bug hunt before testers** -> the project's module-audit skill; its lens-2
  "build the missing prototype feature" findings route to `proto-port`,
  not a blind build.
- **Review**: own risky diff -> `/code-review` or `codex` cross-model;
  someone else's PR -> `github-pr-review`.
- **Session end** -> `session-handoff`. **Periodic** -> `design-drift`,
  `anthropic-skills:consolidate-memory`.
- **New project setup** -> create `<project>/.claude/skills/<project>-loop/`
  with the facts (copy `ship`'s `references/project-facts-template.md`),
  bootstrap the verification gates (`npx receipts-cli init` wires the receipts
  plugin's per-project config), then `fewer-permission-prompts`.

Hard rule: never claim "fixed / green / deployed / verified" without the
corresponding step's evidence - fresh gate output, CI-green on the PR (never
admin-bypass a required check), sha-matched deploy, and a value-asserted check on
the deployed build that THE REPORTED SYMPTOM is resolved (your change being live is
NOT the same as the symptom being gone - reproduce the symptom FIRST so you have an
acceptance test to re-check; placeholder text is a FAIL; if you cannot reproduce
the symptom, DOWNGRADE the claim rather than assert a fix - the receipts
plugin's gates skill is canonical for the gate spec and downgrade statuses).

# MCP auth recovery (mid-session "Unauthorized")

If an MCP tool starts returning Unauthorized / auth-expired MID-SESSION (it worked
earlier), suspect a STALE TOKEN cached by the running server, NOT a real logout -
especially a LOCAL stdio server (e.g. a CLI-backed `<tool> mcp`) that reads creds from a
config/keychain at spawn. First confirm the underlying login is still valid (the
tool's own CLI `whoami`/status, or the cred file's mtime); if it is, RESPAWN the
server before asking the user to re-auth: `pgrep -fl <server>` -> kill the PID ->
re-call any tool (Claude Code relaunches stdio MCP servers on demand with fresh
creds). Only if respawn fails, or it's a REMOTE/OAuth MCP (no local process to kill),
ask the user to re-authenticate. Never run interactive `login` yourself (auth wall).
