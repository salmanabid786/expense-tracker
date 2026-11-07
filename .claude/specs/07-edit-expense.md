# Spec: Edit Expense

## Overview
Replace the `/expenses/<int:id>/edit` placeholder with a working form, so a signed-in
user can correct an expense they already recorded (amount, category, date, optional
description). Step 6 added the first write path (`add_expense`) and the shared form
validation (`_parse_expense_form`). This step reuses both. It adds an update path that
only ever touches rows owned by the signed-in user, plus an "Edit" link on each row of
the profile's recent transactions. It is a plain HTML `POST` form with server-side
validation and the Post/Redirect/Get pattern. After a successful save the user goes back
to `/profile`, where the stats, recent transactions and category breakdown reflect the change.

Note: the placeholder text in `app.py` says "coming in Step 8". The roadmap is one step
behind those labels. This spec is Step 07. Leave the delete placeholder as it is.

### UI plan
- The same single centred card as `add_expense.html` (`.auth-section`, `.auth-container`,
  `.auth-header`, `.auth-card`), so add and edit look the same.
- Title "Edit expense", subtitle "Update the details of this expense".
- Same fields, order, attributes and the `select.form-input` / `.form-optional` styles as
  the add form, but pre-filled with the stored values:
  - **Amount**: the stored amount formatted to 2 decimals (e.g. `12.50`)
  - **Category**: the stored category selected, built from `CATEGORIES`
  - **Date**: the stored `YYYY-MM-DD`
  - **Description**: the stored text, or empty if `NULL`
- Errors appear in `.auth-error` above the form, and the submitted values are filled back in.
- A `.btn-submit` labelled "Save changes", plus a "Cancel" link to `/profile` (`.auth-switch`).
- Entry point: on `profile.html`, each recent-transactions row gets a trailing cell with
  an "Edit" link (`url_for('edit_expense', id=t.id)`). The link has an accessible label
  that says which expense it edits, e.g. `aria-label="Edit expense: Lunch at cafe, 02 Nov"`.
  Add an empty, visually hidden header cell (`<th><span class="sr-only">Actions</span></th>`,
  or the equivalent using the existing classes) so the columns still line up.

```
┌────────────────────────────────┐
│          Edit expense          │
│ Update the details of this     │
│ expense                        │
│ ┌────────────────────────────┐ │
│ │ [error, if any]            │ │
│ │ Amount       [ 12.50     ] │ │
│ │ Category     [ Food    ▾ ] │ │
│ │ Date         [2026-11-02 ] │ │
│ │ Description  [Lunch at…  ] │ │
│ │ [      Save changes      ] │ │
│ └────────────────────────────┘ │
│           Cancel               │
└────────────────────────────────┘
```

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`, `CATEGORIES`)
- Step 3: Login and logout (`session["user_id"]`)
- Step 4/5: Profile page (recent transactions table, which hosts the Edit links)
- Step 6: Add expense (`_parse_expense_form`, `MAX_DESCRIPTION`, form layout)

## Routes
Existing placeholder route replaced (URL unchanged):
- `GET /expenses/<int:id>/edit`: render the form pre-filled with expense `id`. Logged-in only.
- `POST /expenses/<int:id>/edit`: validate with `_parse_expense_form`, update the expense,
  then redirect (302) to `/profile`. On a validation error, re-render the form with the
  error and the submitted values (HTTP 200). Logged-in only.

Access rules, checked in this order for both methods:
1. Signed out: redirect to `/login`.
2. The session's user row no longer exists: clear the session and redirect to `/login`
   (same as `profile()` and `add_expense()`).
3. Expense `id` doesn't exist **or belongs to another user**: `abort(404)`. Use the same
   response for both cases so the app never reveals that another user's expense exists.
   A POST in this case updates nothing.

Validation is exactly the Step 6 rules, through `_parse_expense_form` (amount > 0 and
≤ 1,000,000 and finite, rounded to 2 dp; category in `CATEGORIES`; valid ISO date;
description ≤ 200 characters, `NULL` if empty). Don't duplicate the validation code.

## Database changes
No schema changes. Add two helpers to `database/db.py` and extend one query:

```python
def get_expense(expense_id, user_id):
    """Return one expense row (id, amount, category, date, description) owned by
    user_id, or None if it doesn't exist or belongs to someone else."""

def update_expense(expense_id, user_id, amount, category, spent_on, description):
    """Update one expense owned by user_id; spent_on is a datetime.date.
    Return True if a row was updated."""
