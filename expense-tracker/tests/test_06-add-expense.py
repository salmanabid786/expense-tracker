"""Tests for spec 06-add-expense: GET/POST /expenses/add."""
import html
import sqlite3
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module

ADD_URL = "/expenses/add"
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

ERR_AMOUNT = "Please enter a valid amount greater than 0."
ERR_CATEGORY = "Please choose a valid category."
ERR_DATE = "Please enter a valid date."
ERR_DESC = "Description must be 200 characters or fewer."

TODAY = date.today().isoformat()


# ------------------------------------------------------------------ helpers
def _conn():
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_user(name, email, password="password123"):
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def insert_row(user_id, amount, category, day, description):
    conn = _conn()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, day, description),
    )
    conn.commit()
    conn.close()


def all_expenses():
    conn = _conn()
    rows = conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    conn.close()
    return rows


def login(client, email, password="password123"):
    return client.post("/login", data={"email": email, "password": password})


def form(**overrides):
    data = {"amount": "12.50", "category": "Food", "date": TODAY, "description": "Coffee"}
    data.update(overrides)
    return data


def post_add(client, **overrides):
    return client.post(ADD_URL, data=form(**overrides))


@pytest.fixture
def user(flask_app):
    return add_user("Alice Smith", "alice@example.com")


@pytest.fixture
def other_user(flask_app):
    return add_user("Bob Other", "bob@example.com")


@pytest.fixture
def auth(client, user):
    resp = login(client, "alice@example.com")
    assert resp.status_code == 302, "Login should succeed"
    return client


# ------------------------------------------------------------------ auth guards
class TestAuthGuards:
    def test_get_signed_out_redirects_to_login(self, client):
        resp = client.get(ADD_URL)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_post_signed_out_redirects_to_login_and_inserts_nothing(self, client, user):
        resp = post_add(client)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")
        assert all_expenses() == [], "No row may be inserted when signed out"

    def test_get_stale_session_clears_session_and_redirects(self, client, flask_app):
        with client.session_transaction() as sess:
            sess["user_id"] = 9999
        resp = client.get(ADD_URL)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")
        with client.session_transaction() as sess:
            assert "user_id" not in sess, "Stale session should be cleared"

    def test_post_stale_session_clears_session_and_inserts_nothing(self, client, flask_app):
        with client.session_transaction() as sess:
            sess["user_id"] = 9999
        resp = post_add(client)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")
        with client.session_transaction() as sess:
            assert "user_id" not in sess
        assert all_expenses() == []


