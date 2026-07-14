---
name: design-drift
description: "Use this skill when the user says 'design-drift', '/design-drift', 'fix design drift', 'run design drift', 'audit and fix design drift', or asks to bring a codebase back in line with its design system. Extracts the codebase's design language into design-model.yaml (directly or via hue), audits drift against it (directly or via design-audit), auto-fixes safe patterns (hex-to-token codemods, centralized constants, drift-lint script), and produces a focused handoff of only the decisions that genuinely need human review. Designed to run autonomously in a fresh AI session — does not require upstream skills to be interactive. Do NOT trigger automatically for generic refactor or UI tasks."
version: 1.1.0
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
---

# Design Drift Fixer

You take a codebase that has accumulated design drift — raw hex literals shadowing tokens, duplicated status dictionaries across pages, ad-hoc padding variations, inconsistent feedback patterns — and bring it back in line with its own design language.

The **goal** is to reduce the gap between `design-model.yaml` (the language the codebase claims to have) and the actual source code (what it does). The **output** is a codebase that matches its own system, plus enforcement scaffolding that prevents re-drift.

This skill is an **action tool**, not an analysis tool. If nothing is drifting, the skill returns silently. Do not invent work to justify the run.

---

## Principles

These four principles override everything else in this file. When in doubt, re-read this section.

### 1. Composition over reimplementation

`design-drift` is **orchestration plus remediation**, not a rewrite of upstream skills. Analysis delegates to `hue` (for extracting the language) and `design-audit` (for cataloging drift). The unique value lives in Phase 4 onward — translating findings into concrete fixes.

Never re-implement token extraction or drift detection inline. If the upstream skills produce an unexpected shape, fail loudly with a clear message, do not silently degrade.

### 2. Silent success is a valid outcome

If nothing needs a human decision, the skill says so explicitly:

> **Handoff:** None. The codebase is aligned with `design-model.yaml` within tolerance. Auto-fixes applied.

Do not generate theoretical polish suggestions. A skill that always produces handoff items trains users to ignore them. The audit artifact (HTML + markdown from `design-audit`) is always produced for users who want to explore — the handoff section is strictly "things I cannot fix alone."

### 3. Handoff thresholds are load-bearing

Every handoff-worthy finding must pass a threshold test. See the table in §3 of this file. A pattern repeated twice is not a primitive extraction candidate. A token that shadows its palette value by one hex is a real finding. A value that's visually distinct but semantically identical is a question for the user.

If a finding does not clearly pass its threshold, it does not appear in the handoff. It may appear in the full design-audit artifact for the user to review on their own.

### 4. Auto-fix only the unambiguous

The line between "safe to automate" and "hand off" is drawn where human judgment stops being optional. A codemod from `bg-[#2A6A6A]` to `bg-teal-600` when `design-model.yaml` defines `teal-600: #2A6A6A` is safe — the mapping is mechanical. Extracting a primitive is not safe — the name, prop shape, and which properties vary are all design decisions.

When uncertain whether a fix is safe, hand off. The cost of a wrong auto-fix (user rolls it back, loses trust in the tool) is higher than the cost of a handoff (user spends 10 minutes making the call).

---

## Scope

**In scope:**
- Extract the codebase's design language via `hue` (local-codebase input).
- Audit drift against that language via `design-audit`.
- Auto-fix unambiguous drift: token codemods, centralized constants scaffolding, drift-lint script.
- Generate a concise handoff for decisions only the user can make.
- Write a `DESIGN-SYSTEM.md` at repo root that consolidates the observation, the rules, and any outstanding handoffs.

**Out of scope:**
- Designing new primitives or tokens (`hue` does that).
- Running without a codebase to point at — the skill operates on a local repo, not a URL or a brand name.
- Fixing drift the user hasn't asked about. This skill never extends into general refactoring.
- Removing code the user may still need (dead scaffolding is flagged in the handoff, not deleted automatically — see §4.4).

---

## Workflow

Follow this sequence. Each phase has explicit outputs — check that you have them before advancing.

### Phase 1: Preflight

1. Confirm the working directory is a repo (`.git/` present). If not, fail early with a clear message.
2. Detect the stack. Look at `package.json`, `pyproject.toml`, etc. This skill has been validated on React + Vite + Tailwind v4 + Radix (shadcn-style). Other stacks may work but flag reduced confidence.
3. Note the current branch name for the final summary.