```
- `get_expense`: `SELECT ... FROM expenses WHERE id = ? AND user_id = ?`
- `update_expense`: a single `UPDATE expenses SET amount = ?, category = ?, date = ?,
  description = ? WHERE id = ? AND user_id = ?`. Store `spent_on.isoformat()`, commit,
  return `cursor.rowcount == 1`, and close the connection in `finally`.
- `get_expenses`: add `id` to the selected columns so the profile can build Edit links.
  Keep its filtering and ordering unchanged.

## Templates
- **Create:** `templates/edit_expense.html`: extends `base.html`. The pre-filled form
  described above, posting to `url_for('edit_expense', id=expense_id)`.
- **Modify:** `templates/profile.html`: add the actions header cell and a per-row "Edit"
  link to the recent transactions table. Any small link style goes in `profile.css`.

## Files to change
- `app.py`:
  - Replace the `edit_expense(id)` placeholder with GET/POST handling.
  - Import `get_expense` and `update_expense` from `database.db`, plus `abort` from flask.
  - Add `"id": e["id"]` to each dict in `profile()`'s `transactions` list.
- `database/db.py`: add `get_expense()` and `update_expense()`, and select `id` in `get_expenses()`.
- `templates/profile.html`: Edit link column.
- `static/css/profile.css`: only if the Edit link needs a style (use existing tokens).

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only. Never format values into SQL.
- Passwords hashed with werkzeug (no password handling in this step).
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`.
- `user_id` comes **only** from `session["user_id"]`, and the expense id only from the
  URL. Never read either from the form.
- Every read and write is scoped with `WHERE id = ? AND user_id = ?`. Never fetch by id
  alone and then compare in Python.
- Missing and not-owned expenses both return 404, with no difference in message or timing logic.
- Reuse `_parse_expense_form` and `MAX_DESCRIPTION`. Don't copy the validation.
- Validate everything on the server. HTML attributes (`required`, `min`, `step`,
  `maxlength`) are only for convenience.
- Build the category `<select>` from `CATEGORIES` passed to the template. Never hard-code
  the options.
- Post/Redirect/Get: a successful POST returns a 302 to `url_for('profile')`. Never
  render a template after a successful update.
- Form uses `method="post"` and `action="{{ url_for('edit_expense', id=expense_id) }}"`.
- Jinja autoescape everywhere; no `|safe`.
- Page-specific CSS goes in the template's `head` block. No JavaScript is needed.
- Don't modify `add_expense()` or `add_expense.html`, and don't implement delete. Leave
  the delete placeholder untouched.
- Out of scope: CSRF protection. The app has none yet, and adding it would touch every form.
- Responsive: the card is full width with 16px gutters at ~375px. The profile table with
  the new column must not cause page-level horizontal scroll.

## Definition of done
- [ ] `python app.py` starts with no errors.
- [ ] Signed out, `GET` and `POST /expenses/1/edit` both redirect to `/login`, and nothing is updated.
- [ ] Signed in as the demo user, each recent-transactions row on `/profile` has an
      "Edit" link to `/expenses/<that row's id>/edit`.
- [ ] Opening an Edit link shows the form pre-filled with that expense's amount (2 dp),
      category, date and description. An expense with a `NULL` description shows an
      empty field, not "None".
- [ ] Changing `12.50 / Food / Lunch at cafe` to `15.00 / Transport / Taxi` and saving
      redirects to `/profile`. The row shows the new values, and the totals and category
      breakdown change accordingly.
- [ ] Clearing the description and saving stores `NULL` for that row.
- [ ] Amounts `0`, `-5`, `abc`, `nan` and `inf`, a tampered category (`Crypto`), a
      tampered date (`2026-13-40`) and a 201-character description each show the Step 6
      error message, keep the submitted values in the form, and leave the row unchanged.
- [ ] `/expenses/999999/edit` returns 404.
- [ ] Signed in as a second user, `GET` and `POST` on the demo user's expense id both
      return 404, and the demo user's row is unchanged.
- [ ] Editing doesn't create a new row (the transaction count on `/profile` stays the same).
- [ ] `/expenses/<id>/delete` still returns its placeholder text, and `/expenses/add`
      still works unchanged.
- [ ] `grep -nE "f\"|\.format\(|%s" database/db.py` shows no string-built SQL in the new helpers.
- [ ] No new hex colours in changed CSS (`grep -E "#[0-9a-fA-F]{3,6}"` matches only the
      existing `:root` tokens).
- [ ] At ~375px the edit form fits, and the profile page has no horizontal page scroll.
- [ ] Landing, login, register, profile (with date filters), add expense, terms and
      privacy still work unchanged.
