# Lint Script Template

The `design-drift` skill generates `scripts/lint-design-drift.sh` at the target repo. The template below is parameterized — fill in the actual drift patterns detected for the codebase being fixed.

## Template

```bash
#!/usr/bin/env bash
#
# Design-drift lint for {{REPO_NAME}}.
#
# Enforces the conventions in DESIGN-SYSTEM.md §4 by grepping for known
# drift patterns. Run locally via `npm run lint:design` or in CI before
# merge. Exits non-zero if any drift is found.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0

section() {
  printf "\n\033[1m== %s ==\033[0m\n" "$1"
}

# 1. Banned brand hex literals. Fill in the actual brand-color hex values
#    detected in the source that shadow named tokens.
section "No raw brand-color hex (use semantic tokens)"
hex_pattern="{{BANNED_HEX_PIPE_SEPARATED}}"   # e.g. "#2a6a6a|#235858|#e8f2f2"
hex_matches="$(rg -n -i "$hex_pattern" {{SRC_PATH}} 2>/dev/null || true)"
if [ -n "$hex_matches" ]; then
  echo "$hex_matches"
  printf "\033[31mFAIL\033[0m — raw brand hex. Use the token utilities.\n"
  fail=1
else
  printf "\033[32mOK\033[0m — no raw brand hex.\n"
fi

# 2. Banned per-page status/channel/etc. dictionaries. Fill in the exact
#    identifier names detected as duplicated across pages.
section "No inline status dictionaries in pages"
dict_pattern="{{BANNED_DICT_NAMES_PIPE_SEPARATED}}"  # e.g. "statusBadge|channelColors|caseTypeBadge"
dict_matches="$(rg -n "const\s+(${dict_pattern})(Config)?\s*[:=]" {{PAGES_PATH}} 2>/dev/null || true)"
if [ -n "$dict_matches" ]; then
  echo "$dict_matches"
  printf "\033[31mFAIL\033[0m — per-page dict. Import from constants.\n"
  fail=1
else
  printf "\033[32mOK\033[0m — no inline dictionaries.\n"
fi

# 3. Banned native feedback patterns. Include only if the codebase has
#    migrated to a canonical toast lib (sonner, react-hot-toast, etc.).
section "No native alert() (use toast from {{TOAST_LIB}})"
alert_matches="$(rg -n '(^|[^a-zA-Z])alert\(' {{SRC_PATH}} 2>/dev/null || true)"
if [ -n "$alert_matches" ]; then
  echo "$alert_matches"
  printf "\033[31mFAIL\033[0m — alert(). Use toast.* from {{TOAST_LIB}}.\n"
  fail=1
else
  printf "\033[32mOK\033[0m — no alert() calls.\n"
fi

# 4. Non-fatal warning for arbitrary bracket hex.
section "Warn: arbitrary hex colors in bracket classes (review manually)"
bracket_hex="$(rg -n '(bg|text|border|ring|outline|fill|stroke|decoration|accent|caret|divide|from|to|via)-\[#[0-9a-fA-F]{3,8}\]' {{SRC_PATH}} 2>/dev/null || true)"
if [ -n "$bracket_hex" ]; then
  echo "$bracket_hex"
  printf "\033[33mWARN\033[0m — arbitrary hex. Verify it isn't tokenizable.\n"
else
  printf "\033[32mOK\033[0m — no arbitrary bracket hex.\n"
fi

echo
if [ $fail -ne 0 ]; then
  printf "\033[31mDesign-drift lint failed. See DESIGN-SYSTEM.md.\033[0m\n"
  exit 1
fi
printf "\033[32mDesign-drift lint passed.\033[0m\n"
```

## Parameters

- `{{REPO_NAME}}` — repo name from `package.json` or the folder name
- `{{BANNED_HEX_PIPE_SEPARATED}}` — the top-N brand hex literals that appear in source and shadow a named token, pipe-separated (e.g. `#2a6a6a|#235858|#e8f2f2`)
- `{{BANNED_DICT_NAMES_PIPE_SEPARATED}}` — identifier names detected as duplicate inline dicts, pipe-separated (e.g. `statusBadge|channelColors|caseTypeBadge`)
- `{{SRC_PATH}}` — the source root (e.g. `src/app`, `app`, `src`)
- `{{PAGES_PATH}}` — the pages folder (e.g. `src/app/pages`, `app/routes`). If the stack doesn't have a distinct pages folder, use the same as `SRC_PATH`.
- `{{TOAST_LIB}}` — the canonical feedback library in `package.json` (e.g. `sonner`, `react-hot-toast`). Omit check #3 entirely if no toast lib is in use.

## Notes

- Each check prints its own OK/FAIL line so the user sees exactly what passed and what didn't.
- Use `rg` (ripgrep) not `grep` — ripgrep respects `.gitignore` and is faster.
- The final warning section (#4) is intentionally non-fatal: arbitrary bracket hex may be legitimate one-off brand assets, charts, or intentional overrides.
- Keep the script short enough to review in one screen. Complexity here discourages adoption.
