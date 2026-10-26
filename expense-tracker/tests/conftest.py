import os
import sys

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import database.db as db_module  # noqa: E402

# Point the DB at a throwaway file BEFORE app is imported, because importing
# app runs init_db()/seed_db() at module level.
import tempfile  # noqa: E402

_import_tmp = tempfile.mkdtemp(prefix="spendly_import_")
db_module.DB_PATH = os.path.join(_import_tmp, "import.db")

import app as app_module  # noqa: E402


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    """Flask app bound to a fresh, empty, temporary SQLite database."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    db_module.init_db()
    yield app_module.app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
