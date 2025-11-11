import pytest
from datetime import datetime, timedelta

import services.library_service as library_service  
from services.library_service import calculate_late_fee_for_book

# Mark all tests in this module as expected to fail until R5 is implemented



def with_active_loan(days_overdue: int):
    """
    Return a fake borrowed item whose due_date produces the desired overdue days.
    """
    now = datetime.now()
    return [{
        "book_id": 1,
        "title": "Any",
        "author": "X",
        "borrow_date": now - timedelta(days=14 + max(days_overdue, 0)),
        "due_date": now - timedelta(days=max(days_overdue, 0)),
        "is_overdue": days_overdue > 0,
    }]

@pytest.mark.parametrize("days_overdue, expected_fee", [
    (0, 0.00),      # on/before due date
    (1, 0.50),      # first tier
    (7, 3.50),      # 0.5 * 7
    (8, 4.50),      # 3.5 + 1.0
    (20, 15.00),    # capped
])
def test_fee_tiers_and_cap(monkeypatch, days_overdue, expected_fee):
    monkeypatch.setattr(library_service, "get_patron_borrowed_books",
                        lambda patron_id: with_active_loan(days_overdue))

    result = calculate_late_fee_for_book("123456", 1)
    assert result["days_overdue"] == days_overdue
    assert round(result["fee_amount"], 2) == expected_fee
    assert result["status"] == "ok"

def test_negative_overdue_is_clamped_to_zero(monkeypatch):
    """If due_date is in the future, overdue should be zero and fee = 0."""
    now = datetime.now()
    future_due = now + timedelta(days=3)
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [{
        "book_id": 1,
        "title": "F",
        "author": "A",
        "borrow_date": now - timedelta(days=1),
        "due_date": future_due,
        "is_overdue": False,
    }])

    result = calculate_late_fee_for_book("123456", 1)
    assert result["days_overdue"] == 0
    assert result["fee_amount"] == 0.0

def test_no_active_loan_returns_zero_fee(monkeypatch):
    """If patron does not currently have that book checked out, fee is 0."""
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    result = calculate_late_fee_for_book("123456", 1)
    assert result["days_overdue"] == 0
    assert result["fee_amount"] == 0.0
    assert result["status"] in {"no_active_loan", "ok"}

def test_validates_patron_id_format(monkeypatch):
    """Follow the global constraint: library card must be exactly 6 digits."""
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    result = calculate_late_fee_for_book("12345", 1)  # invalid
    assert "status" in result and result["status"] != "ok"
