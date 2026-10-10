# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly is a Flask-based expense tracker built as a step-by-step teaching project. Some functionality is deliberately left as a stub for students to implement in later steps.

**Do not implement functionality that belongs to a future step unless the user explicitly asks for it.** Markers such as `TODO`, `coming in Step N`, `implement in Step N`, `student implementation`, `stub`, or `placeholder` indicate intentional gaps. Leave them alone unless they are part of the current request.

## Repository Layout

- Git root: `C:\Projects\expense-tracker`
- Flask app: `C:\Projects\expense-tracker\expense-tracker`
- Virtual environment: `C:\Projects\expense-tracker\venv` (one level above the app)

```text
expense-tracker/
├── venv/
└── expense-tracker/
    ├── app.py
    ├── database/db.py
    ├── templates/        # base, landing, login, register, terms, privacy
    ├── static/css/style.css
    ├── static/js/main.js
    ├── requirements.txt
    └── expense_tracker.db   # generated, gitignored — never commit
```

## Commands

Developed on Windows; Git Bash is preferred. Run commands from the app directory.

```bash
source ../venv/Scripts/activate        # PowerShell: ..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py                          # http://127.0.0.1:5001
pytest                                 # all tests
pytest path/to/test_file.py::test_name # single test
```

`pytest` and `pytest-flask` are installed. There is currently no `tests/` directory, no linter, and no frontend build step.

## Stack and Architecture

- **Backend:** Python, Flask, Jinja2, SQLite via the standard library `sqlite3`
- **Frontend:** HTML, CSS, vanilla JavaScript

The architecture is intentionally simple: a single `app.py` module, no blueprints, no application factory, one main stylesheet, and no JavaScript framework or build system. Do not introduce React, Vue, jQuery, Bootstrap JS, npm tooling, an ORM, or extra architectural layers unless explicitly requested.

## Routes

Real routes (render templates):

```text
/   /register   /login   /terms-and-conditions   /privacy-policy
```

Placeholder routes (return simple strings until their step is implemented):

```text
/logout   /profile   /expenses/add   /expenses/edit   /expenses/delete
```

**Authentication:** `login.html` and `register.html` already submit via `POST` and can display `{{ error }}`, but the routes currently accept `GET` only. POST handling belongs to a later step — do not implement it unless requested.

## Database

`database/db.py` is intentionally a stub. It will eventually provide `get_db()`, `init_db()`, and `seed_db()`.

`get_db()` should use `sqlite3`, set `row_factory`, and enable foreign keys. Always use parameterized queries — never build SQL with string concatenation.

## Templates

- All pages extend `templates/base.html`; never duplicate the full HTML document structure.
- `base.html` provides the navbar, footer (including Terms and Privacy links), and these blocks:
  - `title` — page title
  - `head` — page-specific CSS
  - `content` — page content
  - `scripts` — page-specific JavaScript
- Legal pages (`terms.html`, `privacy.html`) reuse `auth-section` / `auth-card` plus `legal-container` / `legal-card`. Keep legal content generic. Do not invent company names, addresses, laws, regulatory claims, or third-party providers unless the user supplies them.

## Styling

Main stylesheet: `static/css/style.css`. Design tokens live under `:root`:

```css
--ink*  --paper*  --accent  --radius-*  --font-display  --font-body
```

Fonts: DM Serif Display and DM Sans (Google Fonts).

- Reuse existing tokens and classes; avoid hard-coded colours where a token exists.
- Match existing typography, spacing, borders, and radius. Do not create a new visual style.
- Keep responsive behaviour intact.
- CSS used by only one page goes in that page's `head` block. Move it to `style.css` only if genuinely shared.

## JavaScript

- Vanilla JavaScript only; no libraries for simple interactions.
- `static/js/main.js` is an empty placeholder. Only add genuinely shared code there.
- Page-specific JavaScript goes in the page's `scripts` block.

**Landing page video modal** (`landing.html`, "See how it works"): plain HTML/CSS/JS with an embedded YouTube video. It must open on click, close via the close button or an outside click, stop the video on close, and lock page scrolling while open. Do not replace it with a framework.

## Working Rules

1. Read the relevant files (including `base.html` and `style.css` for UI work) before changing anything.
2. Follow existing patterns and make the smallest change necessary.
3. Preserve existing routes, navigation, forms, styles, layout, and behaviour. No unrelated refactoring.
4. If the user says "Do not modify any other files", treat it as strict. If another file seems necessary, explain why before touching it.
5. Avoid new dependencies. If one is genuinely required, explain why before adding it.
6. Never hard-code or commit credentials, passwords, API keys, or secrets.

## Validation

- **Backend changes:** run `pytest`; if no tests exist, confirm `python app.py` starts cleanly.
- **Template/UI changes:** confirm the route loads with no Jinja errors, existing pages and navigation still work, and the layout is reasonable on small screens.
- **JavaScript changes:** manually verify the interaction (e.g. modal opens, closes, video stops).

## Git

- Review `git status` and `git diff` before committing; commit only files related to the change.
- Do not commit unless the user asks or the task explicitly requires it.
- Commit message style: `area: short description` (e.g. `legal: add privacy policy page`).

## Completing a Task

Before reporting done: confirm the requested change works, nothing unrelated was modified, and tests/checks pass. Report concisely what changed, plus any assumptions or limitations. If a commit was made, include the message and hash.

## Instruction Priority

1. The user's current request
2. Explicit file-scope restrictions from the user
3. This `CLAUDE.md`
4. Existing project conventions
5. General coding preferences