### Phase 2: Extract the language

Two valid paths. Pick whichever gets you a well-formed `design-model.yaml` without blocking on user input. The skill is not opinionated about which path runs — only that the output is complete and machine-readable.

**Path A — Existing artifact.** If `design-model.yaml` already exists at `<repo>/` or `<repo>/.design/` and is less than 7 days old, use it. This is the fast-path for repeat runs.

**Path B — Direct extraction (default for first run).** Synthesize `design-model.yaml` yourself by reading the codebase. This is what you do when no prior model exists and running `hue` interactively would block on user-gated phases (Confirm Direction, Token Preview). The source data is unambiguous — every field below comes from a specific file:

1. **Colors.** Read the theme file (`src/styles/theme.css`, `app/globals.css`, `tailwind.config.*`, etc. — wherever CSS custom properties or Tailwind `@theme` blocks live). Extract:
   - Neutral ramp (whichever gray-family the repo uses)
   - Brand palette (the custom-named color, typically `{brand-name}-{50..950}`)
   - Status colors (status-like tokens, or the Tailwind scales observed in status badges)
   - All semantic tokens: `--background`, `--primary`, `--muted`, `--accent`, `--destructive`, `--border`, etc.
2. **Typography.** Read `fonts.css` or equivalent + the `@layer base` typography rules. Extract font-family stack, weights, and size scale. Note `system`/`absent` if no font is explicitly loaded.
3. **Spacing, radii, elevation, motion.** Grep `src/app/components/ui/` primitives for the actual values used. The primitives layer is the de-facto system — treat it as authoritative.
4. **Components.** Inventory every file in the UI primitives folder. Each becomes an entry under `components:` with `source: observed` and the file path.

Write the result to `<repo>/design-model.yaml` following the schema in `references/design-model-schema.md`.

**Path C — Skill invocation (when available and non-interactive).** If `hue` supports a non-interactive CLI flag (`--auto-confirm`, `--no-prompt`, etc.) and the current session can invoke it, do so. This path exists for future versions of `hue` that support clean composition. As of skill v1.0.0, `hue` does not support this — do not try to invoke it expecting it to run autonomously.

**Fail-loud gate:** Whichever path produced the file, verify the YAML parses and contains at minimum: `primitives.colors`, `tokens.colors`, `tokens.typography`, `tokens.spacing`, `tokens.radii`. If any are missing, stop and tell the user the extraction produced an unexpected shape — do not proceed with a partial model.

### Phase 3: Audit the drift

Same two-path pattern as Phase 2. The goal is a complete drift inventory in a form Phase 4 can classify against thresholds.

**Path A — Existing audit artifact.** If `design-system-audit.md` exists at `<repo>/` and is less than 7 days old, use it. Parse Section 6 (Observations & Gaps) into three buckets:
- **Inconsistencies** (e.g. raw hex shadowing tokens, duplicated dicts)
- **Missing abstractions** (e.g. 4+ inline StatCards, 3+ empty states)
- **Opportunities for standardization** (partial tokenization, dead scaffolding)

**Path B — Direct drift scan (default for first run).** Walk the codebase yourself against the seven drift categories from the Phase 4 threshold table. For each category, run targeted searches (`rg` / `grep` / `glob`) to establish ground truth:

