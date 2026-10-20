"""
Flask entry point for the Student Marks Dashboard.

Routes:
    GET  /              -> dashboard (all students + stats)
    POST /add           -> validate & insert one student, redirect back
    GET  /edit/<id>     -> show edit form for one student
    POST /update/<id>   -> save edits, redirect to dashboard
    POST /delete/<id>   -> delete one student, redirect back
    POST /reset         -> wipe all students, redirect back
    GET  /export        -> download all students as CSV
    GET  /healthz       -> simple health check for Render
"""

import csv
import io
import os

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, Response, abort
)

import db
import analysis

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Ensure the DB and table exist on startup
db.init_db()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _opt(form, key):
    """Read an optional form field: return trimmed string or None."""
    v = (form.get(key) or "").strip()
    return v or None


def validate_student(form) -> tuple[dict, list[str]]:
    """Return (cleaned_data, errors). cleaned_data is safe to insert/update."""
    errors: list[str] = []

    # ---- Required fields ----
    student_id = (form.get("student_id") or "").strip()
    student_name = (form.get("student_name") or "").strip()
    class_name = (form.get("class_name") or "").strip().upper()
    subject = (form.get("subject") or "").strip().upper()
    age = _to_int(form.get("age"))
    marks = _to_float(form.get("marks"))

    if not student_id:
        errors.append("Student ID is required.")
    if not student_name:
        errors.append("Student name is required.")
    if not class_name:
        errors.append("Class is required.")
    if not subject:
        errors.append("Subject is required.")
    if age is None or not (5 <= age <= 25):
        errors.append("Age must be a number between 5 and 25.")
    if marks is None or not (0 <= marks <= 100):
        errors.append("Marks must be a number between 0 and 100.")

    # ---- Optional fields ----
    gender = (form.get("gender") or "").strip() or None
    religion = _opt(form, "religion")
    favourite_subject = _opt(form, "favourite_subject")
    favourite_sports = _opt(form, "favourite_sports")
    favourite_teacher = _opt(form, "favourite_teacher")
    study_period = _opt(form, "study_period")
    career = _opt(form, "future_career_plan")

    cleaned = {
        "student_id": student_id,
        "student_name": student_name,
        "age": age,
        "gender": gender,
        "religion": religion,
        "country": None,
        "state": None,
        "height_cm": None,
        "class_name": class_name,
        "subject": subject,
        "marks": marks,
        "student_interest": None,
        "favourite_subject": favourite_subject,
        "favourite_sports": favourite_sports,
        "favourite_teacher": favourite_teacher,
        "future_career_plan": career,
        "study_hours_per_day": None,
        "study_hours_per_subject": None,
        "study_period": study_period,
        "lifestyle": None,
    }
    return cleaned, errors


# ------------------------------------------------------------------
# Routes — dashboard
# ------------------------------------------------------------------

@app.route("/")
def index():
    students = db.get_all_students()
    summary = analysis.summarize(students)
    return render_template("dashboard.html", summary=summary)


@app.route("/add", methods=["POST"])
def add_student():
    cleaned, errors = validate_student(request.form)
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("index"))

    try:
        db.insert_student(cleaned)
        flash(f"Added {cleaned['student_name']}.", "success")
    except Exception as e:
        flash(f"Could not save student: {e}", "error")

    return redirect(url_for("index"))


# ------------------------------------------------------------------
# Routes — edit / update
# ------------------------------------------------------------------

@app.route("/edit/<int:student_pk>")
def edit_student(student_pk):
    student = db.get_student(student_pk)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("index"))
    return render_template("edit.html", student=student)


@app.route("/update/<int:student_pk>", methods=["POST"])
def update_student(student_pk):
    if not db.get_student(student_pk):
        flash("Student not found.", "error")
        return redirect(url_for("index"))

    cleaned, errors = validate_student(request.form)
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("edit_student", student_pk=student_pk))

    try:
        db.update_student(student_pk, cleaned)
        flash(f"Updated {cleaned['student_name']}.", "success")
    except Exception as e:
        flash(f"Could not update student: {e}", "error")

    return redirect(url_for("index"))


# ------------------------------------------------------------------
# Routes — delete / reset
# ------------------------------------------------------------------

@app.route("/delete/<int:student_pk>", methods=["POST"])
def delete_student_route(student_pk):
    student = db.get_student(student_pk)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("index"))

    try:
        db.delete_student(student_pk)
        flash(f"Deleted {student['student_name']}.", "success")
    except Exception as e:
        flash(f"Could not delete student: {e}", "error")

    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset_route():
    try:
        removed = db.delete_all_students()
        flash(f"Reset complete. Removed {removed} student(s).", "success")
    except Exception as e:
        flash(f"Could not reset data: {e}", "error")
    return redirect(url_for("index"))


# ------------------------------------------------------------------
# Routes — export / health
# ------------------------------------------------------------------

@app.route("/export")
def export_csv():
    students = db.get_all_students()
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "student_id", "student_name", "age", "gender", "class_name",
        "subject", "marks", "future_career_plan", "created_at",
    ]
    writer.writerow(headers)
    for s in students:
        writer.writerow([s.get(h, "") for h in headers])

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"},
    )


@app.route("/healthz")
def healthz():
    return {"status": "ok", "students": db.count_students()}


if __name__ == "__main__":
    # Local dev only — Render will run this via gunicorn
    app.run(host="0.0.0.0", port=5001, debug=True)