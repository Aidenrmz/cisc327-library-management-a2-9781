import os
import sqlite3
import pytest

DB_PATH = 'library.db'

def _reset_db():
    """Drop and recreate the schema for a clean state per test."""
    if os.path.exists(DB_PATH):
        # Use sqlite3 to drop and recreate tables
        conn = sqlite3.connect(DB_PATH)
    else:
        conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS borrow_records')
    cur.execute('DROP TABLE IF EXISTS books')

    cur.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            total_copies INTEGER NOT NULL,
            available_copies INTEGER NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patron_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    ''')
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True, scope='function')
def reset_db_per_test(request):
    """Ensure each test starts with a clean database. Optionally seed duplicates for specific tests."""
    _reset_db()

    # Conditional seed for duplicate ISBN test
    node_name = getattr(request.node, 'name', '') or ''
    if 'test_add_book_duplicate_isbn' in node_name:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO books (title, author, isbn, total_copies, available_copies) VALUES (?, ?, ?, ?, ?)',
            ('Seeded Book', 'Seed Author', '1234567890123', 5, 5)
        )
        conn.commit()
        conn.close()
    yield

