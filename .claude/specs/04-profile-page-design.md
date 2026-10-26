# Spec: Profile Page Design

## Overview
Replace the `/profile` placeholder ("Profile page — coming in Step 4") with a designed
page that only signed-in users can see. Step 3 put the user in the session, so this is
the first page that belongs to a signed-in user. This step is **UI only**: the page
shows the user's details, four spending summary cards, a recent-transactions table and
a category breakdown, all filled from **hard-coded sample data** in the route. Step 5
replaces the sample data with real queries and does not change the template. The
design follows the `spendly-ui-designer` skill (`.claude/skills/frontend-design/SKILL.md`)
using Spendly's existing tokens: warm paper background, white cards, deep-green accent,
DM Serif Display headings and DM Sans body.

### UI plan
- **Layout:** a single column, left-aligned page inside `--max-width` (1200px), with
  the same side padding as the landing sections (2rem, 1rem on phones). No sidebar.
  Centred layouts are only for the empty state.
- **Profile header card:** an initials avatar (green circle), name in display font,
  email and "Member since" below it, and an "Edit profile" ghost button on the right
  that doesn't do anything yet.
- **Summary row:** 4 cards (Total spent, This month, Transactions, Top category). Each
  has one icon, a small muted label and a large tabular-figure value.
- **Two-column body:** recent transactions table (wide, about 2/3) and spending by
  category (narrow, about 1/3) with horizontal bars. Below 900px it becomes one column.
- **Assumptions:** currency is ₹ (footer says "Track every rupee"); no income figures,
  since Spendly only tracks expenses; no charts library, because the bars are plain CSS.

### Wireframe (desktop)
```
┌──────────────────────────────────────────────────────────────────┐
│ (DU)  Demo User                                 [ Edit profile ] │
│       demo@spendly.com · Member since Oct 2026                   │
└──────────────────────────────────────────────────────────────────┘
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ ◎ Total     │ │ ◎ This month│ │ ◎ Transact. │ │ ◎ Top categ.│
│ ₹357.73     │ │ ₹357.73     │ │ 8           │ │ Bills       │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
┌──────────────────────────────────────┐ ┌───────────────────────┐
│ ◎ Recent transactions                │ │ ◎ Spending by category│
│ Date     Description  Category  Amt  │ │ Bills  ███████  ₹120  │
│ 21 Oct   Groceries    (Food)  ₹56.30 │ │ Food   ████     ₹68   │
│ ...                                  │ │ ...                   │
└──────────────────────────────────────┘ └───────────────────────┘
```

## Depends on
- Step 1 — Database setup (`users` / `expenses` tables, `CATEGORIES` in `database/db.py`)
- Step 3 — Login and logout (`session["user_id"]`, `session["user_name"]`)

## Routes
No new routes. Existing route changed:
- `GET /profile` — render `profile.html` with sample data; redirect to `/login` when
  not signed in — logged-in

## Database changes
No database changes. `database/db.py` already has `users (id, name, email,
password_hash, created_at)` and `expenses (id, user_id, amount, category, date,
description, created_at)`. This step does not query either table; Step 5 does.

## Templates
- **Create:** `templates/profile.html`, which extends `base.html`:
  - `title` → `Profile — Spendly`
  - `head` → `<link>` to `static/css/profile.css`
  - `content` → the sections below
  - `scripts` → Lucide CDN script (pinned) + `lucide.createIcons()`

  | Section | Root class | Contents |
  |---|---|---|
  | Page wrapper | `.profile-page` | max-width container, vertical gap between sections |
  | Header card | `.profile-header` | `.profile-avatar` (initials), `.profile-name` (h1), `.profile-meta` (email · member since), `.btn-ghost` "Edit profile" with `pencil` icon, `aria-disabled="true"` |
  | Summary cards | `.profile-stats` > `.profile-stat` ×4 | `.profile-stat-icon`, `.profile-stat-label`, `.profile-stat-value` |
  | Body grid | `.profile-grid` | 2fr / 1fr columns |
  | Transactions | `.profile-card` + `.profile-table-wrap` > `table.profile-table` | columns Date, Description, Category, Amount; category as `.profile-pill`; empty state `.profile-empty` with `receipt` icon and "No expenses yet" |
  | Category breakdown | `.profile-card` + `.profile-cat-list` | per row: `.profile-cat-name`, `.profile-cat-track` > `.profile-cat-bar` (inline `style="width: {{ c.percent }}%"`), `.profile-cat-amount` |

- **Modify:** `templates/base.html`. In the signed-in navbar branch, turn
  `<span class="nav-user">` into `<a href="{{ url_for('profile') }}" class="nav-user">`.
  Keep "Sign out" as is.

### Icons (Lucide, one per element)
| Element | Icon |
|---|---|
| Total spent | `wallet` |
| This month | `calendar` |
| Transactions | `receipt` |
| Top category | `tag` |
| Recent transactions heading | `credit-card` |
| Spending by category heading | `pie-chart` |
| Edit profile button | `pencil` |

Sizes: 16px inline with text and buttons, 20px in stat cards, 20px in section headings.
Stat icons sit in a 40px `--accent-light` rounded square, with the icon in `--accent`.

