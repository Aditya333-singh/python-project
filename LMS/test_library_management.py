import sqlite3
import tempfile
import unittest
from pathlib import Path

from library_management import LibraryManagementSystem


class LibraryManagementSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.library = LibraryManagementSystem(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.library.close()
        self.temp_dir.cleanup()

    def test_books_can_be_searched_and_available_copies_are_reported(self) -> None:
        self.library.add_book("Dune", "Frank Herbert", "9780441013593", 2)
        self.library.add_book("Foundation", "Isaac Asimov", "9780553293357")

        results = self.library.list_books("frank")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Dune")
        self.assertEqual(results[0]["available"], 2)

    def test_checkout_updates_availability_and_return_restores_it(self) -> None:
        book_id = self.library.add_book("Dune", "Frank Herbert", "9780441013593")
        member_id = self.library.add_member("Ada Lovelace", "ada@example.com")

        loan_id = self.library.borrow_book(book_id, member_id)
        self.assertEqual(self.library.list_books()[0]["available"], 0)
        self.assertEqual(len(self.library.list_loans(include_returned=False)), 1)

        self.library.return_book(loan_id)
        self.assertEqual(self.library.list_books()[0]["available"], 1)
        self.assertEqual(len(self.library.list_loans(include_returned=False)), 0)

    def test_checkout_rejects_unavailable_copies(self) -> None:
        book_id = self.library.add_book("Dune", "Frank Herbert", "9780441013593")
        first_member = self.library.add_member("Ada Lovelace", "ada@example.com")
        second_member = self.library.add_member("Grace Hopper", "grace@example.com")
        self.library.borrow_book(book_id, first_member)

        with self.assertRaisesRegex(ValueError, "No copies"):
            self.library.borrow_book(book_id, second_member)

    def test_duplicate_isbn_and_invalid_copy_count_are_rejected(self) -> None:
        self.library.add_book("Dune", "Frank Herbert", "9780441013593")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
            self.library.add_book("Another book", "Another author", "9780441013593")
        with self.assertRaisesRegex(ValueError, "positive whole number"):
            self.library.add_book("Valid title", "Valid author", "123", 0)

    def test_returning_a_loan_twice_is_rejected(self) -> None:
        book_id = self.library.add_book("Dune", "Frank Herbert", "9780441013593")
        member_id = self.library.add_member("Ada Lovelace", "ada@example.com")
        loan_id = self.library.borrow_book(book_id, member_id)
        self.library.return_book(loan_id)

        with self.assertRaisesRegex(ValueError, "Active loan not found"):
            self.library.return_book(loan_id)


if __name__ == "__main__":
    unittest.main()
