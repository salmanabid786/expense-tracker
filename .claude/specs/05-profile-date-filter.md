# Spec: Date Filter for Profile Page

## Overview
Add a date-range filter to `/profile` so a signed-in user can limit the summary cards,
recent transactions and category breakdown to a chosen period. Step 4 built the page
from hard-coded sample data, and a filter can't work on that, so this step also
replaces the sample data with real queries on the signed-in user's `users` and
`expenses` rows. The filter is a plain HTML `GET` form with query-string parameters
(`?start=YYYY-MM-DD&end=YYYY-MM-DD`). Preset links cover common ranges, so it works
with no JavaScript and filtered views can be bookmarked or shared. The template data
contract from Step 4 stays the same, with one new `filter` dict added.

### UI plan
- A **filter bar card** (`.profile-filter`) goes between the profile header and the
  summary row, with the same card styling as the other profile cards.
- **Left:** preset chips (*This month*, *Last 30 days*, *Last 3 months*, *This year*,
  *All time*). Each chip is an `<a>` linking to `/profile?start=…&end=…`; *All time*
  links to `/profile` with no parameters. The chip that matches the active range gets
  `.is-active` (accent background).
- **Right:** a custom range form with two `<input type="date">` fields (*From*, *To*)
  and an *Apply* button. The fields are pre-filled with the active range, and a *Clear*
  link goes back to `/profile`.
- A **range caption** under the bar shows the active period, e.g. "Showing 01 Oct 2026
  – 27 Oct 2026" or "Showing all time".
- **Errors** appear as one inline message in the filter card (`.profile-filter-error`,
  `--danger` text on `--danger-light`); the page falls back to all time.

```
┌──────────────────────────────────────────────────────────────────┐
│ [This month] [Last 30 days] [Last 3 months] [This year] [All time]│
│                     From [2026-10-01]  To [2026-10-27]  [Apply] Clear │
│ Showing 01 Oct 2026 – 27 Oct 2026                                 │
└──────────────────────────────────────────────────────────────────┘
```

## Depends on
- Step 1: Database setup (`users` / `expenses` tables, `get_db()`, seed data)
- Step 3: Login and logout (`session["user_id"]`)
- Step 4: Profile page design (`profile.html`, `profile.css`, data contract)

## Routes
No new routes. Existing route changed:
- `GET /profile` — reads optional `start` and `end` query parameters (ISO
  `YYYY-MM-DD`, both inclusive), loads the signed-in user's expenses in that range from
  the database and renders `profile.html`; redirects to `/login` when not signed in —
  logged-in

### Filter rules
| Input | Behaviour |
|---|---|
| Neither param | All time, no error |
| Only `start` | From `start` up to and including the latest expense |
| Only `end` | From the earliest expense up to and including `end` |
| Both, `start` ≤ `end` | That inclusive range |
| Unparseable date (`date.fromisoformat` raises `ValueError`) | Ignore both params, show all time, error "Please enter valid dates." |
| `start` > `end` | Ignore both params, show all time, error "Start date must be on or before end date." |
| Empty string (e.g. a blank date input) | Treated as missing |

Presets are worked out from `date.today()` in the route:
- *This month*: the 1st of the current month → today
- *Last 30 days*: today − 29 days → today
- *Last 3 months*: today − 89 days → today
- *This year*: 1 Jan → today
- *All time*: no parameters

## Database changes
No database changes. This uses the existing `users (id, name, email, password_hash,
created_at)` and `expenses (id, user_id, amount, category, date, description,
created_at)`. `expenses.date` is stored as ISO `YYYY-MM-DD` text, so comparing
strings with `BETWEEN` / `>=` / `<=` gives the right date order.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add the `.profile-filter` card between `.profile-header` and `.profile-stats`
    (chips, date form, caption, optional error)
  - Change the empty-state text when a range is active: "No expenses in this period"
    (keep "No expenses yet" for all time with no expenses)
  - Change the *Total spent* label to *Spent in period* when a range is active
  - The rest of the markup, classes and icons stay as they are. Add a
    `calendar-range` Lucide icon to the filter card only

### Template data contract
The Step 4 shapes stay the same, with real values now. One new variable:
```python
user = {"name": str, "email": str, "initials": str, "member_since": str}  # from users row; "Oct 2026" from created_at
stats = {"total_spent": float,        # sum within the active range
         "month_spent": float,        # current calendar month, NOT affected by the filter
         "transaction_count": int,    # count within the active range
         "top_category": str}         # within the active range, "—" if none
transactions = [{"date": str, "description": str, "category": str, "amount": float}, ...]  # within range, newest first, max 10, date "%d %b"
categories = [{"name": str, "amount": float, "percent": int}, ...]  # within range, amount desc, zero-amount categories omitted
filter = {
    "start": str,       # ISO or "" — used for the date input value
    "end": str,         # ISO or ""
    "active": bool,     # True when a valid range is applied
    "label": str,       # "01 Oct 2026 – 27 Oct 2026" / "all time"
    "preset": str,      # "month" | "30d" | "3m" | "year" | "all" | "" (custom)
    "presets": [{"key": str, "label": str, "start": str, "end": str}, ...],
    "error": str,       # "" when none
}
```

