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
# Note: We removed 'subject' and 'marks' from here because they now live in the new table.
STUDENT_COLUMNS = [
    "student_id", "student_name", "age", "gender", "religion", "country",
    "state", "height_cm", "class_name", 
    "student_interest", "favourite_subject", "favourite_sports",
    "favourite_teacher", "future_career_plan", "study_hours_per_day",
    "study_hours_per_subject", "study_period", "lifestyle",
    "semester", "attendance_status", "attendance_days"
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
    student_interest TEXT,
    favourite_subject TEXT,
    favourite_sports TEXT,
    favourite_teacher TEXT,
    future_career_plan TEXT,
    study_hours_per_day REAL,
    study_hours_per_subject REAL,
    study_period TEXT,
    lifestyle TEXT,
    semester TEXT,
    attendance_status TEXT,
    attendance_days INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    subject TEXT,
    marks REAL,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
);
"""


@contextmanager
def get_conn():
    """Open a SQLite connection, commit on success, always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys so ON DELETE CASCADE works
    conn.execute("PRAGMA foreign_keys = ON;")
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

def insert_student(data: dict, subjects: list[dict]):
    """Insert one student, then insert their subjects."""
    values = [data.get(col) for col in STUDENT_COLUMNS]
    placeholders = ",".join(["?"] * len(STUDENT_COLUMNS))
    sql = (
        f"INSERT INTO students ({','.join(STUDENT_COLUMNS)}) "
        f"VALUES ({placeholders})"
    )
    with get_conn() as conn:
        cur = conn.execute(sql, values)
        new_student_id = cur.lastrowid
        
        # Insert subjects
        for subj in subjects:
            conn.execute(
                "INSERT INTO student_subjects (student_id, subject, marks) VALUES (?, ?, ?)",
                (new_student_id, subj['subject'], subj['marks'])
            )


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------

def get_all_students():
    """Return all students with their subjects, newest first."""
    with get_conn() as conn:
        # Get students
        rows = conn.execute(
            "SELECT * FROM students ORDER BY created_at DESC, id DESC"
        ).fetchall()
        
        students = []
        for r in rows:
            student = dict(r)
            # Get subjects for this student
            subs = conn.execute(
                "SELECT subject, marks FROM student_subjects WHERE student_id = ?", 
                (student['id'],)
            ).fetchall()
            
            # If no subjects, provide a default empty list
            student['subjects'] = [dict(s) for s in subs]
            
            # For backward compatibility with the analysis engine, 
            # we attach the first subject/mark to the main dict
            if student['subjects']:
                student['subject'] = student['subjects'][0]['subject']
                student['marks'] = student['subjects'][0]['marks']
            else:
                student['subject'] = "N/A"
                student['marks'] = 0
                
            students.append(student)
            
    return students


def get_student(student_pk: int):
    """Return a single student by primary key with subjects, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_pk,)
        ).fetchone()
        
        if not row:
            return None
            
        student = dict(row)
        subs = conn.execute(
            "SELECT subject, marks FROM student_subjects WHERE student_id = ?", 
            (student_pk,)
        ).fetchall()
        student['subjects'] = [dict(s) for s in subs]
        
        return student


def count_students() -> int:
    """Return how many students are stored."""
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

def update_student(student_pk: int, data: dict, subjects: list[dict]) -> bool:
    """Update fields on one student, and replace their subjects."""
    assignments = ", ".join(f"{c} = ?" for c in STUDENT_COLUMNS)
    values = [data.get(c) for c in STUDENT_COLUMNS] + [student_pk]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE students SET {assignments} WHERE id = ?", values
        )
        
        # Delete old subjects and insert new ones
        conn.execute("DELETE FROM student_subjects WHERE student_id = ?", (student_pk,))
        for subj in subjects:
            conn.execute(
                "INSERT INTO student_subjects (student_id, subject, marks) VALUES (?, ?, ?)",
                (student_pk, subj['subject'], subj['marks'])
            )
            
        return cur.rowcount > 0


# ------------------------------------------------------------------
# Delete
# ------------------------------------------------------------------

def delete_student(student_pk: int) -> bool:
    """Delete one student. (Their subjects are deleted automatically due to CASCADE)."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_pk,))
        return cur.rowcount > 0


def delete_all_students() -> int:
    """Wipe the tables. Returns how many students were removed."""
    with get_conn() as conn:
        # Due to CASCADE, deleting from students will delete subjects
        cur = conn.execute("DELETE FROM students")
        return cur.rowcount