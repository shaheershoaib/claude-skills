# Shaheer's Claude Code skills

A snapshot of the skills in my `~/.claude/skills`, shared so you can see the setup and lift
what's useful. 21 skills; see notes at the bottom for the one that's deliberately not here.

## Install

Drop any skill folder into your own `~/.claude/skills/` (or copy the ones you want):

```bash
cp -R skills/<name> ~/.claude/skills/
```

Restart Claude Code and it'll discover them. Each folder's `SKILL.md` documents itself
(what it does, when it triggers) - that's the source of truth.

## What's here

**The dev pipeline (how I ship work):**
- `ship` - the work-set execution loop: land a set of changes end to end (chat asks, tickets, a plan doc) under verification guardrails.
- `fanout` - the batching decision: which items run in parallel vs serialize, the wave schedule, per-item risk tier.
- `graphify` - a local AST knowledge graph of a codebase (what-renders-what); the substrate the gates + fanout query.
- `pre-commit` - runs the project's real gate commands (typecheck / lint / tests) fail-closed before any "done" claim.
- `git-commit` - identity-aware conventional commits.
- `pr-creator` - opens a PR with a Conventional-Commits title + a consistent body.
- `github-pr-review` - reviews someone else's PR via the gh CLI.
- `parity-builder` / `parity-sweep` - build/port a surface from a prototype to leaf-level parity, and verify it without missing behind-a-click detail.
- `session-handoff` - a structured end-of-session summary so a fresh session continues.
- `setup-audit` - grades your `~/.claude` setup and catches silent breakage (broken skills, dead hooks, missing MCP entry files).

**Design:**
- `design-audit` - documents the design system that already exists in a codebase.
- `design-drift` - brings a codebase back in line with its design system (auto-fixes safe patterns).
- `hue` - a meta-skill that generates new design-language skills.
- `frontend-design`, `web-design-guidelines`, `visual-explainer` - distinctive UI guidance, a Web Interface Guidelines review, and self-contained HTML explainers (this handbook style).

**Misc:**
- `codex` - runs the OpenAI Codex CLI for a cross-model second opinion on a diff.
- `watch` - watches a video (downloads, frames, transcript) and answers questions about it.
- `system-explainer` - teaches how an unfamiliar system works, and can generate a standalone onboarding web app.
- `find-skills` - discovers/installs skills.

## Setup notes

Some skills pair with tooling you'll set up separately:
- `watch` uses `GROQ_API_KEY` or `OPENAI_API_KEY` in `~/.config/watch/.env` (only for the Whisper transcript fallback; captions work without it).
- `codex` needs the OpenAI Codex CLI installed (`npm i -g @openai/codex`).
- `system-explainer/onboarding-template` ships source only - run `npm install` inside it (I stripped `node_modules`).
- A few (`find-skills`, `frontend-design`, `web-design-guidelines`) ship with Claude Code / plugins anyway - included for completeness.
- Not a skill, but related: my verification layer `receipts` is a public plugin - `claude plugin marketplace add shaheershoaib/receipts` then `claude plugin install receipts`.

## Not included: security-audit / VibeSec

I run a `security-audit` skill locally, but it's the **paid VibeSec Pro** (purchased, proprietary,
no redistribution license) - so it's not mine to hand over. You can get VibeSec directly:
- **Free** (Apache-2.0, ~60-70% coverage): https://github.com/BehiSecc/VibeSec-Skill
- **Pro** (fuller coverage, one-time payment): https://vibesec.sh

Everything else here is fair game.
