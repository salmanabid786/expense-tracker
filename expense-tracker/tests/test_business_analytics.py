"""Tests for the Business Analytics coming-soon page: GET /business-analytics"""
import sqlite3

from werkzeug.security import generate_password_hash

import database.db as db_module


def add_user(name, email):
    conn = sqlite3.connect(db_module.DB_PATH)
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash("password123")),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def login_as(client, user_id, name="Asha Rao"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def test_redirects_to_login_when_logged_out(client):
    resp = client.get("/business-analytics")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_redirects_and_clears_session_for_missing_user(client):
    login_as(client, 9999)
    resp = client.get("/business-analytics")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_renders_for_logged_in_user(client):
    uid = add_user("Asha Rao", "asha@example.com")
    login_as(client, uid)
    resp = client.get("/business-analytics")
    page = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Smarter insights are on the way." in page
    assert "Revenue overview" in page
    assert "Notify me" in page
    assert "ba-topbar" not in page
    assert 'aria-current="page"' in page


def test_navbar_link_only_shown_after_login(client):
    page = client.get("/").get_data(as_text=True)
    assert 'href="/business-analytics"' not in page

    uid = add_user("Asha Rao", "asha@example.com")
    login_as(client, uid)
    page = client.get("/").get_data(as_text=True)
    assert 'href="/business-analytics"' in page
