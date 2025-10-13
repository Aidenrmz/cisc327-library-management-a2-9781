import pytest
import library_service  
from library_service import search_books_in_catalog

def book(id, title, author, isbn, total=3, available=2):
    return {
        "id": id,
        "title": title,
        "author": author,
        "isbn": isbn,
        "total_copies": total,
        "available_copies": available,
    }

# Mark all tests in this module as expected to fail until R6 is implemented
pytestmark = pytest.mark.xfail(strict=True, reason="R6 not implemented yet")

def test_search_title_partial_case_insensitive(monkeypatch):
    sample = [
        book(1, "The Great Gatsby", "F. Scott Fitzgerald", "9780743273565"),
        book(2, "GREAT Expectations", "Charles Dickens", "9780141439563"),
        book(3, "Clean Code", "Robert C. Martin", "9780132350884"),
    ]
    monkeypatch.setattr(library_service, "get_all_books", lambda: sample)

    # 'great' should match 1 & 2 regardless of case; not 3.
    results = search_books_in_catalog("great", "title")
    titles = {r["title"] for r in results}
    assert "The Great Gatsby" in titles
    assert "GREAT Expectations" in titles
    assert "Clean Code" not in titles

def test_search_author_partial_case_insensitive(monkeypatch):
    sample = [
        book(1, "Book A", "Harper Lee", "9780061120084"),
        book(2, "Book B", "Lee Child", "9780440243694"),
        book(3, "Book C", "George Orwell", "9780451524935"),
    ]
    monkeypatch.setattr(library_service, "get_all_books", lambda: sample)

    results = search_books_in_catalog("lEe", "author")
    authors = {r["author"] for r in results}
    assert "Harper Lee" in authors
    assert "Lee Child" in authors
    assert "George Orwell" not in authors

def test_search_isbn_exact_match_only(monkeypatch):
    exact = "9780451524935"
    target = book(3, "1984", "George Orwell", exact)
    monkeypatch.setattr(library_service, "get_book_by_isbn", lambda q: target if q == exact else None)

    # exact match.
    results = search_books_in_catalog(exact, "isbn")
    assert len(results) == 1 and results[0]["isbn"] == exact

    # partial match.
    results = search_books_in_catalog(exact[:6], "isbn")
    assert results == []

def test_search_invalid_type_raises_value_error(monkeypatch):
    with pytest.raises(ValueError):
        search_books_in_catalog("anything", "publisher")

def test_search_empty_query_returns_empty_list(monkeypatch):
    # Spec doesn't define empty q; simplest is: return [] (no implicit "list all").
    monkeypatch.setattr(library_service, "get_all_books", lambda: [book(1, "A", "B", "9780000000001")])
    assert search_books_in_catalog("", "title") == []
