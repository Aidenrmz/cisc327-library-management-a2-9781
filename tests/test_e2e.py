import threading
import time
import contextlib
from urllib.request import urlopen

import pytest
from werkzeug.serving import make_server
from playwright.sync_api import expect

# Reuse the existing app factory from the repo
from app import create_app


def _wait_for_server(url: str, timeout_seconds: int = 20) -> None:
    """Poll the given URL until it responds or timeout occurs."""
    deadline = time.time() + timeout_seconds
    last_err = None
    while time.time() < deadline:
        try:
            with contextlib.closing(urlopen(url, timeout=2)):  # follows redirects
                return
        except Exception as e:
            last_err = e
            time.sleep(0.25)
    raise RuntimeError(f"Server did not start at {url} in time. Last error: {last_err}")


@pytest.fixture(scope="session")
def server_url():
    """
    Start the Flask app on 127.0.0.1:5001 for the test session, wait until it's ready,
    yield the base URL, then shut it down cleanly.
    """
    host = "127.0.0.1"
    port = 5001
    base_url = f"http://{host}:{port}"

    app = create_app(testing=True)

    # Create a threaded Werkzeug server
    http_server = make_server(host, port, app)
    server_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    server_thread.start()

    # Wait for readiness
    _wait_for_server(base_url + "/")

    yield base_url

    # Teardown: stop server and join thread
    http_server.shutdown()
    server_thread.join(timeout=5)


"""
E2E flows covered in this file:
- Flow 1: Add a new book and verify it appears in the catalog listing.
- Flow 2: Borrow that book and verify a success confirmation and availability decrement.

Base URL used for tests: http://127.0.0.1:5001 (provided by server_url fixture).
"""


def _unique_isbn() -> str:
    # Create a deterministic 13-digit ISBN based on current time
    millis = int(time.time() * 1000)
    # Ensure 13 digits by taking trailing 10 digits and prefixing with '978'
    return "978" + str(millis)[-10:]


def _go_to_add_book(page, base_url: str) -> None:
    page.goto(base_url + "/")
    # Use robust selector by href to avoid emoji/name variations
    page.locator('a[href="/add_book"]').first.click()
    expect(page).to_have_url(base_url + "/add_book")
    expect(page.get_by_text("Add New Book")).to_be_visible()


def _submit_add_book_form(page, title: str, author: str, isbn: str, copies: int, base_url: str) -> None:
    page.get_by_label("Title *").fill(title)
    page.get_by_label("Author *").fill(author)
    page.get_by_label("ISBN *").fill(isbn)
    page.get_by_label("Total Copies *").fill(str(copies))
    page.get_by_role("button", name="Add Book to Catalog").click()
    # After successful add, we redirect to /catalog with a success flash
    expect(page).to_have_url(base_url + "/catalog")
    expect(page.locator(".flash-success")).to_contain_text("successfully added")
    expect(page.locator(".flash-success")).to_contain_text(title)


def _assert_book_listed_in_catalog(page, base_url: str, title: str) -> None:
    page.goto(base_url + "/catalog")
    row = page.locator("tbody tr").filter(has_text=title).first
    expect(row).to_be_visible()


def _borrow_book_from_row(page, base_url: str, title: str, patron_id: str, expected_availability_substring: str = "") -> None:
    page.goto(base_url + "/catalog")
    row = page.locator("tbody tr").filter(has_text=title).first
    expect(row).to_be_visible()
    # Fill the inline borrow form in the row and submit
    row.locator('input[name="patron_id"]').fill(patron_id)
    row.get_by_role("button", name="Borrow").click()
    # Redirect back to catalog with a success flash
    expect(page).to_have_url(base_url + "/catalog")
    expect(page.locator(".flash-success")).to_contain_text("Successfully borrowed")
    expect(page.locator(".flash-success")).to_contain_text(title)
    # Re-acquire the row and optionally assert availability text changed
    row_after = page.locator("tbody tr").filter(has_text=title).first
    expect(row_after).to_be_visible()
    if expected_availability_substring:
        expect(row_after).to_contain_text(expected_availability_substring)


def test_add_book_and_list(page, server_url):
    base_url = server_url
    title = f"E2E Test Book {int(time.time())}"
    author = "E2E Author"
    isbn = _unique_isbn()
    copies = 2

    _go_to_add_book(page, base_url)
    _submit_add_book_form(page, title, author, isbn, copies, base_url)
    _assert_book_listed_in_catalog(page, base_url, title)


def test_borrow_book_flow(page, server_url):
    base_url = server_url
    # Add a fresh book to ensure independence
    title = f"E2E Borrowable Book {int(time.time())}"
    author = "E2E Borrow Author"
    isbn = _unique_isbn()
    copies = 2  # start with 2 to verify decrement to 1/2

    _go_to_add_book(page, base_url)
    _submit_add_book_form(page, title, author, isbn, copies, base_url)
    _assert_book_listed_in_catalog(page, base_url, title)

    # Borrow with a valid 6-digit patron ID
    _borrow_book_from_row(page, base_url, title, patron_id="123456", expected_availability_substring="1/2 Available")

