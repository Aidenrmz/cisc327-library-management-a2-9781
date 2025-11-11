import pytest
from flask import template_rendered
from contextlib import contextmanager
import services.library_service as library_service 
from services.library_service import search_books_in_catalog

# Mark all tests in this module as expected to fail until R6 is implemented
pytestmark = pytest.mark.xfail(strict=True, reason="R6 not implemented yet")


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

@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

# ---------- Tests ----------

def test_search_with_query_title_calls_service_and_renders_results(app, client, monkeypatch):
    """
    Arrange: make the service return two matches
    """
    results = [
        {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "9780743273565",
         "total_copies": 3, "available_copies": 2},
        {"id": 2, "title": "GREAT Expectations", "author": "Charles Dickens", "isbn": "9780141439563",
         "total_copies": 2, "available_copies": 1},
    ]
    calls = {}
    def fake_search(term, typ):
        calls["term"] = term
        calls["type"] = typ
        return results
    monkeypatch.setattr(library_service, "search_books_in_catalog", fake_search)

    with captured_templates(app) as templates:
        resp = client.get("/search?q=great&type=title")
        assert resp.status_code == 200

    assert len(templates) == 1
    template, ctx = templates[0]
    assert template.name == "search.html"
    assert calls["term"] == "great"
    assert calls["type"] == "title"
    assert ctx["books"] == results
    assert ctx["search_term"] == "great"
    assert ctx["search_type"] == "title"

def test_search_with_empty_query_returns_empty_list_and_renders(app, client):
    """
    No q param -> route should render with empty results
    """
    with captured_templates(app) as templates:
        resp = client.get("/search?type=author")
        assert resp.status_code == 200

    assert len(templates) == 1
    _, ctx = templates[0]
    assert ctx["books"] == []
    assert ctx["search_term"] == ""
    assert ctx["search_type"] == "author"

@pytest.mark.xfail(strict=True, reason="Current route flashes 'not implemented' on empty results; prefer 'no results' UX.")
def test_search_no_matches_should_not_be_treated_as_not_implemented(app, client, monkeypatch):
    """
    Business logic returns [], which can be a legitimate 'no results'
    """
    monkeypatch.setattr(library_service, "search_books_in_catalog", lambda q, t: [])

    resp = client.get("/search?q=zzzz&type=title")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Search functionality is not yet implemented." not in html
