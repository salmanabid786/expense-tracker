"""Tests for spec 05-profile-date-filter: GET /profile?start=...&end=..."""
import html
import re
import sqlite3
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module

ERR_INVALID = "Please enter valid dates."
ERR_ORDER = "Start date must be on or before end date."


# ------------------------------------------------------------------ helpers
def _conn():
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_user(name, email, created_at="2026-03-05 10:00:00"):
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, generate_password_hash("password123"), created_at),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def add_expense(user_id, amount, category, day, description):
    conn = _conn()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, day, description),
    )
    conn.commit()
    conn.close()


def login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def get_profile(client, query=""):
    resp = client.get("/profile" + query)
    return resp, resp.get_data(as_text=True)


def chip_tags(page):
    return [html.unescape(t) for t in re.findall(r"<a\b[^>]*>", page) if "profile-chip" in t]


@pytest.fixture
def user(flask_app):
    """Primary user with fixed-date expenses in 2020 plus one dated today."""
    uid = add_user("Alice Smith", "alice@example.com", "2026-03-05 10:00:00")
    add_expense(uid, 10.00, "Food", "2020-01-10", "alpha-jan10")
    add_expense(uid, 20.00, "Transport", "2020-01-20", "bravo-jan20")
    add_expense(uid, 30.00, "Food", "2020-02-05", "charlie-feb05")
    add_expense(uid, 40.00, "Bills", "2020-03-15", "delta-mar15")
    add_expense(uid, 5.00, "Other", date.today().isoformat(), "echo-today")
    return uid


@pytest.fixture
def other_user(flask_app):
    uid = add_user("Bob Other", "bob@example.com")
    add_expense(uid, 999.00, "Shopping", "2020-01-15", "bobsecret-jan15")
    return uid


@pytest.fixture
def auth(client, user):
    login_as(client, user)
    return client


# ------------------------------------------------------------------ auth
class TestAuth:
    def test_profile_signed_out_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_profile_signed_out_with_filter_params_redirects_to_login(self, client):
        resp = client.get("/profile?start=2020-01-01&end=2020-01-31")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_stale_session_clears_session_and_redirects_to_login(self, client, flask_app):
        login_as(client, 99999)
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        with client.session_transaction() as sess:
            assert "user_id" not in sess


# ------------------------------------------------------------------ real data
class TestRealData:
    def test_profile_shows_real_user_name_email_and_member_since(self, auth):
        resp, page = get_profile(auth)
        assert resp.status_code == 200
        assert "Alice Smith" in page
        assert "alice@example.com" in page
        assert "Mar 2026" in page

    def test_profile_shows_user_expenses_from_db(self, auth):
        _, page = get_profile(auth)
        for desc in ("alpha-jan10", "bravo-jan20", "charlie-feb05", "delta-mar15", "echo-today"):
            assert desc in page, f"{desc} should be listed"

    def test_profile_does_not_show_hardcoded_sample_data_for_user_without_expenses(self, client, flask_app):
        uid = add_user("Empty Person", "empty@example.com")
        login_as(client, uid)
        resp, page = get_profile(client)
        assert resp.status_code == 200
        assert "No expenses yet" in page
        assert "Empty Person" in page

    def test_new_user_does_not_see_other_users_data(self, client, user, other_user):
        uid = add_user("Carol New", "carol@example.com")
        login_as(client, uid)
        _, page = get_profile(client)
        for secret in ("alpha-jan10", "bobsecret-jan15", "echo-today"):
            assert secret not in page

    def test_user_never_sees_other_users_expenses_even_with_matching_range(self, auth, other_user):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "bobsecret-jan15" not in page
        assert "alpha-jan10" in page

    def test_other_user_sees_only_their_own_expenses(self, client, user, other_user):
        login_as(client, other_user)
        _, page = get_profile(client)
        assert "bobsecret-jan15" in page
        assert "alpha-jan10" not in page


