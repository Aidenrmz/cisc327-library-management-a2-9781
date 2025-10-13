import pytest
from contextlib import contextmanager
from typing import List, Dict

from flask import template_rendered

# --- App fixture: supports both application factory and a plain app object ---

@pytest.fixture(scope="session")
def app():
    """
    Load the Flask app for testing.
    Tries `create_app()` first (application factory pattern), and falls back to `app.app`.
    """
    try:
        from app import create_app  # application factory pattern (preferred)
        _app = create_app(testing=True)
    except Exception:
        from app import app as _app  # fallback if the repo exposes a global app
        # Put the app into testing mode if not already
        _app.config.update(TESTING=True)
    return _app


@pytest.fixture()
def client(app):
    return app.test_client()


# --- Utility: capture which template was rendered and with what context ---

@contextmanager
def captured_templates(app):
    """
    Context manager to capture (template, context) pairs during a request.
    """
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


# --- Helpers for mock book rows ---

def make_book(
    id: int,
    title: str = "Title",
    author: str = "Author",
    isbn: str = "1234567890123",
    total: int = 3,
    available: int = 2,
) -> Dict:
    return {
        "id": id,
        "title": title,
        "author": author,
        "isbn": isbn,
        "total_copies": total,
        "available_copies": available,
    }


# =========================================
#                TESTS
# =========================================

def test_catalog_renders_success_and_uses_catalog_template(app, client, monkeypatch):
    """
    R2: Route should render /catalog successfully and use the catalog template,
    passing the books list from get_all_books().
    """
    from routes import catalog_routes

    sample_books: List[Dict] = [
        make_book(1, "Clean Code", "Robert C. Martin", "9780132350884", total=5, available=5),
        make_book(2, "The Pragmatic Programmer", "Andrew Hunt", "9780201616224", total=2, available=1),
    ]

    # Patch the symbol used inside the route module
    monkeypatch.setattr(catalog_routes, "get_all_books", lambda: sample_books)

    with captured_templates(app) as templates:
        resp = client.get("/catalog")
        assert resp.status_code == 200

    # Exactly one template render expected
    assert len(templates) == 1
    template, context = templates[0]

    # Template name should be catalog.html (as per route)
    assert template.name == "catalog.html"

    # Context should include the same books list (identity or equality)
    assert "books" in context
    assert context["books"] == sample_books
    # sanity check a field
    assert context["books"][0]["title"] == "Clean Code"


def test_catalog_handles_empty_list(app, client, monkeypatch):
    """
    R2: When there are no books, the route should still render and pass an empty list.
    """
    from routes import catalog_routes
    monkeypatch.setattr(catalog_routes, "get_all_books", lambda: [])

    with captured_templates(app) as templates:
        resp = client.get("/catalog")
        assert resp.status_code == 200

    assert len(templates) == 1
    _, context = templates[0]
    assert "books" in context
    assert context["books"] == []  # empty catalog is acceptable


def test_catalog_availability_boundaries_reflected_in_context(app, client, monkeypatch):
    """
    R2: The route should surface availability correctly so the template can decide
    whether to show a Borrow action (spec requirement).
    """
    from routes import catalog_routes

    sample_books = [
        make_book(1, "Available Book", "Auth A", "1111111111111", total=1, available=1),
        make_book(2, "Unavailable Book", "Auth B", "2222222222222", total=1, available=0),
    ]
    monkeypatch.setattr(catalog_routes, "get_all_books", lambda: sample_books)

    with captured_templates(app) as templates:
        resp = client.get("/catalog")
        assert resp.status_code == 200

    assert len(templates) == 1
    _, context = templates[0]
    books = context["books"]
    assert books[0]["available_copies"] == 1
    assert books[1]["available_copies"] == 0


def test_catalog_response_includes_titles_authors_isbns(app, client, monkeypatch):
    """
    R2: Basic smoke test that rendered HTML includes key fields
    (we're not snapshot-testing the whole template).
    """
    from routes import catalog_routes

    sample_books = [
        make_book(10, "Dune", "Frank Herbert", "9780441013593", total=4, available=3),
        make_book(11, "1984", "George Orwell", "9780451524935", total=2, available=0),
    ]
    monkeypatch.setattr(catalog_routes, "get_all_books", lambda: sample_books)

    resp = client.get("/catalog")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    # Titles & authors should appear in the table
    assert "Dune" in html
    assert "Frank Herbert" in html
    assert "1984" in html
    assert "George Orwell" in html
    # ISBNs usually appear as text; if your template hides them, remove these asserts
    assert "9780441013593" in html
    assert "9780451524935" in html


def test_catalog_scales_with_many_books(app, client, monkeypatch):
    """
    R2: Route should render fine with a larger catalog (basic scalability smoke test).
    """
    from routes import catalog_routes

    big_list = [make_book(i, f"Title {i}", f"Author {i}", f"{i:013d}", total=5, available=(i % 3))
                for i in range(1, 201)]  # 200 books

    monkeypatch.setattr(catalog_routes, "get_all_books", lambda: big_list)

    with captured_templates(app) as templates:
        resp = client.get("/catalog")
        assert resp.status_code == 200

    assert len(templates) == 1
    _, context = templates[0]
    assert "books" in context
    assert len(context["books"]) == 200
