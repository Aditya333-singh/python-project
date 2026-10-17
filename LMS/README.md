# Python Library Management System

A simple terminal-based library manager. It stores books, members, and checkout
records in a local SQLite database, so records remain available between runs.
It uses only the Python standard library.

## Run

```powershell
python library_management.py
```

The default database file is `library.db` in the current directory. Choose a
different file with `--database`, for example:

```powershell
python library_management.py --database data/library.db
```

Use the menu to add and search books, register members, check books out and
back in, and review loan records. ISBNs and member email addresses must be
unique. A book cannot be checked out when all of its copies are on loan.

## Tests

Run the standard-library test suite with:

```powershell
python -m unittest -v
```
