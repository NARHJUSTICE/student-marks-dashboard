"""
All statistics and grading logic for the dashboard.

Pure functions on a list of student dicts (keys matching the SQLite schema),
so this module has no dependency on Flask or the database — easy to reason
about and easy to test.
"""

from collections import Counter


def get_status(marks: float) -> str:
    if marks >= 85:
        return "Excellent"
    if marks >= 70:
        return "Good"
    if marks >= 50:
        return "Average"
    return "At Risk"


def get_grade(marks: float) -> str:
    if marks >= 90:
        return "A (90-100)"
    if marks >= 80:
        return "B (80-89)"
    if marks >= 70:
        return "C (70-79)"
    if marks >= 60:
        return "D (60-69)"
    return "F (Below 60)"


# Canonical ordering for display — highest grade first
GRADE_ORDER = [
    "A (90-100)",
    "B (80-89)",
    "C (70-79)",
    "D (60-69)",
    "F (Below 60)",
]

# Canonical ordering for status display
STATUS_ORDER = ["Excellent", "Good", "Average", "At Risk"]


def _safe_mode(values):
    """Most common non-empty value, or 'Not stated'."""
    cleaned = [v for v in values if v not in (None, "", "Not stated")]
    if not cleaned:
        return "Not stated"
    return Counter(cleaned).most_common(1)[0][0]


def _empty_summary() -> dict:
    """Return the summary shape for zero students (keeps the template simple)."""
    return {
        "total_students": 0,
        "avg_marks": 0.0,
        "top_student": "N/A",
        "top_score": 0.0,
        "best_subject": "N/A",
        "best_subject_score": 0.0,
        "weakest_subject": "N/A",
        "weakest_subject_score": 0.0,
        "subject_summary": [],
        "status_counts": [],
        "grade_distribution": [],
        "career_distribution": [],
        "class_summary": [],
        "avg_study_hours": 0.0,
        "most_common_period": "Not stated",
        "most_common_interest": "Not stated",
        "rows": [],
    }


def summarize(students: list[dict]) -> dict:
    """
    Given a list of student dicts, return everything the dashboard needs.
    Handles the empty case gracefully.
    """
    if not students:
        return _empty_summary()

    marks = [float(s["marks"]) for s in students]
    total = len(students)
    avg_marks = sum(marks) / total

    # Top student
    top = max(students, key=lambda s: float(s["marks"]))

    # ---- Subject averages ----
    subject_buckets: dict[str, list[float]] = {}
    for s in students:
        subj = (s.get("subject") or "UNKNOWN").upper()
        subject_buckets.setdefault(subj, []).append(float(s["marks"]))
    subject_avg = {k: sum(v) / len(v) for k, v in subject_buckets.items()}
    sorted_subjects = sorted(subject_avg.items(), key=lambda kv: kv[1], reverse=True)
    best_subject, best_subject_score = sorted_subjects[0]
    weakest_subject, weakest_subject_score = sorted_subjects[-1]

    # ---- Status counts (as ordered list of dicts) ----
    raw_status: dict[str, int] = {}
    for s in students:
        st = get_status(float(s["marks"]))
        raw_status[st] = raw_status.get(st, 0) + 1
    status_counts = [
        {"status": st, "count": raw_status.get(st, 0)}
        for st in STATUS_ORDER
        if raw_status.get(st, 0) > 0
    ]

    # ---- Grade distribution (as ordered list of dicts) ----
    raw_grades: dict[str, int] = {}
    for s in students:
        g = get_grade(float(s["marks"]))
        raw_grades[g] = raw_grades.get(g, 0) + 1
    grade_distribution = [
        {"grade": g, "count": raw_grades.get(g, 0)}
        for g in GRADE_ORDER
        if raw_grades.get(g, 0) > 0
    ]

    # ---- Career distribution (top 5) ----
    career_counter = Counter(
        (s.get("future_career_plan") or "Not stated").strip() or "Not stated"
        for s in students
    )
    career_distribution = [
        {"career": k, "count": v} for k, v in career_counter.most_common(5)
    ]

    # ---- Class comparison ----
    class_buckets: dict[str, list[float]] = {}
    for s in students:
        cls = (s.get("class_name") or "UNKNOWN").upper()
        class_buckets.setdefault(cls, []).append(float(s["marks"]))
    class_summary = sorted(
        [
            {
                "class_name": k,
                "avg": round(sum(v) / len(v), 2),
                "count": len(v),
            }
            for k, v in class_buckets.items()
        ],
        key=lambda d: d["avg"],
        reverse=True,
    )

    # ---- Study hours ----
    study_hours = [
        float(s["study_hours_per_day"])
        for s in students
        if s.get("study_hours_per_day") not in (None, "")
    ]
    avg_study_hours = sum(study_hours) / len(study_hours) if study_hours else 0.0

    most_common_period = _safe_mode([s.get("study_period") for s in students])
    most_common_interest = _safe_mode([s.get("student_interest") for s in students])

    # ---- Rows for the table (attach status + grade) ----
    rows = []
    for s in students[:12]:
        rows.append({
            **s,
            "status": get_status(float(s["marks"])),
            "grade": get_grade(float(s["marks"])),
        })

    return {
        "total_students": total,
        "avg_marks": round(avg_marks, 2),
        "top_student": top["student_name"],
        "top_score": round(float(top["marks"]), 2),
        "best_subject": best_subject,
        "best_subject_score": round(best_subject_score, 2),
        "weakest_subject": weakest_subject,
        "weakest_subject_score": round(weakest_subject_score, 2),
        "subject_summary": [
            {"subject": k, "avg": round(v, 2)} for k, v in sorted_subjects
        ],
        "status_counts": status_counts,
        "grade_distribution": grade_distribution,
        "career_distribution": career_distribution,
        "class_summary": class_summary,
        "avg_study_hours": round(avg_study_hours, 2),
        "most_common_period": most_common_period,
        "most_common_interest": most_common_interest,
        "rows": rows,
    }