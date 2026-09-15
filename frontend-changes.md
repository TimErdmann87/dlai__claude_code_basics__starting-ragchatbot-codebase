# Frontend Changes — Code Quality Tooling

Adds automatic code formatting and dev scripts for running quality checks.

The feature request named **black**, which only formats Python, while the scope was restricted to
the front end. Both halves are covered: black + isort for `backend/`, and **Prettier** for
`frontend/` — so the front-end files are actually formatted rather than left out of a
"code quality" change. One set of scripts drives both.

## What changed

### New files

| File | Purpose |
| --- | --- |
| `package.json` | Declares Prettier as the only npm dev dependency; `format` / `format:check` scripts scoped to `frontend/**/*.{html,css,js}`. `"private": true`, no build step. |
| `package-lock.json` | Lockfile so every machine gets the identical Prettier version. |
| `.prettierrc.json` | Prettier config (see below). |
| `.prettierignore` | Excludes `node_modules/`, `.venv/`, `__pycache__/`, `backend/chroma_db/`, `.playwright-mcp/`, and `docs/`. |
| `scripts/format.sh` | Auto-formats everything in place: isort → black → Prettier. |
| `scripts/check.sh` | Verifies formatting without writing; prints diffs, exits 1 if anything is unformatted. |
| `scripts/quality.sh` | Full gate: `check.sh` + `pytest`. Run before committing; suitable for CI. |

`docs/` is deliberately Prettier-ignored — `DocumentProcessor` parses those course files
line-by-line against an exact `Course Title:` / `Lesson N:` layout, so reformatting them would
break ingestion.

### Modified files

- **`pyproject.toml`** — added `black>=25.1.0` and `isort>=6.0.1` to the `dev` dependency group,
  plus `[tool.black]` (line length 88, target `py313`) and `[tool.isort]` (`profile = "black"` so
  the two tools never fight, with the `backend/` modules listed as `known_first_party` — they are
  imported as top-level names via pytest's `pythonpath`, so isort would otherwise sort them as
  third-party).
- **`.gitignore`** — added `.venv/` and `node_modules/`.
- **`README.md`** — new "Code Quality" section; Node.js 18+ noted as a prerequisite for the
  formatter only.
- **`CLAUDE.md`** — replaced the now-stale "no test suite, linter, or build step" line with the
  script list and a note about the pre-existing test failures.

### Reformatted front-end sources

All three front-end files were reformatted by Prettier — cosmetic only, no behavior change:

| File | Lines changed |
| --- | --- |
| `frontend/index.html` | +96 / −74 |
| `frontend/script.js` | +161 / −157 |
| `frontend/style.css` | +422 / −409 |

The front end had **mixed indentation** (some blocks 4-space, some 2-space, some misaligned) and
mixed quote styles; that is what most of the diff is. Specifically:

- **Consistent 2-space indentation** across HTML, CSS and JS, replacing the mix.
- **Double quotes** in JS and CSS (`'/api'` → `"/api"`, `content: '▶'` → `content: "▶"`).
- **Self-closing void elements** in HTML (`<meta ...>` → `<meta ... />`), lowercase `<!doctype html>`.
- **One selector per line** in CSS (`*, *::before, *::after` and `@keyframes` stops).
- **Expanded one-line rules** (`.message-content h1 { font-size: 1.5rem; }` → block form).
- **Long attribute lists wrapped** — the `data-question` buttons and the send-button `<svg>`.
- `&quot;` inside a `data-question` attribute became a single-quoted attribute holding literal
  `"` (identical after HTML parsing).
- Trailing newline added to `index.html`, which previously had none.
- Trailing whitespace and stray blank lines removed throughout.

Backend `.py` files were reformatted too (13 files), which is where the rest of the overall diff
comes from.

## Configuration

`.prettierrc.json`:

```json
{
  "printWidth": 100,
  "tabWidth": 2,
  "semi": true,
  "singleQuote": false,
  "trailingComma": "es5",
  "arrowParens": "always",
  "endOfLine": "lf",
  "htmlWhitespaceSensitivity": "css"
}
```

- `printWidth` 100 (120 for HTML via an override) — the existing markup is attribute-heavy, and
  the default 80 would have shattered nearly every tag onto multiple lines.
- `endOfLine: "lf"` keeps diffs stable on Windows, which is the primary dev platform here.
- `htmlWhitespaceSensitivity: "css"` lets Prettier re-indent only where CSS `display` makes
  whitespace insignificant, so re-wrapping the `<button>` elements cannot change rendering.

## Usage

```bash
./scripts/format.sh    # fix everything
./scripts/check.sh     # verify only (CI-friendly, writes nothing)
./scripts/quality.sh   # check.sh + pytest
```

Front-end only, without `uv`:

```bash
npm run format
npm run format:check
```

First run of `format.sh` / `check.sh` installs Prettier automatically if `node_modules/` is absent.

## Verification

- `./scripts/format.sh` — clean run; 13 Python files and all 3 front-end files reformatted.
- `./scripts/check.sh` — passes (idempotent: a second format pass is a no-op).
- `uv run pytest` — **28 passed, 3 failed**. The same 3 failures reproduce on the unmodified
  `HEAD` snapshot (verified via `git archive HEAD` into a temp dir), so they are pre-existing
  diagnostic failures in `test_rag_system_content_queries.py`, not caused by reformatting.
- Runtime smoke test — started `uvicorn app:app`, confirmed `GET /` returns 200 and serves the
  reformatted `index.html` byte-identical to the source file, and `GET /api/courses` returns all
  4 courses.
- Reviewed the front-end diff with `git diff -w` to confirm every change is whitespace, quoting,
  or wrapping — no semantic edits.

Tool versions: black 26.5.1, isort 9.0.1, Prettier 3.9.6.
