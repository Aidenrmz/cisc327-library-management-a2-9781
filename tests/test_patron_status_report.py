import pytest
from datetime import datetime, timedelta

import services.library_service as library_service  
from services.library_service import get_patron_status_report

# Mark the whole module as expected-failing until R7 is implemented



def borrowed_item(book_id, title, days_overdue=0):
    """Make a borrowed-book dict shaped like database.get_patron_borrowed_books returns."""
    now = datetime.now()
    due = now - timedelta(days=max(days_overdue, 0))
    borrow = now - timedelta(days=14 + max(days_overdue, 0))
    return {
        "book_id": book_id,
        "title": title,
        "author": "Any",
        "borrow_date": borrow,
        "due_date": due,
        "is_overdue": days_overdue > 0,
    }


def test_status_happy_path_two_current_borrows_and_fees(monkeypatch):
    """
    R7: report includes current borrows (with due dates), total late fees (sum), and count.
    One overdue (8 days => $4.50), one not overdue (0 => $0.00). Total should be $4.50.
    """
    current = [
        borrowed_item(1, "Clean Code", days_overdue=8),
        borrowed_item(2, "Dune", days_overdue=0),
    ]
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: current)
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda pid: 2)

    def fee_for(patron_id, book_id):
        return {"fee_amount": 4.50, "days_overdue": 8, "status": "ok"} if book_id == 1 else \
               {"fee_amount": 0.00, "days_overdue": 0, "status": "ok"}
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book", fee_for)

    report = get_patron_status_report("123456")
    assert isinstance(report, dict)
    assert set(["current_borrows", "total_late_fees", "current_borrow_count", "history"]).issubset(report.keys())

    assert len(report["current_borrows"]) == 2
    titles = {b["title"] for b in report["current_borrows"]}
    assert "Clean Code" in titles and "Dune" in titles
    assert all("due_date" in b for b in report["current_borrows"])

    assert report["current_borrow_count"] == 2
    assert round(float(report["total_late_fees"]), 2) == 4.50  # monetary value rounded to 2 decimals


def test_status_no_current_borrows_zero_fees_and_empty_history(monkeypatch):
    """
    R7: empty borrowed list => count=0, total late fees=0.00, history exists (may be empty).
    """
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda pid: 0)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda pid, bid: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"})

    report = get_patron_status_report("123456")
    assert report["current_borrow_count"] == 0
    assert float(report["total_late_fees"]) == 0.0
    assert "history" in report and isinstance(report["history"], list)


def test_status_includes_overdue_flag_from_current_loans(monkeypatch):
    """
    R7: Each current-borrow entry should preserve/compute an overdue indicator (useful for UI).
    """
    current = [
        borrowed_item(1, "X", days_overdue=1),
        borrowed_item(2, "Y", days_overdue=0),
    ]
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: current)
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda pid: 2)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda pid, bid: {"fee_amount": 0.5 if bid == 1 else 0.0, "days_overdue": 1 if bid == 1 else 0, "status": "ok"})

    report = get_patron_status_report("123456")
    flags = [b.get("is_overdue") for b in report["current_borrows"]]
    assert flags == [True, False]


def test_status_validates_patron_id_format(monkeypatch):
    """
    R7 should honor the global constraint: patron ID must be exactly 6 digits.
    Implementation may raise or return an error status; accept either.
    """
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda pid: 0)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda pid, bid: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"})

    try:
        report = get_patron_status_report("12345")  # invalid
        assert isinstance(report, dict) and report.get("status") not in (None, "ok")
    except ValueError:
        assert True


def test_status_history_key_is_present_and_list_type(monkeypatch):
    """
    R7 requires a borrowing history in the report. If you later add a DB helper like
    get_patron_borrow_history, wire it here. For now we only assert existence & type.
    """
    monkeypatch.setattr(library_service, "get_patron_borrowed_books", lambda pid: [])
    monkeypatch.setattr(library_service, "get_patron_borrow_count", lambda pid: 0)
    monkeypatch.setattr(library_service, "calculate_late_fee_for_book",
                        lambda pid, bid: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"})

    report = get_patron_status_report("123456")
    assert "history" in report and isinstance(report["history"], list)