# ------------------------------------------------------------------ filter rules
class TestFilterRules:
    def test_no_params_shows_all_time_without_error(self, auth):
        _, page = get_profile(auth)
        assert "all time" in page.lower()
        assert ERR_INVALID not in page
        assert ERR_ORDER not in page
        assert "profile-filter-error" not in page

    def test_filter_card_present(self, auth):
        _, page = get_profile(auth)
        assert "profile-filter" in page

    def test_both_dates_filters_inclusive_range(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "alpha-jan10" in page
        assert "bravo-jan20" in page
        assert "charlie-feb05" not in page
        assert "delta-mar15" not in page
        assert "echo-today" not in page

    def test_start_and_end_bounds_are_inclusive(self, auth):
        _, page = get_profile(auth, "?start=2020-01-10&end=2020-01-20")
        assert "alpha-jan10" in page
        assert "bravo-jan20" in page
        assert "charlie-feb05" not in page

    def test_same_day_range_includes_that_day(self, auth):
        _, page = get_profile(auth, "?start=2020-01-10&end=2020-01-10")
        assert "alpha-jan10" in page
        assert "bravo-jan20" not in page
        assert ERR_ORDER not in page

    def test_only_start_includes_everything_from_start_onward(self, auth):
        _, page = get_profile(auth, "?start=2020-02-05")
        assert "alpha-jan10" not in page
        assert "bravo-jan20" not in page
        assert "charlie-feb05" in page
        assert "delta-mar15" in page
        assert "echo-today" in page

    def test_only_end_includes_everything_up_to_end(self, auth):
        _, page = get_profile(auth, "?end=2020-02-05")
        assert "alpha-jan10" in page
        assert "bravo-jan20" in page
        assert "charlie-feb05" in page
        assert "delta-mar15" not in page
        assert "echo-today" not in page

    @pytest.mark.parametrize("query", ["?start=&end=", "?start=", "?end="])
    def test_empty_strings_treated_as_missing(self, auth, query):
        resp, page = get_profile(auth, query)
        assert resp.status_code == 200
        assert ERR_INVALID not in page
        assert ERR_ORDER not in page
        assert "alpha-jan10" in page and "delta-mar15" in page

    def test_empty_start_with_valid_end_acts_as_only_end(self, auth):
        _, page = get_profile(auth, "?start=&end=2020-01-31")
        assert "alpha-jan10" in page
        assert "charlie-feb05" not in page
        assert ERR_INVALID not in page

    def test_range_with_no_expenses_shows_empty_period_message(self, auth):
        _, page = get_profile(auth, "?start=2019-01-01&end=2019-12-31")
        assert "No expenses in this period" in page
        assert "alpha-jan10" not in page

    def test_all_time_with_no_expenses_keeps_no_expenses_yet(self, client, flask_app):
        uid = add_user("Empty Person", "empty2@example.com")
        login_as(client, uid)
        _, page = get_profile(client)
        assert "No expenses yet" in page
        assert "No expenses in this period" not in page


# ------------------------------------------------------------------ validation
class TestValidation:
    @pytest.mark.parametrize(
        "query",
        [
            "?start=2026-13-01",
            "?start=abc",
            "?end=abc",
            "?start=2020-02-30",
            "?start=2020-01-01&end=notadate",
            "?start=notadate&end=2020-01-31",
            "?start=01/02/2020",
            "?start=' OR 1=1 --",
            "?start=2020-01-01;DROP TABLE expenses",
        ],
    )
    def test_invalid_date_shows_error_and_falls_back_to_all_time(self, auth, query):
        resp, page = get_profile(auth, query)
        assert resp.status_code == 200, "invalid dates must not cause a 500"
        assert ERR_INVALID in page
        assert "profile-filter-error" in page
        for desc in ("alpha-jan10", "bravo-jan20", "charlie-feb05", "delta-mar15", "echo-today"):
            assert desc in page, "invalid range should fall back to all time"

    def test_invalid_end_ignores_valid_start_too(self, auth):
        _, page = get_profile(auth, "?start=2020-03-01&end=garbage")
        assert ERR_INVALID in page
        assert "alpha-jan10" in page, "both params must be ignored on error"

    def test_start_after_end_shows_order_error_and_all_time(self, auth):
        resp, page = get_profile(auth, "?start=2020-03-20&end=2020-01-01")
        assert resp.status_code == 200
        assert ERR_ORDER in page
        assert "alpha-jan10" in page and "delta-mar15" in page

    def test_error_not_shown_for_valid_range(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert ERR_INVALID not in page
        assert ERR_ORDER not in page

    def test_sql_injection_in_params_does_not_damage_db(self, auth):
        get_profile(auth, "?start=2020-01-01'; DROP TABLE expenses;--")
        conn = _conn()
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert count == 5, "expenses table must be intact"

    def test_very_long_param_does_not_500(self, auth):
        resp, page = get_profile(auth, "?start=" + "9" * 5000)
        assert resp.status_code == 200
        assert ERR_INVALID in page

    def test_error_inputs_are_not_reflected_unescaped(self, auth):
        _, page = get_profile(auth, "?start=<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in page


# ------------------------------------------------------------------ stats / data
class TestStatsAndBreakdown:
    def test_total_reflects_filtered_range(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "30.00" in page  # 10 + 20

    def test_total_all_time_includes_everything(self, auth):
        _, page = get_profile(auth)
        assert "105.00" in page  # 10+20+30+40+5

    def test_empty_range_shows_zero_total(self, auth):
        _, page = get_profile(auth, "?start=2019-01-01&end=2019-12-31")
        assert "0.00" in page
        assert "—" in page, "top category placeholder expected"

    def test_top_category_is_computed_within_range(self, auth):
        # Jan: Food 10, Transport 20 -> Transport. All time: Bills 40 is top.
        _, page_jan = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "Transport" in page_jan
        assert "Bills" not in page_jan
        _, page_all = get_profile(auth)
        assert "Bills" in page_all

    def test_category_breakdown_omits_categories_outside_range(self, auth):
        _, page = get_profile(auth, "?start=2020-03-01&end=2020-03-31")
        assert "Bills" in page
        assert "Transport" not in page
        assert "Food" not in page

    def test_category_percent_values_for_range(self, auth):
        # Jan: Food 10, Transport 20 => 33% and 67%
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "33" in page and "67" in page

    def test_category_breakdown_sorted_by_amount_desc(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-03-31")
        # Bills 40, Food 40 (10+30), Transport 20 -> Transport must come last
        assert page.rfind("Transport") > page.find("Bills")
        assert page.rfind("Transport") > page.find("Food")

    def test_month_spent_unaffected_by_filter(self, auth):
        # Only the 5.00 expense dated today lies in the current month.
        _, page_all = get_profile(auth)
        _, page_old = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        _, page_empty = get_profile(auth, "?start=2019-01-01&end=2019-01-31")
        for page in (page_all, page_old, page_empty):
            assert "5.00" in page, "month_spent must stay at 5.00 regardless of filter"

    def test_total_label_changes_when_range_active(self, auth):
        _, page_all = get_profile(auth)
        _, page_range = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "Total spent" in page_all
        assert "Spent in period" not in page_all
        assert "Spent in period" in page_range

    def test_transactions_newest_first(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-03-31")
        positions = [page.find(d) for d in ("delta-mar15", "charlie-feb05", "bravo-jan20", "alpha-jan10")]
        assert all(p >= 0 for p in positions)
        assert positions == sorted(positions), "transactions must be listed newest first"

    def test_transactions_date_format_day_month(self, auth):
        _, page = get_profile(auth, "?start=2020-03-01&end=2020-03-31")
        assert "15 Mar" in page

    def test_transactions_limited_to_ten_but_stats_count_all(self, client, flask_app):
        uid = add_user("Many Spender", "many@example.com")
        for i in range(1, 13):
            add_expense(uid, 1.00, "Food", f"2020-05-{i:02d}", f"manyitem-{i:02d}")
        login_as(client, uid)
        _, page = get_profile(client, "?start=2020-05-01&end=2020-05-31")
        shown = [i for i in range(1, 13) if f"manyitem-{i:02d}" in page]
        assert len(shown) == 10
        assert shown == list(range(3, 13)), "the 10 newest should be shown"
        assert "12.00" in page, "total should include all 12 rows"

    def test_zero_amount_category_omitted_without_crash(self, client, flask_app):
        uid = add_user("Zero Person", "zero@example.com")
        add_expense(uid, 0.0, "Health", "2020-06-01", "zeroitem")
        login_as(client, uid)
        resp, page = get_profile(client, "?start=2020-06-01&end=2020-06-30")
        assert resp.status_code == 200, "total == 0 must not divide by zero"


# ------------------------------------------------------------------ presets / UI
class TestFilterUI:
    def test_five_preset_chips_rendered(self, auth):
        _, page = get_profile(auth)
        chips = chip_tags(page)
        assert len(chips) == 5, f"expected 5 chips, got {chips}"
        for label in ("This month", "Last 30 days", "Last 3 months", "This year", "All time"):
            assert label in page

    def test_all_time_chip_active_by_default_with_caption(self, auth):
        _, page = get_profile(auth)
        active = [t for t in chip_tags(page) if "is-active" in t]
        assert len(active) == 1
        assert re.search(r'href="/profile"', active[0]), "All time chip links to bare /profile"
        assert "Showing all time" in page or "Showing" in page and "all time" in page

    def test_all_time_chip_has_no_query_params(self, auth):
        _, page = get_profile(auth)
        no_param = [t for t in chip_tags(page) if re.search(r'href="/profile"', t)]
        assert len(no_param) == 1

    def test_preset_chip_hrefs_use_expected_ranges(self, auth):
        today = date.today()
        expected = {
            "month": today.replace(day=1),
            "30d": today - timedelta(days=29),
            "3m": today - timedelta(days=89),
            "year": today.replace(month=1, day=1),
        }
        _, page = get_profile(auth)
        tags = " ".join(chip_tags(page))
        for start in expected.values():
            assert f"start={start.isoformat()}" in tags
        assert tags.count(f"end={today.isoformat()}") == 4

    @pytest.mark.parametrize(
        "key",
        ["month", "30d", "3m", "year"],
    )
    def test_preset_range_marks_matching_chip_active(self, auth, key):
        today = date.today()
        start = {
            "month": today.replace(day=1),
            "30d": today - timedelta(days=29),
            "3m": today - timedelta(days=89),
            "year": today.replace(month=1, day=1),
        }[key]
        _, page = get_profile(auth, f"?start={start.isoformat()}&end={today.isoformat()}")
        active = [t for t in chip_tags(page) if "is-active" in t]
        assert len(active) >= 1
        assert any(f"start={start.isoformat()}" in t for t in active)
        assert not any(re.search(r'href="/profile"', t) for t in active), "All time must not be active"

    def test_this_month_preset_includes_todays_expense(self, auth):
        today = date.today()
        _, page = get_profile(auth, f"?start={today.replace(day=1).isoformat()}&end={today.isoformat()}")
        assert "echo-today" in page
        assert "alpha-jan10" not in page

    def test_custom_range_has_no_active_chip(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert not [t for t in chip_tags(page) if "is-active" in t]

    def test_date_inputs_prefilled_with_active_range(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert 'type="date"' in page
        assert 'value="2020-01-01"' in page
        assert 'value="2020-01-31"' in page
        assert 'name="start"' in page and 'name="end"' in page

    def test_filter_form_uses_get_method(self, auth):
        _, page = get_profile(auth)
        assert re.search(r'<form[^>]*method="get"', page, re.I)

    def test_caption_shows_formatted_range(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "01 Jan 2020" in page
        assert "31 Jan 2020" in page
        assert "Showing" in page

    def test_clear_link_goes_to_bare_profile(self, auth):
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "Clear" in page
        assert 'href="/profile"' in page

    def test_error_message_inside_filter_card(self, auth):
        _, page = get_profile(auth, "?start=abc")
        assert "profile-filter-error" in page
        assert page.find("profile-filter") < page.find(ERR_INVALID)

    def test_error_state_inputs_not_prefilled_and_all_time_active(self, auth):
        _, page = get_profile(auth, "?start=2020-03-20&end=2020-01-01")
        assert 'value="2020-03-20"' not in page
        assert 'value="2020-01-01"' not in page
        active = [t for t in chip_tags(page) if "is-active" in t]
        assert len(active) == 1 and re.search(r'href="/profile"', active[0])

    def test_filter_card_not_hardcoded_to_javascript(self, auth):
        _, page = get_profile(auth)
        assert "profile-filter" in page
        assert "lucide" in page.lower()


# ------------------------------------------------------------------ DB side effects
class TestNoSideEffects:
    def test_filtering_does_not_modify_expenses(self, auth):
        conn = _conn()
        before = [tuple(r) for r in conn.execute("SELECT * FROM expenses ORDER BY id")]
        conn.close()
        get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        get_profile(auth, "?start=bad")
        get_profile(auth, "?start=2021-01-01&end=2020-01-01")
        conn = _conn()
        after = [tuple(r) for r in conn.execute("SELECT * FROM expenses ORDER BY id")]
        conn.close()
        assert before == after

    def test_new_expense_in_db_appears_in_range(self, auth, user):
        add_expense(user, 77.00, "Health", "2020-01-25", "newlyadded-jan25")
        _, page = get_profile(auth, "?start=2020-01-01&end=2020-01-31")
        assert "newlyadded-jan25" in page
        assert "107.00" in page  # 10 + 20 + 77
