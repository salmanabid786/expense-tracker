import os
import sqlite3
from collections import defaultdict
from datetime import date, timedelta

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    get_db,
    get_expenses,
    get_month_total,
    get_user,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                conn.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            finally:
                conn.close()
        return render_template("register.html", error=error, name=name, email=email)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Please enter your email and password."
        else:
            conn = get_db()
            try:
                user = conn.execute(
                    "SELECT id, name, password_hash FROM users WHERE email = ?",
                    (email,),
                ).fetchone()
            finally:
                conn.close()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                return redirect(url_for("profile"))
            error = "Invalid email or password."
        return render_template("login.html", error=error, email=email)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _parse_date_range(args):
    """Return (start, end, error) from the query string; invalid input yields no range."""
    raw_start = args.get("start", "").strip()
    raw_end = args.get("end", "").strip()
    try:
        start = date.fromisoformat(raw_start) if raw_start else None
        end = date.fromisoformat(raw_end) if raw_end else None
    except ValueError:
        return None, None, "Please enter valid dates."
    if start and end and start > end:
        return None, None, "Start date must be on or before end date."
    return start, end, None


def _date_presets(today):
    """Return the preset chips (key, label, ISO start/end) relative to today."""
    ranges = [
        ("month", "This month", today.replace(day=1)),
        ("30d", "Last 30 days", today - timedelta(days=29)),
        ("3m", "Last 3 months", today - timedelta(days=89)),
        ("year", "This year", today.replace(month=1, day=1)),
    ]
    presets = [
        {"key": key, "label": label, "start": start.isoformat(), "end": today.isoformat()}
        for key, label, start in ranges
    ]
    presets.append({"key": "all", "label": "All time", "start": "", "end": ""})
    return presets


def _build_date_filter(start, end, error, today):
    """Return the `filter` dict the profile template expects."""
    presets = _date_presets(today)
    start_iso = start.isoformat() if start else ""
    end_iso = end.isoformat() if end else ""
    preset = next(
        (p["key"] for p in presets if p["start"] == start_iso and p["end"] == end_iso), ""
    )
    if start and end:
        label = f"{start:%d %b %Y} – {end:%d %b %Y}"
    elif start:
        label = f"from {start:%d %b %Y}"
    elif end:
        label = f"until {end:%d %b %Y}"
    else:
        label = "all time"

    return {
        "start": start_iso,
        "end": end_iso,
        "active": bool(start or end),
        "label": label,
        "preset": preset,
        "presets": presets,
        "error": error,
    }


def _parse_stored_date(value):
    """Parse a stored YYYY-MM-DD[...] value; return None if it is missing or malformed."""
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = date.today()
    start, end, error = _parse_date_range(request.args)

    row = get_user(user_id)
    if row is None:
        session.clear()
        return redirect(url_for("login"))
    expenses = get_expenses(user_id, start, end)
    month_spent = get_month_total(user_id, today)

    total = sum(e["amount"] for e in expenses)

    totals = defaultdict(float)
    for e in expenses:
        totals[e["category"]] += e["amount"]
    categories = sorted(
        (
            {"name": c, "amount": amt, "percent": round(amt / total * 100) if total else 0}
            for c, amt in totals.items()
            if amt > 0
        ),
        key=lambda c: c["amount"],
        reverse=True,
    )

    transactions = []
    for e in expenses[:10]:
        spent_on = _parse_stored_date(e["date"])
        transactions.append({
            "date": spent_on.strftime("%d %b") if spent_on else e["date"],
            "description": e["description"] or "",
            "category": e["category"],
            "amount": e["amount"],
        })

    name = row["name"]
    created = _parse_stored_date(row["created_at"]) or today
    user = {
        "name": name,
        "email": row["email"],
        "initials": "".join(w[0] for w in name.split()[:2]).upper(),
        "member_since": created.strftime("%b %Y"),
    }
    stats = {
        "total_spent": total,
        "month_spent": month_spent,
        "transaction_count": len(expenses),
        "top_category": categories[0]["name"] if categories else "—",
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filter=_build_date_filter(start, end, error, today),
    )


@app.route("/business-analytics")
def business_analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if get_user(session["user_id"]) is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template("business_analytics.html")


@app.route("/terms-and-conditions")
def terms_and_conditions():
    return render_template("terms.html")


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
