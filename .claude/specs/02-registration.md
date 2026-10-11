# Spec: Registration

## Overview
Make the existing sign-up form create real accounts. Step 1 added the SQLite data
layer (`users` table, `get_db()`), but `POST /register` still validates input and
then returns the placeholder "Account creation isn't available yet." This step
stores a new user with a werkzeug-hashed password, rejects duplicate emails with a
clear message, and sends the user to the sign-in page on success. Logging in and
sessions are left to Step 3.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with UNIQUE email)

## Routes
No new routes. Existing route changed:
- `POST /register` — validate input, insert user, redirect to `/login` on success;
  re-render `register.html` with an error otherwise — public
- `GET /register` — unchanged — public

## Database changes
No database changes. The `users` table in `database/db.py` already has
`id, name, email (UNIQUE), password_hash, created_at`.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — keep the submitted `name` and `email` in
  the inputs after a failed submit (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`).
  The password is never sent back to the form.

## Files to change
- `app.py` — implement the success path of `register()`; import `redirect`, `url_for`
  from flask and `generate_password_hash` from `werkzeug.security`
- `templates/register.html` — refill name/email after an error

## Files to create
- None

## New dependencies
No new dependencies (`werkzeug` ships with Flask).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log plain text
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; close the connection in every path
- Normalise email with `.strip().lower()` before checking and inserting
- Keep the existing validation and messages (all fields required, password ≥ 8 chars)
- Detect duplicates by catching `sqlite3.IntegrityError` on insert (the UNIQUE
  constraint is the source of truth) → error "An account with that email already exists."
- On success: `redirect(url_for("login"))` (Post/Redirect/Get). Do not add sessions,
  `secret_key`, or auto-login — that's Step 3
- Don't touch placeholder routes or the login route

## Definition of done
- [ ] `python app.py` starts with no errors and `/register` loads
- [ ] Submitting with any empty field shows "Please fill in all fields."
- [ ] A password under 8 characters shows "Password must be at least 8 characters."
- [ ] A valid new name/email/password redirects to `/login`
- [ ] The new row is in `users` with a hashed `password_hash` (starts with `scrypt:` or
      `pbkdf2:`), not the plain password
- [ ] Registering again with the same email (any letter case) shows
      "An account with that email already exists." and creates no second row
- [ ] After an error, name and email are still filled in; password is empty
- [ ] `demo@spendly.com` can't be registered again
- [ ] Landing, login, terms and privacy pages still load
