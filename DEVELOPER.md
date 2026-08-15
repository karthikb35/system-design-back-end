# Developer Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Toolchain](#toolchain)
3. [Pre-commit hooks](#pre-commit-hooks)
4. [Running checks locally](#running-checks-locally)
5. [CI pipeline](#ci-pipeline)
6. [Required status checks](#required-status-checks)
7. [Branch protection](#branch-protection)
8. [Workflow for contributions](#workflow-for-contributions)

---

## Quick Start

```powershell
# 1. Install uv (if not already installed)
winget install --id astral-sh.uv

# 2. Install all dev dependencies (creates .venv/)
uv sync --dev

# 3. Install pre-commit hooks into .git/hooks/
uv run pre-commit install

# 4. Verify everything is green before your first commit
uv run pre-commit run --all-files
```

After step 3, every `git commit` automatically runs the full hook suite.

---

## Toolchain

All dev tooling is managed via **[uv](https://docs.astral.sh/uv/)** — a fast Python package manager.

| File | Purpose |
|---|---|
| `pyproject.toml` | Project metadata + dev dependency group |
| `uv.lock` | Pinned lockfile — guarantees local == CI |

Dev dependencies (pinned in `uv.lock`):

| Package | Version | Role |
|---|---|---|
| `ruff` | 0.16.2 | Lint (pyflakes + pycodestyle + pyupgrade) |
| `isort` | 8.0.1 | Import-order enforcement |
| `blacken-docs` | 1.20.0 | Format Python code blocks in Markdown files |
| `pre-commit` | ≥4.0 | Git hook runner |
| `html5lib` | ≥1.1 | HTML parse validation for study-guide books |
| `cssutils` | ≥2.11 | CSS parse validation for architects-path.css |
| `lxml` | ≥5.3 | Tree-builder backend for html5lib |

> **Pinning:** `uv.lock` is committed. Run `uv lock --upgrade` to update all
> dependencies, then commit the refreshed lockfile.

---

## Pre-commit hooks

Config lives in `.pre-commit-config.yaml`. Hooks run on every `git commit`
and can also be run manually with `uv run pre-commit run --all-files`.

### Hook inventory

| Hook | Source | What it checks |
|---|---|---|
| `trailing-whitespace` | pre-commit-hooks | No trailing spaces (excludes `.ipynb`, `.md`) |
| `end-of-file-fixer` | pre-commit-hooks | Files end with exactly one newline (excludes `.ipynb`) |
| `check-yaml` | pre-commit-hooks | Valid YAML syntax in all `.yml`/`.yaml` files |
| `check-json` | pre-commit-hooks | Valid JSON syntax (excludes `.ipynb`) |
| `check-merge-conflict` | pre-commit-hooks | No unresolved conflict markers |
| `check-added-large-files` | pre-commit-hooks | No file > 2 MB added by accident |
| `mixed-line-ending` | pre-commit-hooks | Normalise to LF (excludes `.ipynb`) |
| `ruff` | ruff-pre-commit | Lint all `.py` files; auto-fixes safe issues |
| `isort` | isort | Sort imports in all `.py` files |
| `blacken-docs` | blacken-docs | Reformat Python blocks in `*.md` files |
| `study-guide-html-css` | local | Parse all HTML books + CSS (see below) |

### HTML / CSS validation hook

`study-guide/check_html.py` validates every `*.html` file in `study-guide/`:

1. **HTML parse** — `html5lib` strict parser; exits non-zero on malformed markup.
2. **Broken links** — every relative `href` and `src` must resolve to a real file in `study-guide/`.
3. **CSS reference** — every book must link `architects-path.css` (books that embed CSS inline are exempt via `CSS_LINK_EXEMPT` set).
4. **CSS parse** — `cssutils` scans `architects-path.css` for unknown `@`-rules; CSS custom properties (`var(--x)`) are intentionally silenced.

Run it standalone:

```bash
uv run python study-guide/check_html.py
```

---

## Running checks locally

### Run everything (recommended before opening a PR)

```bash
uv run pre-commit run --all-files
```

### Run individual checks

```bash
# Lint Python
uv run ruff check .

# Fix auto-fixable lint issues
uv run ruff check --fix .

# Import order
uv run isort --check-only --diff .
uv run isort .           # auto-fix

# Markdown code blocks
uv run blacken-docs $(git ls-files '*.md')

# HTML / CSS books
uv run python study-guide/check_html.py

# Curriculum self-tests (standard library only, no install needed)
python 09-concurrency/production_code.py
python 10-networking-security-testing/production_code.py
```

### Ruff configuration

Ruff is configured in `ruff.toml`. Key decisions:

| Rule | Status | Reason |
|---|---|---|
| `E501` (line length) | Ignored | Long illustrative lines are intentional in didactic code |
| `E701` (compact `if x: raise`) | Ignored | Common notebook one-liner pattern (matches E702 exemption) |
| `E702` (semicolons) | Ignored | `a = 1; b = 2` compact notation used in worked examples |
| `**/*.ipynb` | Excluded | ruff mis-parses UTF-8 arrows in f-strings as invalid syntax on Windows |

---

## CI pipeline

The CI workflow (`.github/workflows/ci.yml`) runs on every push and pull request.

### Jobs

```
ci.yml
├── lint                   # ruff + isort + blacken-docs  (via uv)
├── html-css-check         # study-guide HTML/CSS validation  (via uv)
├── module-selftests       # py3.11 / py3.12 / py3.13  (stdlib only)
└── microservices          # rest / grpc / graphql  ×  py3.11 / py3.12 / py3.13
    └── (9 matrix jobs)
```

### Lint job details

The `lint` job installs dependencies with `uv sync --dev --frozen` (exact lockfile
versions, no network resolution at runtime) and runs:

```yaml
- name: ruff (lint)
  run: uv run ruff check .

- name: isort (import order)
  run: uv run isort --check-only --diff .

- name: blacken-docs (Markdown code blocks)
  run: uv run blacken-docs $(git ls-files '*.md')
```

### HTML & CSS check job details

```yaml
- name: Install HTML/CSS check dependencies via uv
  run: uv sync --dev --frozen

- name: Validate HTML books and CSS
  run: uv run python study-guide/check_html.py
```

Checks all 10 books in `study-guide/` plus `architects-path.css`.

---

## Required status checks

The following checks **must be green** before any PR can be merged into `main`:

| Status check | What it runs |
|---|---|
| `Lint (ruff · isort · blacken-docs)` | Full Python lint suite via uv |
| `HTML & CSS check (study-guide)` | `check_html.py` — parse, links, CSS |
| `Curriculum module self-tests (py3.12)` | `09-concurrency/production_code.py` + `10-networking-security-testing/production_code.py` |
| `Curriculum module self-tests (py3.13)` | Same, on Python 3.13 |
| `rest-ecommerce tests (py3.13)` | pytest suite for the REST microservice |
| `grpc-ecommerce tests (py3.13)` | pytest suite for the gRPC microservice |
| `graphql-ecommerce tests (py3.13)` | pytest suite for the GraphQL microservice |

> All 7 checks are enforced by a GitHub branch protection ruleset on `main`.
> The ruleset uses `~DEFAULT_BRANCH` so only `main` is protected — feature
> branches can be pushed freely.

---

## Branch protection

`main` is protected by two overlapping rules:

### Classic branch protection (`main` pattern)
- Requires all 6 required status checks to pass
- Requires changes to go through a pull request (0 approvals needed — solo repo)
- `enforce_admins: false` — repo owner can bypass

### Repository ruleset (ID 20883378)
- Scope: `~DEFAULT_BRANCH` only
- Rules: no-deletion, no-force-push, required status checks, pull request required
- **Bypass actor:** `@karthikb35` (actor type: User, bypass mode: always)

The bypass actor lets the sole owner merge their own PRs without a second reviewer,
while still requiring CI to pass.

---

## Workflow for contributions

```
main  (protected)
 │
 └─► feature/my-change
      ├── write code
      ├── git commit          # pre-commit hooks fire automatically
      ├── git push origin feature/my-change
      ├── gh pr create --base main --head feature/my-change
      ├── wait for CI  (all 7 checks green)
      └── gh pr merge --squash
```

### Step-by-step

```bash
# 1. Branch off main
git checkout main && git pull
git checkout -b feature/my-topic

# 2. Make changes, commit (hooks run automatically)
git add -A
git commit -m "feat: ..."   # pre-commit runs here

# 3. If hooks auto-fixed files, stage and re-commit
git add -A && git commit --amend --no-edit

# 4. Push and open PR
git push origin feature/my-topic
gh pr create --base main --head feature/my-topic --title "..." --body "..."

# 5. Once CI passes, merge
gh pr merge <number> --squash --delete-branch
```

### Fixing a failing CI check

| Check | Common failure | Fix |
|---|---|---|
| `ruff` | New lint violation | `uv run ruff check --fix .` then commit |
| `isort` | Wrong import order | `uv run isort .` then commit |
| `blacken-docs` | Unformatted Markdown code block | `uv run blacken-docs $(git ls-files '*.md')` then commit |
| `HTML & CSS check` | Broken link or missing CSS ref | Run `uv run python study-guide/check_html.py` locally, fix the HTML/CSS |
| `module-selftests` | Self-test assertion failed | Run `python 09-concurrency/production_code.py` locally |
| `microservices` | Test failure | `cd protocol-microservices/<repo>; pytest` locally |
