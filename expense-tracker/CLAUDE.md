# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly is a Flask expense tracker built in numbered steps as a teaching project. Several parts are deliberately stubs for "students" to fill in later. Comments such as "coming in Step N" mark this work. Don't implement a stubbed step unless asked.

The git repo root is the parent directory (`C:\Projects\expense-tracker`). The Flask app lives in this `expense-tracker/` subfolder. The virtualenv is `../venv`, one level up from the app.

## Commands (Windows)

```bash
# activate venv (Git Bash); PowerShell: ..\venv\Scripts\Activate.ps1
source ../venv/Scripts/activate
pip install -r requirements.txt

python app.py          # dev server, debug mode, http://127.0.0.1:5001
pytest                 # run tests
pytest path/to/test_file.py::test_name   # single test
```

pytest and pytest-flask are installed, but there is no `tests/` directory yet. There is no linter or build step.

## Architecture

- **`app.py`**: the only Flask module, with no blueprints or app factory. Real routes render templates: `landing`, `register`, `login`, `terms_and_conditions` and `privacy_policy`. The placeholder routes (`logout`, `profile`, and the expenses add/edit/delete routes) return plain strings until their step is implemented.
- **`database/db.py`**: a stub. It is meant to provide `get_db()`, which returns a SQLite connection with `row_factory` set and foreign keys on. It will also provide `init_db()` (`CREATE TABLE IF NOT EXISTS`) and `seed_db()`. The DB file `expense_tracker.db` is gitignored. Use the stdlib `sqlite3` module, not an ORM.
- **Templates**: Jinja2. Every page extends `templates/base.html`, which holds the navbar and footer (including the Terms and Privacy links). `base.html` exposes four blocks: `title`, `head` (page-specific `<style>`), `content` and `scripts`.
- **Auth forms**: `login.html` and `register.html` `POST` to `/login` and `/register` and render an `{{ error }}` variable. The routes accept POST and validate the fields. Because no database exists yet, a valid submission re-renders the form with a "not available yet" error instead of creating an account or signing in.
- **Legal pages**: `terms.html` and `privacy.html` reuse the auth-page layout classes (`auth-section`, `auth-card`) together with `.legal-container` and `.legal-card`.
- **Styling**: one stylesheet, `static/css/style.css`, built on design tokens in `:root` (`--ink*`, `--paper*`, `--accent`, `--radius-*`, `--font-display`/`--font-body`, with DM Serif Display and DM Sans loaded from Google Fonts). Use these variables rather than hard-coded colours. Page-specific CSS can go in that page's `head` block instead; for example, the landing page's video modal styles live there.
- **JS**: vanilla JavaScript only, with no frameworks or build tooling. `static/js/main.js` is an empty placeholder. The landing page keeps its modal script inline in its `scripts` block.
