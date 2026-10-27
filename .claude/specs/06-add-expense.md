# Spec: Add Expense

## Overview
Replace the `/expenses/add` placeholder with a working form, so a signed-in user can
record a new expense (amount, category, date, optional description). Steps 1–5 built
the schema, auth and a profile page that reads real `expenses` rows. Until now the only
way to add a row was the seed data. This step adds the first write path for expenses,
which the upcoming edit and delete steps will build on. It is a plain HTML `POST` form
with server-side validation and the Post/Redirect/Get pattern. When the save succeeds,
the user goes back to `/profile` and the new expense shows up in the stats, recent
transactions and category breakdown.

Note: the placeholder text in `app.py` says "coming in Step 7". The roadmap is now one
step behind those labels. This spec is Step 06, and the placeholder strings for
edit and delete stay as they are.

### UI plan
- A single centred card that reuses the auth layout (`.auth-section`,
  `.auth-container`, `.auth-header`, `.auth-card`), so it matches login and register.
- Title "Add an expense", subtitle "Record what you spent and when".
- Fields, in order, each in a `.form-group` with a `<label>` and `.form-input`:
  - **Amount** — `<input type="number" name="amount" step="0.01" min="0.01">`, placeholder "0.00"
  - **Category** — `<select name="category">` built from `CATEGORIES`, with a
    disabled "Choose a category" first option
  - **Date** — `<input type="date" name="date">`, defaults to today
  - **Description** — `<input type="text" name="description" maxlength="200">`, optional
- Errors appear in the existing `.auth-error` box above the form. The submitted
  values are filled back into the form so the user doesn't have to type them again.
- A `.btn-submit` labelled "Add expense", plus a "Cancel" link to `/profile` (`.auth-switch`).
- Entry point: an "Add expense" link in the navbar for signed-in users (before the
  user name). The profile header has no action buttons (the "Edit profile" button was
  removed at the user's request).

```
┌────────────────────────────────┐
│        Add an expense          │
│  Record what you spent and when│
│ ┌────────────────────────────┐ │
│ │ [error, if any]            │ │
│ │ Amount       [ 0.00      ] │ │
│ │ Category     [ Choose… ▾ ] │ │
│ │ Date         [2026-10-28 ] │ │
│ │ Description  [ optional  ] │ │
│ │ [       Add expense      ] │ │
│ └────────────────────────────┘ │
│           Cancel               │
└────────────────────────────────┘
```

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`, `CATEGORIES`)
- Step 3: Login and logout (`session["user_id"]`)
- Step 4/5: Profile page reading real expenses (where the new expense must appear)

## Routes
Existing placeholder route replaced:
- `GET /expenses/add` — render the empty add-expense form (date defaults to today) — logged-in
- `POST /expenses/add` — validate, insert the expense for `session["user_id"]`, then
  redirect to `/profile`. On a validation error, re-render the form with the error and
  the submitted values (HTTP 200) — logged-in

Both methods redirect to `/login` when signed out. If the session's user row no
longer exists, clear the session and redirect to `/login` (same as `profile()`).

### Validation rules
| Field | Rule | Error message |
|---|---|---|
| amount | Required; `float()` must parse it; must be finite and > 0; at most 1,000,000 | "Please enter a valid amount greater than 0." |
| category | Must be one of `CATEGORIES` exactly | "Please choose a valid category." |
| date | Required; `date.fromisoformat()` must parse it | "Please enter a valid date." |
| description | Optional; strip it; at most 200 characters; store `NULL` if empty | "Description must be 200 characters or fewer." |

Show only the first error, in the field order above. Round the amount to 2 decimal
places before inserting.

## Database changes
No database changes. Uses the existing `expenses (id, user_id, amount, category, date,
description, created_at)` table. Add one helper to `database/db.py`:

```python
def add_expense(user_id, amount, category, spent_on, description):
    """Insert one expense for user_id; spent_on is a datetime.date."""
```
It runs a single parameterised `INSERT`, stores `spent_on.isoformat()`, commits, and
closes the connection in `finally`.

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`, the form described above
- **Modify:**
  - `templates/base.html` — add an "Add expense" link (`url_for('add_expense')`) to
    the signed-in nav links
  - `templates/profile.html` — remove the disabled "Edit profile" button from
    `.profile-header` (and its `.profile-edit` styles in `profile.css`)

## Files to change
- `app.py` — replace the `add_expense()` placeholder with GET/POST handling. Import
  `add_expense` (aliased, e.g. `insert_expense`, so it doesn't clash with the view
  name) and `CATEGORIES` from `database.db`
- `database/db.py` — add the `add_expense()` helper
- `templates/base.html` — nav link
- `templates/profile.html` — remove the header "Edit profile" button
- `static/css/profile.css` — remove the `.profile-edit` styles
- `static/css/style.css` — only if a shared `select.form-input` style is needed
  (e.g. `appearance`/padding so the select matches the inputs)

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only. Never format values into SQL
- Passwords hashed with werkzeug (no password handling in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `user_id` comes **only** from `session["user_id"]`. Never read it from the form
- Validate everything on the server. HTML attributes (`required`, `min`, `step`,
  `maxlength`) are only for convenience
- Reject `nan`, `inf` and negative or zero amounts (`math.isfinite`)
- Category must be validated against `CATEGORIES`. Build the `<select>` from the same
  list passed to the template. Never hard-code the options in HTML
- Post/Redirect/Get: a successful POST returns a 302 to `url_for('profile')`. Never
  render a template after a successful insert
- Form uses `method="post"` and `action="{{ url_for('add_expense') }}"`
- Jinja autoescape everywhere; no `|safe`
- Page-specific CSS goes in the template's `head` block. No JavaScript is needed
- Don't implement edit or delete. Leave those placeholder routes untouched
- Responsive: the card is full width with 16px gutters at ~375px, with no horizontal scroll

## Definition of done
- [ ] `python app.py` starts with no errors
- [ ] Visiting `/expenses/add` while signed out redirects to `/login`. A POST while
      signed out also redirects and inserts nothing
- [ ] Signed in, `/expenses/add` shows the form with today's date filled in and all
      7 categories in the dropdown
- [ ] The navbar shows "Add expense" only when signed in, and it opens the form. The
      profile header shows no "Add expense" or "Edit profile" buttons
- [ ] Submitting `12.50` / `Food` / today / "Coffee" redirects to `/profile`, where the
      expense appears at the top of recent transactions and the totals go up by ₹12.50
- [ ] Submitting with an empty description works, and the row's `description` is `NULL`
- [ ] Amounts `0`, `-5`, `abc`, `nan` and `inf` each show "Please enter a valid amount
      greater than 0." and the values entered are kept in the form
- [ ] A tampered category (e.g. `Crypto`, sent via devtools) shows "Please choose a
      valid category." and nothing is inserted
- [ ] A tampered date (`2026-13-40` or `abc`) shows "Please enter a valid date." with no
      500 error
- [ ] A 201-character description is rejected with the length error
- [ ] An expense added by a second user never shows up on the demo user's profile
- [ ] `grep -nE "f\"|\.format\(|%s" database/db.py` shows no string-built SQL in `add_expense`
- [ ] No new hex colours in changed CSS (`grep -E "#[0-9a-fA-F]{3,6}"` only matches the
      existing `:root` tokens)
- [ ] At ~375px the form fits without horizontal scroll
- [ ] Landing, login, register, profile (with filters), terms and privacy still work unchanged
