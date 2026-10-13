import os
import sqlite3
from datetime import date

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import CATEGORIES, get_db, init_db, seed_db

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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Sample data mirroring seed_db(); Step 5 replaces this with real queries.
    today = date.today()
    sample = [
        (12.50, "Food", 2, "Lunch at cafe"),
        (45.00, "Transport", 4, "Monthly bus pass"),
        (120.75, "Bills", 6, "Electricity bill"),
        (30.00, "Health", 9, "Pharmacy"),
        (18.99, "Entertainment", 12, "Movie tickets"),
        (64.20, "Shopping", 15, "New shoes"),
        (9.99, "Other", 18, "Phone case"),
        (56.30, "Food", 21, "Groceries"),
        (22.40, "Transport", 23, "Taxi ride"),
        (75.00, "Bills", 24, "Internet bill"),
        (14.75, "Food", 25, "Coffee and snacks"),
        (40.00, "Health", 26, "Gym membership"),
        (29.99, "Shopping", 28, "Books"),
    ]
    expenses = [
        {"date": today.replace(day=d), "description": desc, "category": cat, "amount": amt}
        for amt, cat, d, desc in sample
    ]
    total = sum(e["amount"] for e in expenses)

    totals = {c: sum(e["amount"] for e in expenses if e["category"] == c) for c in CATEGORIES}
    categories = sorted(
        (
            {"name": c, "amount": amt, "percent": round(amt / total * 100)}
            for c, amt in totals.items()
            if amt > 0
        ),
        key=lambda c: c["amount"],
        reverse=True,
    )

    recent = sorted(expenses, key=lambda e: e["date"], reverse=True)[:10]
    transactions = [{**e, "date": e["date"].strftime("%d %b")} for e in recent]

    name = session.get("user_name", "")
    user = {
        "name": name,
        "email": "demo@spendly.com",
        "initials": "".join(w[0] for w in name.split()[:2]).upper(),
        "member_since": today.strftime("%b %Y"),
    }
    stats = {
        "total_spent": total,
        "month_spent": total,
        "transaction_count": len(expenses),
        "top_category": categories[0]["name"] if categories else "—",
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


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
