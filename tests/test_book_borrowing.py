import re
import pytest
from datetime import datetime, timedelta

import library_service 
from library_service import borrow_book_by_patron  

def fake_book(available=1, total=3, title="Test Title", book_id=1):
    """
    Create a fake book object for testing.
    """
    return {
        "id": book_id,
        "title": title,
        "author": "Someone",
        "isbn": "1234567890123",
        "total_copies": total,
        "available_copies": available,
    }

def test_borrow_available_copies_and_borrow_limit_allows_when_patron_has_4(monkeypatch):
    """
    patron has 4 borrowed (under limit), book is available.
    should create a borrow record, decrement availability, and return success.
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 4)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: fake_book(available=1, book_id=book_id))
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    success, message= borrow_book_by_patron("123456", 1)

    assert success == True
    assert "Successfully borrowed" in message

@pytest.mark.xfail(strict=True, reason="Spec: max 5; implementation pending")
def test_borrow_rejects_when_patron_has_5_already__per_spec(monkeypatch):
    """
    patron has 5 borrowed (at limit), book is available.
    should return failure, no borrow record created.
    known bug: uses '> 5' instead of '>= 5'
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 5)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: fake_book(available=1, book_id=book_id))
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success == False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_fails_when_no_available_copies(monkeypatch):
    """
    book has no available copies. 
    should return failure, no borrow record created.
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 3)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: fake_book(available=0, book_id=book_id))
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success == False
    assert "not available" in message.lower()

def test_borrow_fails_for_invalid_patron_id(monkeypatch):
    """
    invalid patron ID (not 6 digits).
    should return failure, no borrow record created.
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 3)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: fake_book(available=1, book_id=book_id))
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    # too short
    success, message = borrow_book_by_patron("12345", 1)
    assert success == False
    assert "exactly 6 digits" in message.lower()

    # non-digit
    success, message = borrow_book_by_patron("12345a", 1)
    assert success == False
    assert "exactly 6 digits" in message.lower()

    # too long
    success, message = borrow_book_by_patron("1234567", 1)
    assert success == False
    assert "exactly 6 digits" in message.lower()

def test_borrow_fails_when_book_not_found(monkeypatch):
    """
    book not found.
    should return failure, no borrow record created.
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 3)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: None)
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success == False
    assert "not found" in message.lower()

def test_borrow_fails_when_database_error_creating_borrow_record(monkeypatch):
    """
    database error creating borrow record.
    should return failure, no borrow record created.
    """
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda patron_id: 3)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda book_id: fake_book(available=1, book_id=book_id))
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: False)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)       
    assert success == False
    assert "database error creating borrow record" in message.lower()