## Files to change
- `app.py`:
  - Rewrite the body of `profile()`. Remove the sample data and replace it with real
    queries, filtered by `user_id` and the date range
  - Add a small helper `_parse_date_range(args)` that returns
    `(start, end, error)` and a helper that builds the presets list. Keep both in
    `app.py` above `profile()`; no new modules
- `templates/profile.html`: filter card, conditional labels and empty-state text
- `static/css/profile.css`: `.profile-filter*` styles plus responsive rules

## Files to create
None.

## New dependencies
No new dependencies. Use `datetime.date` / `timedelta` from the standard library.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only. Pass the dates as `?` parameters and never format them
  into SQL. Build the `WHERE` clause from fixed fragments
  (`"user_id = ?"`, `"date >= ?"`, `"date <= ?"`) joined with `AND`, with values in a
  params list
- Passwords hashed with werkzeug (no password handling in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- **Every query is scoped to `session["user_id"]`.** A user must never see another
  user's expenses, whatever the query string says
- Validate dates with `date.fromisoformat()` on the server. Don't trust the browser's
  date picker, and never pass raw query values to SQL without parsing them
- Do the sums and the category grouping in SQL (`SUM`, `COUNT`, `GROUP BY category`)
  or in Python over a single filtered query. Either is fine; keep it readable
- Work out `month_spent` with its own query for the current calendar month, ignoring
  the filter
- Percentages: `round(amount / total * 100)`, guarding against `total == 0`
- If the `users` row for `session["user_id"]` is missing (stale session), clear the
  session and redirect to `/login`
- Filter form: `method="get"`, `action="{{ url_for('profile') }}"`, input names
  `start` / `end`. Build chip links with `url_for('profile', start=..., end=...)`
- No JavaScript for the filter. The only script stays the existing Lucide include
- Reuse `.btn-ghost` for *Apply* and `.form-input` for the date inputs where the
  styling fits. Chips are new `.profile-chip` styles: `--radius-sm`, `--border`, and
  `--accent` / `--paper-card` text when `.is-active`
- Spacing, type scale and card styling follow the Step 4 rules (8px grid, 1.5rem card
  padding, no shadows)
- Responsive: at ≤600px chips wrap and the date form stacks to full width, with no
  horizontal page scroll
- Jinja autoescape everywhere; no `|safe`
- Don't touch the `/expenses/*` placeholder routes

## Definition of done
- [ ] `python app.py` starts with no errors
- [ ] Visiting `/profile` while signed out still redirects to `/login`
- [ ] Signed in as `demo@spendly.com` / `demo123`, `/profile` shows the real seeded
      expenses (8 rows, total ₹357.73) and the real email and member-since date from the DB
- [ ] The filter card shows 5 preset chips; *All time* is active by default and the
      caption reads "Showing all time"
- [ ] Clicking *This month* sets the URL to `?start=<1st>&end=<today>`, highlights that
      chip, and only current-month expenses show up in the cards, table and breakdown
- [ ] Entering a custom From/To range and clicking *Apply* filters the page; the inputs
      keep their values after reload and no chip is highlighted
- [ ] A range with no expenses shows "No expenses in this period" in both cards and
      ₹0.00 / 0 / "—" in the stats
- [ ] *This month* stays the same whatever filter is applied
- [ ] `/profile?start=2026-13-01` and `/profile?start=abc` show "Please enter valid
      dates." and fall back to all time with no 500 error
- [ ] `/profile?start=2026-10-20&end=2026-10-01` shows "Start date must be on or
      before end date."
- [ ] `/profile?start=2026-10-01&end=2026-10-01` includes expenses dated exactly 1 Oct
      (the bounds are inclusive)
- [ ] A second registered user with no expenses sees empty states, not the demo user's data
- [ ] `grep -nE "f\"|\.format\(|%s" app.py` shows no string-built SQL in `profile()`
- [ ] `grep -E "#[0-9a-fA-F]{3,6}" static/css/profile.css` returns nothing
- [ ] At ~375px chips wrap, the date form stacks, and there's no horizontal page scroll
- [ ] Landing, login, register, terms and privacy pages still load and look unchanged