### Template data contract
`profile()` passes exactly these variables. Step 5 must keep the same shapes.
```python
user = {"name": str, "email": str, "initials": str, "member_since": str}  # "Oct 2026"
stats = {"total_spent": float, "month_spent": float,
         "transaction_count": int, "top_category": str}
transactions = [{"date": str, "description": str, "category": str, "amount": float}, ...]  # newest first, max 5
categories = [{"name": str, "amount": float, "percent": int}, ...]  # sorted by amount desc, percent 0–100
```

## Files to change
- `app.py`: implement `profile()` (session guard, sample data, `render_template`);
  import `CATEGORIES` from `database.db`
- `templates/base.html`: navbar name links to `/profile`
- `static/css/style.css`: add only `.nav-user:hover { color: var(--ink); }` next to
  the existing `.nav-user` rule (a shared navbar style)

## Files to create
- `templates/profile.html`
- `static/css/profile.css`: every selector prefixed `.profile-`

## New dependencies
No new pip dependencies. Lucide is loaded from a CDN in `profile.html`'s `scripts`
block only, pinned to an exact version (`https://unpkg.com/lucide@0.460.0`), not
`@latest` and not in `base.html`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (none are needed in this step)
- Passwords hashed with werkzeug (no password handling in this step)
- Use CSS variables — never hardcode hex values. Map the skill's palette to existing tokens:

  | Skill role | Spendly token |
  |---|---|
  | Background | `--paper` (from `body`) |
  | Card surface / border | `--paper-card` / `--border` |
  | Row hover, table header bg | `--paper-warm` |
  | Primary text / secondary | `--ink` / `--ink-muted` (`--ink-faint` for captions) |
  | Primary accent | `--accent` / `--accent-light` (avatar, stat icons, bars, pills) |
  | Warning (unused here) | `--accent-2` |
  | Negative | `--danger` (don't use it for normal expense amounts) |
  | Radius | `--radius-sm` (pills, buttons), `--radius-md` (cards) |
  | Fonts | `--font-display` (h1, section titles, large values), `--font-body` (everything else) |

- All templates extend `base.html`
- Session guard first: `if not session.get("user_id"): return redirect(url_for("login"))`
- Sample data: name from `session["user_name"]`; email `demo@spendly.com`; transactions
  mirror the seed data in `seed_db()`; categories from `CATEGORIES` with the empty
  ones left out; `initials` from the first letters of the first two name words
- Do not query the database for profile data; that belongs to Step 5
- Reuse `.btn-ghost` for "Edit profile"; don't create a new button style
- Spacing on an 8px grid, using rem: `0.5 / 1 / 1.5 / 2rem`. Card padding is `1.5rem`
  everywhere, and the section gap is `1.5rem`. No odd values
- Type scale: values `1.5rem` display; section titles `1.25rem` display; labels and
  table headers `0.75rem` uppercase, `--ink-muted`, letter-spacing `0.04em`; body `0.875–1rem`
- Amounts: `font-variant-numeric: tabular-nums`, right-aligned, `₹` plus 2 decimals
  via `"{:,.2f}".format(x)`
- Cards: `1px solid var(--border)`, `--radius-md`, and no shadow (border beats shadow,
  matching `.feature-card` / `.auth-card`)
- Table: row hover `--paper-warm`, `border-bottom: 1px solid var(--border-soft)` between
  rows, no zebra stripes
- Bars: track `--accent-light`, fill `--accent`, 8px tall, fully rounded
- One icon per card, heading and button. Call `lucide.createIcons()` once
- "Edit profile" has no route and no JS (`aria-disabled="true"`, `cursor: not-allowed`)
- Responsive:
  - `≤900px`: `.profile-grid` becomes 1 column and `.profile-stats` 2 columns
  - `≤600px`: `.profile-stats` 1 column, header stacks (button under name),
    page padding `1rem`, `.profile-table-wrap { overflow-x: auto; }`
  - Leave the existing `.nav-user` hide rule at ≤600px alone; the profile link is hidden
    on phones like the rest of the navbar links
- Jinja autoescape everywhere; no `|safe`
- Don't touch the `/expenses/*` placeholder routes

## Definition of done
- [ ] `python app.py` starts with no errors
- [ ] Visiting `/profile` while signed out redirects to `/login`
- [ ] After signing in as `demo@spendly.com` / `demo123`, `/profile` renders the
      designed page (not the "coming in Step 4" string) with no Jinja errors
- [ ] Header shows a "DU" avatar, "Demo User", the email and a "Member since" date;
      "Edit profile" looks disabled and does nothing when clicked
- [ ] Four summary cards show their Lucide icon, label and value; amounts start with ₹
      and have 2 decimals
- [ ] Recent transactions shows up to 5 rows, newest first, category pills, amounts
      right-aligned; rows highlight on hover
- [ ] Category breakdown shows one bar per category with spending, longest first, with bar
      widths matching their percentages
- [ ] All icons render (no empty `<i data-lucide>` left in DevTools); console has no errors
- [ ] Clicking the name in the navbar (desktop) opens `/profile`; "Sign out" still works
- [ ] `grep -E "#[0-9a-fA-F]{3,6}" static/css/profile.css` returns nothing
- [ ] At ~800px: body is one column and stats are in 2 columns
- [ ] At ~375px: stats in 1 column, header stacked, table scrolls sideways, no
      horizontal page scroll
- [ ] Landing, login, register, terms and privacy pages still load and look unchanged