1. **Hex-shadowing-token.** For each hex in `primitives.colors` (from Phase 2's `design-model.yaml`), search the source tree for raw-hex occurrences (`bg-[#xxx]`, `text-[#xxx]`, inline `style={{ ... }}` hex values). Record each hit with its file:line.
2. **Duplicated status dicts.** Search for `const X = { ... }` patterns where identifier names match status-like conventions (`*Badge`, `*Colors`, `*Config`). Cluster by identifier name and compare values across files to find true duplicates vs name collisions across semantic concepts.
3. **Inline primitive patterns.** Search for repeated JSX patterns that could have been primitives: card-with-big-number (StatCard), icon-circle-title-description (EmptyState), title+subtitle+backArrow (PageHeader). Count occurrences and measure variation in padding / typography / color.
4. **Token palette drift.** Compare every color referenced in source (Tailwind utilities or CSS vars) against `design-model.yaml`'s token definitions. Flag references that are "close but not identical" to a defined token.
5. **Dead scaffolding.** For each primitive in the UI folder, count non-self-referential imports. Zero imports = candidate. Cross-check against `DESIGN-SYSTEM.md` for intentional-future-use annotations.
6. **Feedback patterns.** Search for `alert(` calls, custom-toast implementations, and unused toast-library imports. Compare installed deps to actual usage.
7. **Hardcoded project/brand strings.** Search for string literals matching known project/brand names where the value should derive from runtime state.

Write a minimal audit record to `<repo>/design-system-audit.md` with at least the three bucket sections, each listing findings with file:line citations. You do not need to produce the full HTML Storybook output from `design-audit` — that's an optional enrichment, not a hard dependency.

**Path C — Skill invocation (when available and non-interactive).** If `design-audit` supports a non-interactive run, invoke it. As of skill v1.0.0, it does not — the skill prompts for confirmation on ambiguous findings. Plan for this to be fixed upstream later.

**Fail-loud gate:** Whichever path produced the audit, verify it contains at minimum one section for each of the three buckets (Inconsistencies / Missing abstractions / Opportunities for standardization). If a bucket is absent, re-run the scan. Empty buckets ("no findings") are fine — that's a valid healthy-codebase outcome. Missing buckets ("we forgot to check this") are not.

### Phase 4: Classify findings (auto-fix vs handoff)

For every finding from Phase 3, classify it using the threshold table:

| Finding type | Auto-fix when... | Handoff when... |
|---|---|---|
| **Hex-shadowing-token** | Raw hex literal equals a value in `primitives.colors`, and only one token matches that hex | Multiple tokens map to the same hex (ambiguous which to use), or the hex is off by a shade |
| **Duplicated status dict** | ≥2 files contain a near-identical dictionary for the same semantic concept | Each dict uses a different color family for the same status (design disagreement, needs user decision on canonical) |
| **Inline primitive pattern** | Never auto-fix primitive extraction | Pattern appears ≥3 times with variation in ≥2 properties (padding, color, typography), AND no existing primitive covers the pattern |
| **Token palette drift** | Never auto-fix | `design-model.yaml` defines a token at value X, code references value Y that is close but not identical |
| **Dead scaffolding** | Never auto-fix removal | Dependency in `package.json` + zero imports across `src/` + not cited in `DESIGN-SYSTEM.md` as intentional-future-use |
| **Feedback pattern drift** | If `sonner` or another canonical toast lib is installed, migrate `alert()` calls | Custom toast implementations with bespoke behavior (e.g. live countdowns) that don't trivially map to the canonical lib |
| **Hardcoded project/brand strings** | Can derive from runtime state (props, store, params) | Cannot be derived without architectural changes |

Findings that fail their handoff threshold (e.g. pattern repeated only twice) are **dropped**. They live in the design-audit artifact for users who want to explore.

### Phase 5: Execute auto-fixes

For each auto-fix classified in Phase 4:

1. **Hex codemod.** For each `palette_hex → utility` mapping from the design model, run sed/awk across `src/**/*.{ts,tsx,js,jsx}`. Replace `bg-[#HEX]` → `bg-<token>`, `text-[#HEX]` → `text-<token>`, etc. Do not touch inline styles (`style={{}}`) — those need CSS custom property references, not utility classes. Note them in the handoff instead.

2. **Constants file scaffold.** Create `<src>/lib/constants/` (or the idiomatic location for the stack). For each duplicated dict found, generate one file per semantic concept. Do not delete inline dicts — let the user confirm the canonical color family before removing duplicates. Instead, the handoff includes "migrate N pages from inline to the constants file."

3. **Drift-lint script.** Write `<repo>/scripts/lint-design-drift.sh` (or platform-idiomatic location). Parameterize with the specific drift patterns detected. See `references/lint-script-template.md`. Wire it into `package.json` scripts as `lint:design` if a `package.json` exists.

4. **Sonner migration.** If `sonner` is in `package.json` and there are `alert()` calls or inline custom-toast state, migrate them. Add a `<Toaster />` to the root layout file if not already present.

5. **Hardcoded project-string fix.** If findings include strings like "In re Varsity Brands" in files that should read from runtime state, replace with a store/props lookup. Only fix when the lookup source is obvious — otherwise hand off.

Track every fix applied for the summary. A fix that doesn't apply cleanly (e.g. a file was modified in a way that breaks the find-and-replace) is escalated to the handoff with the specific file:line.

### Phase 6: Generate the handoff

Write `<repo>/DESIGN-SYSTEM.md` with three sections:

1. **The Language** — brief summary of `design-model.yaml`. Link to the full YAML.
2. **What was fixed** — bulleted list of auto-fixes applied in this run.
3. **Handoff** — ordered list of decisions that need human review.

For the handoff section, each item has:
- A plain-English statement of the finding ("Your claim-status badge colors differ between the ClaimsQueue and CaseDetail pages.")
- The specific decision needed ("Pick one family to canonicalize: `*-50/600` soft or `*-100/800` bold.")
- Concrete file citations
- An explicit next action ("Once you decide, I can propagate that choice across all pages in one commit.")

**Critical:** if Phase 4 produced zero handoff items, write "Handoff: None. The codebase is aligned with `design-model.yaml` within tolerance. Auto-fixes applied; no human decisions needed." and stop. Do not invent handoff items.

### Phase 7: Report

Print a concise summary to the user:
- Path to `DESIGN-SYSTEM.md`
- Count of auto-fixes applied (grouped by type)
- Count of handoff items (often zero, which is the success case)
- Suggest `npm run lint:design` to verify no new drift

Do not re-iterate the full content of `DESIGN-SYSTEM.md`. The user will read it.

---

## Quality Standards

These apply regardless of what the upstream skills produce.

### Auto-fixes must be reversible with `git restore`

Every auto-fix is a small, atomic change that touches code the user can roll back in one command. Do not commit anything — leave changes staged/unstaged so the user reviews before committing.

### The handoff is not a to-do list

Every handoff item is a **single decision**, not a project plan. "Decide the canonical status family (soft vs bold)" is a handoff item. "Extract StatCard, EmptyState, and PageHeader, then migrate all their inline usages" is three items, not one.

### Thresholds are empirical, not aspirational

The thresholds in Phase 4 are the ones empirically validated on the Atticus prototype. If a future run of this skill on a different codebase produces obviously wrong results (too many handoffs, too few), the thresholds get tuned — do not paper over the mismatch with prose.

### Never delete code the user may want

Dead-dependency removal, primitive extraction, and component consolidation are never auto-applied. The handoff suggests them; the user decides. When in doubt, preserve.

### Trace every finding to a file:line citation

Every handoff item must be anchored to `file:line` citations from the design-audit output. If you can't cite it, don't write it.

---

## Anti-patterns

- **No "consider X" language in the handoff.** Every handoff is a decision, not a suggestion. If you find yourself writing "consider", reframe as "decide".
- **No running without `hue` or `design-audit`.** If either upstream skill is unavailable, stop with a clear message. Do not approximate their output.
- **No over-eager codemods.** A hex literal in a comment or a string-embedded example is not drift. Only replace hex in class attributes and CSS properties.
- **No scope creep.** Do not fix bugs, add features, or refactor logic unrelated to design drift. Stay in your lane.
- **No silent degradation.** If upstream output is malformed, fail loud. Do not produce a best-guess result — the user has no way to know it's wrong.
- **No invented thresholds.** Do not relax the handoff thresholds to produce more output. The tool's value is in its restraint.

---

## Outputs

After a successful run, the user has:

1. `<repo>/design-model.yaml` — machine-readable language spec (from `hue`)
2. `<repo>/design-system-audit.md` + `.html` — diagnostic report (from `design-audit`)
3. `<repo>/DESIGN-SYSTEM.md` — consolidated language + fix summary + handoff (from this skill)
4. `<repo>/scripts/lint-design-drift.sh` — drift guard tuned to this codebase
5. `<repo>/src/**/lib/constants/*` — centralized status/channel/etc. dictionaries
6. Auto-fixed files in the working tree, ready for the user's review

If handoff is empty, only artifacts 1–4 are meaningfully updated. The user sees "no decisions needed" and moves on. That is the intended outcome of a healthy codebase.

---

## Invocation

The skill is invoked via:
- "design-drift"
- "/design-drift"
- "fix design drift"
- "audit and fix design drift"
- Direct request to bring a codebase in line with its design system

Never trigger automatically. Generic UI or refactor tasks should use other skills or direct tool calls.
