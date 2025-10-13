import re
import pytest
from datetime import datetime, timedelta

# Mark all tests in this module as expected to fail until R4 is implemented
pytestmark = pytest.mark.xfail(strict=True, reason="R4 not implemented yet")

import library_service  
from library_service import return_book_by_patron



def fake_book(book_id=1, title="Any Title", available=0, total=1):
    return {
        "id": book_id,
        "title": title,
        "author": "X",
        "isbn": "1234567890123",
        "total_copies": total,
        "available_copies": available,
    }


def test_return_success_updates_return_date_increments_availability_and_reports_fee(monkeypatch):
    """
    patron has the book checked out
    should return success, update return date, increment availability, and calculate/display late fees.
    """

    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: borrowed)
    borrowed = [
        {
            "book_id": 1,
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "borrow_date": datetime.now() - timedelta(days=20),
            "due_date": datetime.now() - timedelta(days=6),  # overdue
            "is_overdue": True,
        }
    ]
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: borrowed)

    monkeypatch.setattr(library_service, "get_book_by_id", lambda bid: fake_book(book_id=bid, title="Clean Code", available=0, total=1))

    monkeypatch.setattr(library_service, "update_borrow_record_return_date", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)

    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda patron_id, book_id: {"fee_amount": 4.50, "days_overdue": 8, "status": "ok"})

    success, msg = return_book_by_patron("123456", 1)
    assert success is True
    assert "Returned" in msg or "success" in msg.lower()
    assert "Clean Code" in msg
    assert "4.5" in msg or "4.50" in msg
    assert "8" in msg  # days overdue appears


def test_return_fails_if_patron_does_not_have_this_book(monkeypatch):
    """
    patron does not have the book checked out
    should return failure, no return date updated.
    """

    borrowed = [{"book_id": 2, "title": "Other", "author": "A",
                 "borrow_date": datetime.now(), "due_date": datetime.now() + timedelta(days=10), "is_overdue": False}]
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: borrowed)

    monkeypatch.setattr(library_service, "get_book_by_id", lambda bid: fake_book(book_id=bid, title="Clean Code", available=0, total=1))

    success, msg = return_book_by_patron("123456", 1)
    assert success is False
    assert "not borrowed" in msg.lower() or "no active" in msg.lower()


def test_return_fails_if_book_not_found(monkeypatch):
    """
    book not found
    should return failure, no return date updated.
    """
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    monkeypatch.setattr(library_service, "get_book_by_id", lambda bid: None)

    success, msg = return_book_by_patron("123456", 999)
    assert success is False
    assert "book not found" in msg.lower()


def test_return_propagates_db_errors(monkeypatch):
    """
    database error updating return date or availability
    should return failure, no return date updated.
    """

    borrowed = [{"book_id": 1, "title": "Clean Code", "author": "A",
                 "borrow_date": datetime.now(), "due_date": datetime.now() - timedelta(days=1), "is_overdue": True}]
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: borrowed)
    monkeypatch.setattr(library_service, "get_book_by_id", lambda bid: fake_book(book_id=bid, title="Clean Code", available=0, total=1))

    monkeypatch.setattr(library_service, "update_borrow_record_return_date", lambda *args, **kwargs: False)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book", lambda *args, **kwargs: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"})

    success, msg = return_book_by_patron("123456", 1)
    assert success is False
    assert "return date" in msg.lower() or "updating" in msg.lower()

    monkeypatch.setattr(library_service, "update_borrow_record_return_date", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: False)

    success, msg = return_book_by_patron("123456", 1)
    assert success is False
    assert "availability" in msg.lower()


def test_return_validates_patron_id_format(monkeypatch):
    """
    invalid patron ID (not 6 digits).
    should return failure, no return date updated.
    """
    \
    monkeypatch.setattr(library_service, "get_book_by_id", lambda bid: fake_book(book_id=bid))
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    monkeypatch.setattr(library_service, "update_borrow_record_return_date", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book", lambda *args, **kwargs: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"})

    ok, msg = return_book_by_patron("12345", 1)
    assert ok is False
    assert "6 digits" in msg
