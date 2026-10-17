"""A small, persistent library management system backed by SQLite."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any


class LibraryManagementSystem:
    """Manage books, members, and loans in a local SQLite database."""

    def __init__(self, database_path: str | Path = "library.db") -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_database()

    def _initialize_database(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT NOT NULL UNIQUE,
                    copies INTEGER NOT NULL CHECK (copies > 0)
                );
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL REFERENCES books(id),
                    member_id INTEGER NOT NULL REFERENCES members(id),
                    borrowed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    returned_at TEXT
                );
                """
            )

    @staticmethod
    def _required_text(value: str, field: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{field} is required.")
        return value

    def add_book(
        self, title: str, author: str, isbn: str, copies: int = 1
    ) -> int:
        title = self._required_text(title, "Title")
        author = self._required_text(author, "Author")
        isbn = self._required_text(isbn, "ISBN")
        if isinstance(copies, bool) or not isinstance(copies, int) or copies < 1:
            raise ValueError("Copies must be a positive whole number.")
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO books (title, author, isbn, copies) VALUES (?, ?, ?, ?)",
                (title, author, isbn, copies),
            )
        return int(cursor.lastrowid)

    def list_books(self, search: str = "") -> list[dict[str, Any]]:
        query = """
            SELECT b.id, b.title, b.author, b.isbn, b.copies,
                   b.copies - COUNT(l.id) AS available
            FROM books AS b
            LEFT JOIN loans AS l
                ON l.book_id = b.id AND l.returned_at IS NULL
        """
        parameters: tuple[str, ...] = ()
        if search.strip():
            query += " WHERE b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?"
            term = f"%{search.strip()}%"
            parameters = (term, term, term)
        query += " GROUP BY b.id ORDER BY b.title, b.author"
        return [dict(row) for row in self.connection.execute(query, parameters)]

    def add_member(self, name: str, email: str) -> int:
        name = self._required_text(name, "Name")
        email = self._required_text(email, "Email")
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO members (name, email) VALUES (?, ?)", (name, email)
            )
        return int(cursor.lastrowid)

    def list_members(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT id, name, email FROM members ORDER BY name, email"
        )
        return [dict(row) for row in rows]

    def borrow_book(self, book_id: int, member_id: int) -> int:
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            book = self.connection.execute(
                "SELECT copies FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if book is None:
                raise ValueError("Book not found.")
            member = self.connection.execute(
                "SELECT id FROM members WHERE id = ?", (member_id,)
            ).fetchone()
            if member is None:
                raise ValueError("Member not found.")
            active_loans = self.connection.execute(
                "SELECT COUNT(*) FROM loans WHERE book_id = ? AND returned_at IS NULL",
                (book_id,),
            ).fetchone()[0]
            if active_loans >= book["copies"]:
                raise ValueError("No copies of this book are currently available.")
            cursor = self.connection.execute(
                "INSERT INTO loans (book_id, member_id) VALUES (?, ?)",
                (book_id, member_id),
            )
        return int(cursor.lastrowid)

    def return_book(self, loan_id: int) -> None:
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE loans SET returned_at = CURRENT_TIMESTAMP
                WHERE id = ? AND returned_at IS NULL
                """,
                (loan_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError("Active loan not found.")

    def list_loans(self, include_returned: bool = True) -> list[dict[str, Any]]:
        query = """
            SELECT l.id, b.title AS book_title, m.name AS member_name,
                   l.borrowed_at, l.returned_at
            FROM loans AS l
            JOIN books AS b ON b.id = l.book_id
            JOIN members AS m ON m.id = l.member_id
        """
        if not include_returned:
            query += " WHERE l.returned_at IS NULL"
        query += " ORDER BY l.borrowed_at DESC, l.id DESC"
        return [dict(row) for row in self.connection.execute(query)]

    def close(self) -> None:
        self.connection.close()


def _print_records(records: list[dict[str, Any]]) -> None:
    if not records:
        print("No records found.")
        return
    for record in records:
        print(" | ".join(f"{key}: {value}" for key, value in record.items()))


def run_cli(database_path: str | Path = "library.db") -> None:
    library = LibraryManagementSystem(database_path)
    actions = {
        "1": "Add book",
        "2": "List/search books",
        "3": "Register member",
        "4": "List members",
        "5": "Borrow book",
        "6": "Return book",
        "7": "List loans",
        "0": "Exit",
    }
    try:
        while True:
            print("\nLibrary Management System")
            for key, action in actions.items():
                print(f"{key}. {action}")
            choice = input("Choose an option: ").strip()
            try:
                if choice == "1":
                    title = input("Title: ")
                    author = input("Author: ")
                    isbn = input("ISBN: ")
                    copies = int(input("Number of copies: "))
                    book_id = library.add_book(title, author, isbn, copies)
                    print(f"Book added (ID {book_id}).")
                elif choice == "2":
                    _print_records(library.list_books(input("Search (blank for all): ")))
                elif choice == "3":
                    name = input("Member name: ")
                    email = input("Member email: ")
                    member_id = library.add_member(name, email)
                    print(f"Member registered (ID {member_id}).")
                elif choice == "4":
                    _print_records(library.list_members())
                elif choice == "5":
                    book_id = int(input("Book ID: "))
                    member_id = int(input("Member ID: "))
                    loan_id = library.borrow_book(book_id, member_id)
                    print(f"Book checked out (loan ID {loan_id}).")
                elif choice == "6":
                    loan_id = int(input("Loan ID: "))
                    library.return_book(loan_id)
                    print("Book returned.")
                elif choice == "7":
                    _print_records(library.list_loans())
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Choose one of the listed options.")
            except ValueError as error:
                print(f"Could not complete that action: {error}")
            except sqlite3.IntegrityError as error:
                print(f"Could not save the record: {error}")
    finally:
        library.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage a small library.")
    parser.add_argument(
        "--database",
        default="library.db",
        help="SQLite database file (default: library.db)",
    )
    args = parser.parse_args()
    run_cli(args.database)


if __name__ == "__main__":
    main()