# ------------------------------------------------------------------ GET form
class TestGetForm:
    def test_get_returns_200_with_form_fields(self, auth):
        resp = auth.get(ADD_URL)
        page = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert 'name="amount"' in page
        assert 'name="category"' in page
        assert 'name="date"' in page
        assert 'name="description"' in page
        assert "Add an expense" in page
        assert "Record what you spent and when" in page

    def test_get_form_posts_to_add_url(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        assert 'method="post"' in page.lower()
        assert f'action="{ADD_URL}"' in page

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_get_select_contains_each_category(self, auth, category):
        page = auth.get(ADD_URL).get_data(as_text=True)
        assert f">{category}<" in page, f"{category} missing from select"

    def test_get_select_has_all_seven_categories(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        select = page[page.index("<select"):page.index("</select>")]
        assert select.count("<option") == 8, "7 categories plus the placeholder option"
        assert "Choose a category" in select
        assert "disabled" in select

    def test_get_date_prefilled_with_today(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        assert f'value="{TODAY}"' in page

    def test_get_has_no_error_box_content(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        for msg in (ERR_AMOUNT, ERR_CATEGORY, ERR_DATE, ERR_DESC):
            assert msg not in page

    def test_get_has_cancel_link_to_profile(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        assert "Cancel" in page
        assert 'href="/profile"' in page


# ------------------------------------------------------------------ happy path
class TestHappyPath:
    def test_post_valid_redirects_to_profile(self, auth):
        resp = post_add(auth)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/profile")

    def test_post_valid_inserts_row_for_session_user(self, auth, user):
        post_add(auth, amount="12.50", category="Food", date="2026-10-28", description="Coffee")
        rows = all_expenses()
        assert len(rows) == 1
        row = rows[0]
        assert row["user_id"] == user
        assert row["amount"] == pytest.approx(12.50)
        assert row["category"] == "Food"
        assert row["date"] == "2026-10-28"
        assert row["description"] == "Coffee"

    def test_post_amount_rounded_to_two_decimals(self, auth):
        post_add(auth, amount="12.3456")
        assert all_expenses()[0]["amount"] == pytest.approx(12.35)

    def test_post_amount_rounds_up_to_whole(self, auth):
        post_add(auth, amount="7.999")
        assert all_expenses()[0]["amount"] == pytest.approx(8.00)

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_post_every_valid_category_accepted(self, auth, category):
        resp = post_add(auth, category=category)
        assert resp.status_code == 302
        assert all_expenses()[0]["category"] == category

    def test_post_amount_exactly_one_million_accepted(self, auth):
        resp = post_add(auth, amount="1000000")
        assert resp.status_code == 302
        assert all_expenses()[0]["amount"] == pytest.approx(1_000_000)

    def test_post_smallest_amount_accepted(self, auth):
        resp = post_add(auth, amount="0.01")
        assert resp.status_code == 302
        assert all_expenses()[0]["amount"] == pytest.approx(0.01)

    def test_post_description_stripped(self, auth):
        post_add(auth, description="   Lunch   ")
        assert all_expenses()[0]["description"] == "Lunch"

    def test_post_empty_description_stored_as_null(self, auth):
        resp = post_add(auth, description="")
        assert resp.status_code == 302
        assert all_expenses()[0]["description"] is None

    def test_post_whitespace_description_stored_as_null(self, auth):
        post_add(auth, description="    ")
        assert all_expenses()[0]["description"] is None

    def test_post_missing_description_field_stored_as_null(self, auth):
        data = form()
        del data["description"]
        resp = auth.post(ADD_URL, data=data)
        assert resp.status_code == 302
        assert all_expenses()[0]["description"] is None

    def test_post_description_exactly_200_chars_accepted(self, auth):
        desc = "d" * 200
        resp = post_add(auth, description=desc)
        assert resp.status_code == 302
        assert all_expenses()[0]["description"] == desc

    def test_new_expense_appears_on_profile(self, auth):
        post_add(auth, amount="12.50", description="unique-coffee-marker")
        resp = auth.get("/profile")
        page = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert "unique-coffee-marker" in page
        assert "12.50" in page

    def test_follow_redirect_lands_on_profile(self, auth):
        resp = auth.post(ADD_URL, data=form(description="followed-marker"), follow_redirects=True)
        assert resp.status_code == 200
        assert "followed-marker" in resp.get_data(as_text=True)

    def test_description_is_html_escaped_on_profile(self, auth):
        post_add(auth, description="<script>alert(1)</script>")
        page = auth.get("/profile").get_data(as_text=True)
        assert "<script>alert(1)</script>" not in page

    def test_sql_injection_description_stored_literally(self, auth):
        payload = "x'); DROP TABLE expenses;--"
        resp = post_add(auth, description=payload)
        assert resp.status_code == 302
        rows = all_expenses()
        assert len(rows) == 1 and rows[0]["description"] == payload

    def test_multiple_posts_insert_multiple_rows(self, auth):
        post_add(auth, description="one")
        post_add(auth, description="two")
        assert [r["description"] for r in all_expenses()] == ["one", "two"]


# ------------------------------------------------------------------ validation
def assert_rejected(resp, message):
    page = resp.get_data(as_text=True)
    assert resp.status_code == 200, "Validation errors re-render with HTTP 200"
    assert html.escape(message, quote=True) in page or message in page, (
        f"Expected error {message!r}"
    )
    assert all_expenses() == [], "No row may be inserted on validation error"
    return page


class TestAmountValidation:
    @pytest.mark.parametrize(
        "amount",
        ["0", "0.00", "-5", "-0.01", "abc", "", "   ", "nan", "NaN", "inf", "-inf",
         "Infinity", "1000000.01", "1e9", "1,5", "0.004"],
    )
    def test_invalid_amount_shows_error(self, auth, amount):
        resp = post_add(auth, amount=amount)
        assert_rejected(resp, ERR_AMOUNT)

    def test_missing_amount_field_shows_error(self, auth):
        data = form()
        del data["amount"]
        resp = auth.post(ADD_URL, data=data)
        assert_rejected(resp, ERR_AMOUNT)

    def test_invalid_amount_keeps_other_values(self, auth):
        resp = post_add(auth, amount="abc", category="Bills", date="2026-05-06",
                        description="kept-desc")
        page = assert_rejected(resp, ERR_AMOUNT)
        assert 'value="abc"' in page
        assert 'value="2026-05-06"' in page
        assert 'value="kept-desc"' in page
        assert "selected" in page

    def test_invalid_amount_selected_category_preserved(self, auth):
        resp = post_add(auth, amount="-5", category="Health")
        page = assert_rejected(resp, ERR_AMOUNT)
        select = page[page.index("<select"):page.index("</select>")]
        option = select[select.index(">Health<") - 80:select.index(">Health<")]
        assert "selected" in option, "Submitted category should stay selected"


class TestCategoryValidation:
    @pytest.mark.parametrize("category", ["Crypto", "food", "FOOD", " ", "Food2", "'; DROP TABLE expenses;--"])
    def test_tampered_category_shows_error(self, auth, category):
        resp = post_add(auth, category=category)
        assert_rejected(resp, ERR_CATEGORY)

    def test_missing_category_field_shows_error(self, auth):
        data = form()
        del data["category"]
        resp = auth.post(ADD_URL, data=data)
        assert_rejected(resp, ERR_CATEGORY)

    def test_empty_category_shows_error(self, auth):
        resp = post_add(auth, category="")
        assert_rejected(resp, ERR_CATEGORY)

    def test_category_error_keeps_other_values(self, auth):
        resp = post_add(auth, category="Crypto", amount="33.30", description="kept-desc")
        page = assert_rejected(resp, ERR_CATEGORY)
        assert 'value="33.30"' in page
        assert 'value="kept-desc"' in page


class TestDateValidation:
    @pytest.mark.parametrize(
        "bad_date", ["2026-13-40", "abc", "", "2026-02-30", "28/10/2026", "2026-1-1x"]
    )
    def test_invalid_date_shows_error_not_500(self, auth, bad_date):
        resp = post_add(auth, date=bad_date)
        assert_rejected(resp, ERR_DATE)

    def test_missing_date_field_shows_error(self, auth):
        data = form()
        del data["date"]
        resp = auth.post(ADD_URL, data=data)
        assert_rejected(resp, ERR_DATE)

    def test_date_error_keeps_other_values(self, auth):
        resp = post_add(auth, date="2026-13-40", amount="9.99", description="kept-desc")
        page = assert_rejected(resp, ERR_DATE)
        assert 'value="9.99"' in page
        assert 'value="kept-desc"' in page


class TestDescriptionValidation:
    def test_201_char_description_rejected(self, auth):
        resp = post_add(auth, description="y" * 201)
        assert_rejected(resp, ERR_DESC)

    def test_long_description_with_padding_counts_after_strip(self, auth):
        # 200 real chars plus surrounding whitespace is valid once stripped.
        resp = post_add(auth, description="  " + "z" * 200 + "  ")
        assert resp.status_code == 302
        assert all_expenses()[0]["description"] == "z" * 200

    def test_description_error_refills_form(self, auth):
        desc = "w" * 201
        resp = post_add(auth, description=desc, amount="4.00")
        page = assert_rejected(resp, ERR_DESC)
        assert 'value="4.00"' in page
        assert desc in page


class TestFirstErrorOrdering:
    def test_amount_error_wins_over_all_others(self, auth):
        resp = post_add(auth, amount="0", category="Crypto", date="abc", description="q" * 201)
        page = assert_rejected(resp, ERR_AMOUNT)
        for other in (ERR_CATEGORY, ERR_DATE, ERR_DESC):
            assert other not in page, "Only the first error should be shown"

    def test_category_error_wins_over_date_and_description(self, auth):
        resp = post_add(auth, category="Crypto", date="abc", description="q" * 201)
        page = assert_rejected(resp, ERR_CATEGORY)
        for other in (ERR_AMOUNT, ERR_DATE, ERR_DESC):
            assert other not in page

    def test_date_error_wins_over_description(self, auth):
        resp = post_add(auth, date="abc", description="q" * 201)
        page = assert_rejected(resp, ERR_DATE)
        for other in (ERR_AMOUNT, ERR_CATEGORY, ERR_DESC):
            assert other not in page


# ------------------------------------------------------------------ ownership / isolation
class TestOwnershipAndIsolation:
    def test_user_id_in_form_is_ignored(self, auth, user, other_user):
        resp = auth.post(ADD_URL, data=form(user_id=str(other_user)))
        assert resp.status_code == 302
        rows = all_expenses()
        assert len(rows) == 1
        assert rows[0]["user_id"] == user, "Row must belong to the session user"

    def test_second_users_expense_not_on_first_users_profile(self, client, user, other_user):
        login(client, "bob@example.com")
        post_add(client, description="bob-private-marker", amount="777.00")
        client.get("/logout")
        login(client, "alice@example.com")
        page = client.get("/profile").get_data(as_text=True)
        assert "bob-private-marker" not in page
        assert "777.00" not in page

    def test_each_user_expense_owned_by_that_user(self, client, user, other_user):
        login(client, "alice@example.com")
        post_add(client, description="alice-row")
        client.get("/logout")
        login(client, "bob@example.com")
        post_add(client, description="bob-row")
        owners = {r["description"]: r["user_id"] for r in all_expenses()}
        assert owners == {"alice-row": user, "bob-row": other_user}

    def test_existing_other_user_expenses_untouched(self, auth, user, other_user):
        insert_row(other_user, 5.0, "Other", "2020-01-01", "bob-existing")
        post_add(auth)
        rows = all_expenses()
        assert len(rows) == 2
        assert [r["user_id"] for r in rows if r["description"] == "bob-existing"] == [other_user]


# ------------------------------------------------------------------ navigation entry points
class TestEntryPoints:
    def test_nav_link_hidden_when_signed_out(self, client):
        page = client.get("/").get_data(as_text=True)
        assert ADD_URL not in page
        assert "Add expense" not in page

    def test_nav_link_hidden_on_login_page_when_signed_out(self, client):
        page = client.get("/login").get_data(as_text=True)
        assert ADD_URL not in page

    def test_nav_link_shown_when_signed_in(self, auth):
        page = auth.get("/profile").get_data(as_text=True)
        assert f'href="{ADD_URL}"' in page
        assert "Add expense" in page

    def test_nav_link_shown_on_add_page_itself(self, auth):
        page = auth.get(ADD_URL).get_data(as_text=True)
        assert f'href="{ADD_URL}"' in page

    def test_profile_add_link_opens_form(self, auth):
        resp = auth.get(ADD_URL)
        assert resp.status_code == 200


# ------------------------------------------------------------------ untouched placeholders
class TestPlaceholdersUntouched:
    def test_edit_placeholder_still_a_placeholder(self, auth):
        resp = auth.get("/expenses/1/edit")
        assert resp.status_code == 200
        assert "coming in" in resp.get_data(as_text=True).lower()

    def test_delete_placeholder_still_a_placeholder(self, auth):
        resp = auth.get("/expenses/1/delete")
        assert resp.status_code == 200
        assert "coming in" in resp.get_data(as_text=True).lower()
