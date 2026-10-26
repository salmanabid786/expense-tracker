import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def get_expenses(user_id, start=None, end=None):
    """Return the user's expenses, newest first, optionally limited to [start, end]."""
    where = ["user_id = ?"]
    params = [user_id]
    if start:
        where.append("date >= ?")
        params.append(start.isoformat())
    if end:
        where.append("date <= ?")
        params.append(end.isoformat())

    conn = get_db()
    try:
        return conn.execute(
            "SELECT amount, category, date, description FROM expenses WHERE "
            + " AND ".join(where)
            + " ORDER BY date DESC, id DESC",
            params,
        ).fetchall()
    finally:
        conn.close()


def get_month_total(user_id, today):
    """Return the user's spending from the 1st of today's month up to today."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses"
            " WHERE user_id = ? AND date >= ? AND date <= ?",
            (user_id, today.replace(day=1).isoformat(), today.isoformat()),
        ).fetchone()[0]
    finally:
        conn.close()


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    def day(n):
        return date.today().replace(day=n).strftime("%Y-%m-%d")

    expenses = [
        (user_id, 12.50, "Food", day(2), "Lunch at cafe"),
        (user_id, 45.00, "Transport", day(4), "Monthly bus pass"),
        (user_id, 120.75, "Bills", day(6), "Electricity bill"),
        (user_id, 30.00, "Health", day(9), "Pharmacy"),
        (user_id, 18.99, "Entertainment", day(12), "Movie tickets"),
        (user_id, 64.20, "Shopping", day(15), "New shoes"),
        (user_id, 9.99, "Other", day(18), "Phone case"),
        (user_id, 56.30, "Food", day(21), "Groceries"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
