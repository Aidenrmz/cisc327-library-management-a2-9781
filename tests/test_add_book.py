import pytest
from services.library_service import add_book_to_catalog

def test_add_book_valid_nominal():
    """13-digit, digits-only ISBN; typical title/author; copies > 0"""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
    
    assert success == True
    assert "successfully added" in message.lower()

def test_add_book_valid_boundary_lengths():
    """title exactly 200 chars, author exactly 100 chars; valid ISBN; copies > 0"""
    success, message = add_book_to_catalog("The Library System: Thorough Testing, Robust Validation, and Clean Architecture—A Student’s Guide to Building Reliable Features with Flask, SQLite, and Blueprints (R1–R7) — exact-length title demo v10", "Alexandria K. Montgomery–Santos, PhD, MSc, BEng, QA Lead and Researcher in Software Reliability (QA)", "1234567890123", 5)
    
    assert success == True
    assert "successfully added" in message.lower()

def test_add_book_invalid_isbn_wrong_length():
    """ISBN wrong length (12 digits)"""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789012", 5)
    
    assert success == False
    assert "13 digits" in message

def test_add_book_invalid_total_copies_nonpositive():
    """Total copies <= 0"""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 0)

    assert success == False
    assert "positive integer" in message.lower()

def test_add_book_duplicate_isbn():
    """Duplicate ISBN"""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)

    assert success == False 
    assert "already exists" in message.lower()