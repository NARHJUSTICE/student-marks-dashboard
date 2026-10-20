"""
SQLite storage layer for the student marks dashboard.

The database path is controlled by the DATABASE_PATH environment variable
so that Render can point it at a persistent disk (e.g. /var/data/students.db).
Locally it defaults to ./students.db inside this folder.
"""

import os
import sqlite3
from contextlib import contextmanager

# Where the database file lives
DB_PATH = os.environ.get("DATABASE_PATH", "students.db")

# Single source of truth for column names (used by insert + update)
STUDENT_COLUMNS = [
    "student_id", "student_name", "age", "gender", "religion", "country",
    "state", "height_cm", "class_name", "subject", "marks",
    "student_interest", "favourite_subject", "favourite_sports",
    "favourite_teacher", "future_career_plan", "study_hours_per_day",
    "study_hours_per_subject", "study_period", "lifestyle",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    student_name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    religion TEXT,
    country TEXT,
    state TEXT,
    height_cm REAL,
    class_name TEXT,
    subject TEXT,
    marks REAL NOT NULL,
    student_interest TEXT,
    favourite_subject TEXT,
    favourite_sports TEXT,
    favourite_teacher TEXT,
    future_career_plan TEXT,
    study_hours_per_day REAL,
    study_hours_per_subject REAL,
    study_period TEXT,
    lifestyle TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def get_conn():
    """Open a SQLite connection, commit on success, always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the students table if it doesn't exist yet."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------

def insert_student(data: dict):
    """Insert one student. Keys of `data` must match STUDENT_COLUMNS."""
    values = [data.get(col) for col in STUDENT_COLUMNS]
    placeholders = ",".join(["?"] * len(STUDENT_COLUMNS))
    sql = (
        f"INSERT INTO students ({','.join(STUDENT_COLUMNS)}) "
        f"VALUES ({placeholders})"
    )
    with get_conn() as conn:
        conn.execute(sql, values)


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------

def get_all_students():
    """Return all students, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_student(student_pk: int):
    """Return a single student by primary key, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_pk,)
        ).fetchone()
    return dict(row) if row else None


def count_students() -> int:
    """Return how many students are stored."""
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

def update_student(student_pk: int, data: dict) -> bool:
    """Update fields on one student. Returns True if a row was updated."""
    assignments = ", ".join(f"{c} = ?" for c in STUDENT_COLUMNS)
    values = [data.get(c) for c in STUDENT_COLUMNS] + [student_pk]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE students SET {assignments} WHERE id = ?", values
        )
        return cur.rowcount > 0


# ------------------------------------------------------------------
# Delete
# ------------------------------------------------------------------

def delete_student(student_pk: int) -> bool:
    """Delete one student. Returns True if a row was deleted."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_pk,))
        return cur.rowcount > 0


def delete_all_students() -> int:
    """Wipe the table. Returns how many rows were removed."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM students")
        return cur.rowcount