import pytest
from flask import url_for
import library_service

# Mark all tests in this module as expected to fail until R5 is implemented
pytestmark = pytest.mark.xfail(strict=True, reason="R5 not implemented yet")

@pytest.fixture(scope="session")
def app():
    try:
        from app import create_app
        _app = create_app(testing=True)
    except Exception:
        from app import app as _app
        _app.config.update(TESTING=True)
    return _app

@pytest.fixture()
def client(app):
    return app.test_client()

def _late_fee_route_exists(app):
    return any(str(r.rule).startswith("/api/late_fee/") for r in app.url_map.iter_rules())

@pytest.mark.skipif(True, reason="Unskip once /api/late_fee/<patron>/<book> is registered")
def test_dummy_skip_marker():
    assert True

def test_late_fee_api_happy_path_returns_json(client, app, monkeypatch):
    if not _late_fee_route_exists(app):
        pytest.skip("late fee endpoint not registered yet")

    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda pid, bid: {"fee_amount": 4.50, "days_overdue": 8, "status": "ok"})

    resp = client.get("/api/late_fee/123456/1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["fee_amount"] == 4.50
    assert data["days_overdue"] == 8
