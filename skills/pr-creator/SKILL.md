---
name: pr-creator
description: Use this skill when asked to create a pull request (PR). Enforces Conventional Commits titles, the repo's PR template, a consistent description style (Summary / Why / Test plan / Notes), and safety rails around pushing to main.
---

# Pull Request Creator

Creates high-quality pull requests following the standards below. Project-local rules in `CLAUDE.md` and `.github/pull_request_template.md` override these defaults.

## Workflow

### 1. Read project conventions first

Before touching anything, check for project-specific overrides:

- `CLAUDE.md` (repo root) for sections on commit conventions, branch conventions, writing conventions, and pull requests
- `.github/pull_request_template.md` for the PR body structure
- `.github/pull_request_template/` directory if multiple templates exist; ask which one or pick by context

Project rules win in conflict with this skill.

### 2. Branch management (safety rail)

**CRITICAL: never work on or push to `main`.**

```bash
git branch --show-current
```

If on `main`, create a new branch:

```bash
git checkout -b type/short-kebab-description
```

Branch name follows the same type vocabulary as commits (see step 3).

### 3. Stage and commit changes

Stage files by name. **Never use `git add .` or `git add -A`** (sweeps in secrets, generated artifacts, autocorrect cruft):

```bash
git status
git add path/to/file1 path/to/file2
```

Commit using Conventional Commits format:

```
type(scope): short summary in imperative mood (max 72 chars, no period)
```

Type vocabulary: `feat | fix | chore | refactor | docs | perf | test | style | build | ci | revert`

Scope is optional and project-specific. Read `CLAUDE.md` for the project's scope vocabulary.

For multi-line messages with a body, use HEREDOC:

```bash
git commit -m "$(cat <<'EOF'
type(scope): short summary

Body explaining WHY (not WHAT). Wrap at 72 chars. Blank line above.
EOF
)"
```

If commits need a specific author for attribution (e.g., deploy webhooks tied to a different email), pass `--author`:

```bash
git commit --author="name <email>" -m "..."
```

### 4. Preflight (quality gates)

Run the project's quality checks. Try in this order, run whichever exist:

```bash
# Preferred unified script
npm run preflight 2>/dev/null

# Otherwise, run the standard trio individually
npm run type-check 2>/dev/null || npx tsc --noEmit
npm run lint:design 2>/dev/null || npm run lint 2>/dev/null
npm run build 2>/dev/null
npm run test 2>/dev/null
```

Address any failures before pushing.

### 5. Push to remote (multi-remote aware)

Detect remotes before pushing. Some repos have several (e.g., worktrees with both `origin` and a sibling remote):

```bash
git remote -v
```

If a single remote, push there. If multiple, pick the one matching the target repo. Ask the user if ambiguous:

```bash
git push -u <remote> HEAD
```

**Verify current branch is NOT `main` before pushing.**

### 6. Draft the PR description

If `.github/pull_request_template.md` exists, mirror its structure exactly. Otherwise use this default:

```markdown
## Summary

- 1-3 bullets describing what this PR changes.

## Why

Optional but encouraged. Explain motivation, not the diff. Link Slack threads, Notion tickets, design notes.

## Test plan

- [ ] Specific command (e.g. `npm run type-check`)
- [ ] Specific user step (e.g. "visit /reports/ingestion, hard-refresh, confirm bars stay identical")

## Notes

Optional. Deploy implications, related PRs (full URLs), follow-ups, screenshots.
```

### 7. Description style rules

These rules apply on top of whatever template the repo uses:

- **Summary**: 1-3 bullets. Not paragraphs. What changed, in plain language.
- **Why**: motivation only. Don't restate the diff. If there's nothing non-obvious, drop the section.
- **Test plan**: specific commands or specific user actions. "Tested manually" is not a test plan; "visited /X, hard-refreshed, confirmed Y" is.
- **Notes**: deploy implications, related PRs with full URLs, follow-ups, screenshots.
- **Length**: short. If a section has nothing to add, write "n/a" or remove it.
- **No AI attribution footers**: no "Generated with Claude Code", "Co-Authored-By: Claude", or any AI tool branding. PRs read as if a human wrote them.
- **ASCII punctuation only**: no en-dash (U+2013), no em-dash (U+2014). Use ASCII hyphens, colons, commas, or restructure. Curly quotes out too; use straight.

### 8. Create the PR

Use `gh` CLI with `--body-file` to avoid shell-escaping issues with markdown:

```bash
# Write the drafted body to a temp file
cat > /tmp/pr-body.md <<'EOF'
## Summary
...
EOF

# Create the PR
gh pr create \
  --title "type(scope): summary" \
  --body-file /tmp/pr-body.md \
  --base main

# Clean up
rm /tmp/pr-body.md
```

- **Title**: Conventional Commits format (same as commits).
- **Base**: the repo's integration/default branch. That is `main` only when the
  project has no designated integration branch - many projects integrate on a
  long-lived branch instead (check the project skill / CLAUDE.md / memory;
  e.g. a `develop` or `release/*` style branch). Never base on an
  unrelated feature branch.

## Safety principles

- **Never push directly to `main`/the default branch.** Highest priority.
- **Never use `git add .` or `git add -A`.** Stage by name.
- **Never skip hooks** (`--no-verify`) unless the user explicitly asks.
- **Never force-push to `main`.**
- **Never amend an existing commit** unless the user explicitly asks (hooks reject differently and amending can destroy work).
- **Read `CLAUDE.md` first** if it exists. Project-local rules win.
- **No AI attribution footers** in commits or PR descriptions - UNLESS the
  project's own rules require a trailer (some repos mandate a specific
  `Co-Authored-By:` line; the project rule wins, per the precedence above).
- **ASCII only** in all writing (commits, branches, comments, docs, PR descriptions).
