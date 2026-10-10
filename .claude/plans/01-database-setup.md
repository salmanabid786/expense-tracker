# Plan: 01 — Database Setup

## Context

Spec: `.claude/specs/01-database-setup.md`. `expense-tracker/database/db.py` currently only has stub comments. This step gives Spendly a SQLite data layer (`users` and `expenses` tables, plus demo seed data) that later steps (auth, profile, expenses) will build on. It adds no new routes and no new files, so the register/login handlers in `app.py` stay as they are.

## Files to change

1. `expense-tracker/database/db.py`: implement `get_db()`, `init_db()` and `seed_db()`
2. `expense-tracker/app.py`: add the import and startup calls

No new files and no new dependencies. Uses `sqlite3` from the standard library and `werkzeug.security`, which is already installed.

## 1. `database/db.py`

- **DB path:** `DB_PATH = os.path.join(<app dir>, "expense_tracker.db")`, resolved from `__file__` (the parent of `database/`) so it doesn't depend on the current working directory. The spec lists `expense_tracker.db` as an option, and it is already in `expense-tracker/.gitignore`.
- **`get_db()`:** `sqlite3.connect(DB_PATH)`, set `conn.row_factory = sqlite3.Row`, run `PRAGMA foreign_keys = ON`, then return `conn`.
- **`init_db()`:** a single `executescript` with:
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
  );
  CREATE TABLE IF NOT EXISTS expenses (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      amount REAL NOT NULL,
      category TEXT NOT NULL,
      date TEXT NOT NULL,
      description TEXT,
      created_at TEXT DEFAULT (datetime('now'))
  );
  ```
  Commit, then close.
- **`seed_db()`:**
  - Run `SELECT COUNT(*) FROM users`. If it's greater than 0, close and return early.
  - Insert the demo user (`Demo User`, `demo@spendly.com`, `generate_password_hash("demo123")`) with a parameterized `INSERT`. Read `cursor.lastrowid` to get its id.
  - Insert 8 expenses with `executemany` (parameterized). Each of the 7 fixed categories appears once and Food appears twice. Dates are built from `date.today().replace(day=N).strftime("%Y-%m-%d")` with N between 1 and 28, so they fall in the current month and are always valid. Amounts are floats.
  - Commit, then close.
- Optional: a module-level `CATEGORIES` list holding the 7 fixed values, for reuse in later steps.

## 2. `app.py`

- `from database.db import get_db, init_db, seed_db`. The spec asks for `get_db` to be imported too, although nothing uses it yet.
- After `app = Flask(__name__)`:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```
- No route changes.

## Verification

From `expense-tracker/`, with the venv active:
1. `python app.py` starts cleanly, and `expense_tracker.db` appears in `expense-tracker/`.
2. A quick Python check:
   - both tables exist (`PRAGMA table_info`)
   - 1 user and 8 expenses, covering all 7 categories
   - `check_password_hash(row["password_hash"], "demo123")` is true
3. Restart the app. The counts are still 1 and 8, so no duplicates were added.
4. Inserting a duplicate email raises `sqlite3.IntegrityError`. Inserting an expense with `user_id=9999` through `get_db()` raises `IntegrityError` (foreign key).
5. `/`, `/login` and `/register` still load.
6. `git status` must not show `expense_tracker.db` (it is gitignored).
