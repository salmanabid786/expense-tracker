# Spec: Login and Logout

## Overview
Let registered users sign in and out. Step 2 stores users with werkzeug-hashed
passwords, but `POST /login` still returns the placeholder "Sign in isn't available
yet." and `/logout` is a placeholder string. This step checks the submitted email and
password against the `users` table, stores the user in Flask's signed session cookie
on success, clears it on logout, and updates the navbar to reflect signed-in state.
It is the foundation for every logged-in page that follows (profile in Step 4,
expenses in Steps 7–9).

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table, seeded `demo@spendly.com` / `demo123`)
- Step 2 — Registration (users created with `generate_password_hash`, emails stored lowercase)

## Routes
No new routes. Existing routes changed:
- `POST /login` — validate input, check credentials, set session, redirect to `/` — public
- `GET /login` — unchanged, except a signed-in user is redirected to `/` — public
- `GET /register` / `POST /register` — signed-in user is redirected to `/` — public
- `GET /logout` — clear the session and redirect to `/` — public (harmless when signed out)

## Database changes
No database changes. `users` in `database/db.py` already has
`id, name, email (UNIQUE), password_hash, created_at`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — keep the submitted email in the input after a failed
    submit (`value="{{ email or '' }}"`); password is never sent back
  - `templates/base.html` — navbar: when `session.user_id` is set show
    "{{ session.user_name }}" and a "Sign out" link to `url_for('logout')`;
    otherwise keep the current "Sign in" / "Get started" links

## Files to change
- `app.py` — set `app.secret_key`; implement `POST /login`; implement `logout()`;
  redirect signed-in users away from `/login` and `/register`; import `session`
  from flask and `check_password_hash` from `werkzeug.security`; import `os`
- `templates/login.html` — refill email after an error
- `templates/base.html` — signed-in navbar state

## Files to create
- None

## New dependencies
No new dependencies (sessions and `werkzeug.security` ship with Flask).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`; never log or
  re-render the password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; close the connection in every path
- `app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)` — never commit a
  hard-coded secret (dev restarts sign users out; acceptable for now)
- Normalise email with `.strip().lower()` before lookup (matches Step 2)
- Keep "Please enter your email and password." for empty fields
- Wrong email or wrong password both show the same message:
  "Invalid email or password." (don't reveal which one was wrong)
- On success: `session.clear()`, then set `session["user_id"]` and
  `session["user_name"]`; `redirect(url_for("landing"))` (Post/Redirect/Get)
- Logout: `session.clear()` then `redirect(url_for("landing"))`
- Navbar additions reuse existing `nav-links` / `nav-cta` classes; any new CSS uses tokens
- Do not add a `login_required` decorator or protect `/profile` / expense routes —
  that belongs to the steps that implement those pages
- Don't touch the other placeholder routes

## Definition of done
- [ ] `python app.py` starts with no errors and `/login` loads
- [ ] Empty email or password shows "Please enter your email and password."
- [ ] `demo@spendly.com` / `demo123` signs in and redirects to `/`
- [ ] Email is case-insensitive (`DEMO@Spendly.com` works)
- [ ] Wrong password and unknown email both show "Invalid email or password."
- [ ] After a failed sign-in the email is still filled in; password is empty
- [ ] When signed in, the navbar shows the user's name and "Sign out" instead of
      "Sign in" / "Get started"
- [ ] Visiting `/login` or `/register` while signed in redirects to `/`
- [ ] Clicking "Sign out" redirects to `/` and the navbar shows "Sign in" / "Get started" again
- [ ] A user registered via `/register` can then sign in with their password
- [ ] Landing, register, terms and privacy pages still load; navbar looks right on a
      narrow screen
