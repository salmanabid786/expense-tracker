# Spec: Delete Expense

## Overview
Replace the `/expenses/<int:id>/delete` placeholder so a signed-in user can permanently
remove an expense they recorded by mistake. Steps 6 and 7 added the create and update
paths. This step completes expense management (add, edit, delete) on the profile page.
Deleting can't be undone, so it is a two-step flow with no JavaScript:
1. A "Delete" link on each recent-transactions row opens a confirmation page showing
   the expense's details.
2. Only a `POST` from that page's form removes the row.

A `GET` never deletes anything, so link prefetching, crawlers or a pasted URL can't
remove data. After a successful delete the user goes back to `/profile` (Post/Redirect/Get),
and the stats, recent transactions and category breakdown no longer include the expense.

Note: the placeholder text in `app.py` says "coming in Step 9". The roadmap is one step
behind those labels. This spec is Step 08.

### UI plan
- The same single centred card as the add and edit pages (`.auth-section`,
  `.auth-container`, `.auth-header`, `.auth-card`).
- Title "Delete expense", subtitle "This can't be undone".
- The card shows the expense as a read-only summary list (`<dl>`): Amount (`₹1,234.50`
  format, as on the profile), Category, Date (`02 Nov 2026`), and Description (or "—" if empty).
- A form with `method="post"` and a single danger-styled submit button, "Delete expense",
  plus a "Cancel" link back to `/profile` (`.auth-switch`).
- Entry point: in `profile.html`'s `.profile-actions` cell, a "Delete" link after "Edit"
  (`url_for('delete_expense', id=t.id)`). It has an accessible label, e.g.
  `aria-label="Delete expense: Lunch at cafe, 02 Nov"`, and is styled as a quieter
  danger link that is visibly different from Edit.

```
┌────────────────────────────────┐
│         Delete expense         │
│      This can't be undone      │
│ ┌────────────────────────────┐ │
│ │ Amount       ₹12.50        │ │
│ │ Category     Food          │ │
│ │ Date         02 Nov 2026   │ │
│ │ Description  Lunch at cafe │ │
│ │ [     Delete expense     ] │ │  ← danger button
│ └────────────────────────────┘ │
│           Cancel               │
└────────────────────────────────┘
```

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`)
- Step 3: Login and logout (`session["user_id"]`)
- Step 4/5: Profile page (recent transactions table and `.profile-actions` cell)
- Step 7: Edit expense (`get_expense()` owner-scoped lookup, the id in `transactions`,
  the 404 ownership pattern)

## Routes
Existing placeholder route replaced (URL unchanged):
- `GET /expenses/<int:id>/delete`: render the confirmation page for expense `id`. Deletes nothing. Logged-in only.
- `POST /expenses/<int:id>/delete`: delete the expense, then redirect (302) to `/profile`. Logged-in only.

Access rules, checked in this order for both methods (same as `edit_expense()`):
1. Signed out: redirect to `/login`.
2. The session's user row no longer exists: clear the session and redirect to `/login`.
3. Expense `id` doesn't exist **or belongs to another user**: `abort(404)`. Use the same
   response for both. A POST in this case deletes nothing.

The POST body needs no fields. The id comes only from the URL and the owner only from the session.

## Database changes
No schema changes. Add one helper to `database/db.py`, after `update_expense()`:

```python
def delete_expense(expense_id, user_id):
    """Delete one expense owned by user_id. Return True if a row was deleted."""
```
- A single parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?`.
- Commit, return `cur.rowcount == 1`, and close the connection in `finally`.
- Import it in `app.py` with an alias (e.g. `delete_expense as remove_expense`) so it
  doesn't clash with the `delete_expense` view name. Step 6 handles `add_expense` the same way.

## Templates
- **Create:** `templates/delete_expense.html`: extends `base.html`. The confirmation card
  described above, with the form posting to `url_for('delete_expense', id=expense.id)`.
- **Modify:** `templates/profile.html`: add the "Delete" link after "Edit" in each row's
  `.profile-actions` cell.

## Files to change
- `app.py`:
  - Replace the `delete_expense(id)` placeholder with GET/POST handling, and move it next
    to `edit_expense()` so the "Placeholder routes" banner can be removed if nothing is left under it.
  - Import the aliased `delete_expense` helper.
  - On GET, pass a display dict to the template: `id`, `amount`, `category`, the date
    formatted `%d %b %Y` (fall back to the raw value via `_parse_stored_date`), and
    `description`.
- `database/db.py`: add `delete_expense()`.
- `templates/profile.html`: Delete link.
- `static/css/profile.css`: `.profile-delete-link` style (and spacing between the two
  links), using tokens only.
- `tests/test_06-add-expense.py`: remove the outdated `TestPlaceholdersUntouched` class.
  Both edit and delete are real routes now, and its edit check already fails since Step 7.

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only. Never format values into SQL.
- Passwords hashed with werkzeug (no password handling in this step).
- Use CSS variables. Never hardcode hex values. Use the existing danger/error token
  (whatever `.auth-error` uses in `style.css`) for the danger button and link. Don't add a new red.
- All templates extend `base.html`.
- **GET never deletes.** Only `POST` changes data.
- `user_id` comes **only** from `session["user_id"]`, and the expense id only from the
  URL. Never read either from the form.
- Every read and the delete itself are scoped with `WHERE id = ? AND user_id = ?`, using
  `get_expense()` for the lookup. Never fetch or delete by id alone.
- Missing and not-owned expenses both return 404, with no difference in message.
- Post/Redirect/Get: a successful POST returns a 302 to `url_for('profile')`. Never
  render a template after a delete.
- Jinja autoescape everywhere; no `|safe`.
- No JavaScript `confirm()`. The confirmation page is the confirmation.
- Page-specific CSS goes in the template's `head` block.
- Don't change add or edit behaviour. Out of scope: soft delete or undo, bulk delete,
  flash messages, and CSRF protection (the app has none yet).
- Responsive: the card is full width with 16px gutters at ~375px, and the profile actions
  cell with two links must not cause page-level horizontal scroll.

## Definition of done
- [ ] `python app.py` starts with no errors, and `pytest` passes after removing the
      outdated placeholder tests.
- [ ] Signed out, `GET` and `POST /expenses/1/delete` both redirect to `/login`, and
      nothing is deleted.
- [ ] Signed in as the demo user, each recent-transactions row has a "Delete" link (after
      "Edit") to `/expenses/<that row's id>/delete`.
- [ ] `GET /expenses/<id>/delete` shows the confirmation page with the correct amount,
      category, date and description (or "—"), and the row still exists afterwards.
- [ ] Clicking "Delete expense" redirects to `/profile`. The row is gone, the transaction
      count drops by 1, and the totals and category breakdown no longer include it.
- [ ] "Cancel" returns to `/profile` with the expense intact.
- [ ] A second `POST` to the same (now deleted) id returns 404.
- [ ] `/expenses/999999/delete` returns 404 for both GET and POST.
- [ ] Signed in as a second user, `GET` and `POST` on the demo user's expense id both
      return 404, and the demo user's row still exists.
- [ ] Add expense and edit expense still work unchanged.
- [ ] `grep -nE "f\"|\.format\(|%s" database/db.py` shows no string-built SQL in `delete_expense`.
- [ ] No new hex colours in changed CSS (`grep -E "#[0-9a-fA-F]{3,6}"` matches only the
      existing `:root` tokens).
- [ ] At ~375px the confirmation card fits, and the profile page has no horizontal page scroll.
- [ ] Landing, login, register, profile (with date filters), terms and privacy still work unchanged.
