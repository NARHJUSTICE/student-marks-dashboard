"""
All statistics and grading logic for the dashboard.
Updated to support multiple subjects per student.
"""

from collections import Counter, defaultdict


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


GRADE_ORDER = [
    "A (90-100)", "B (80-89)", "C (70-79)", "D (60-69)", "F (Below 60)",
]
STATUS_ORDER = ["Excellent", "Good", "Average", "At Risk"]


def _safe_mode(values):
    cleaned = [v for v in values if v not in (None, "", "Not stated")]
    if not cleaned:
        return "Not stated"
    return Counter(cleaned).most_common(1)[0][0]


def _empty_summary() -> dict:
    return {
        "total_students": 0, "avg_marks": 0.0, "top_student": "N/A", "top_score": 0.0,
        "best_subject": "N/A", "best_subject_score": 0.0, "weakest_subject": "N/A", "weakest_subject_score": 0.0,
        "subject_summary": [], "status_counts": [], "grade_distribution": [], "career_distribution": [],
        "class_summary": [], "semester_summary": [], "attendance_summary": [],
        "avg_study_hours": 0.0, "most_common_period": "Not stated", "most_common_interest": "Not stated",
        "rows": [],
    }


def summarize(students: list[dict]) -> dict:
    if not students:
        return _empty_summary()

    # 1. Calculate each student's TRUE average across all their subjects
    all_student_averages = []
    for s in students:
        subs = s.get("subjects", [])
        if subs:
            avg = sum(sub["marks"] for sub in subs) / len(subs)
        else:
            avg = 0.0
        s["average_marks"] = avg
        all_student_averages.append(avg)

    total = len(students)
    overall_avg = sum(all_student_averages) / total if total else 0.0

    # Top student based on their true average
    top = max(students, key=lambda s: s["average_marks"])

    # 2. Subject averages (across ALL students)
    subject_buckets = defaultdict(list)
    for s in students:
        for sub in s.get("subjects", []):
            subject_buckets[sub["subject"]].append(sub["marks"])
    
    subject_avg = {k: sum(v) / len(v) for k, v in subject_buckets.items()}
    sorted_subjects = sorted(subject_avg.items(), key=lambda kv: kv[1], reverse=True)
    best_subject, best_subject_score = sorted_subjects[0] if sorted_subjects else ("N/A", 0)
    weakest_subject, weakest_subject_score = sorted_subjects[-1] if sorted_subjects else ("N/A", 0)

    # 3. Status counts based on true averages
    raw_status = Counter(get_status(s["average_marks"]) for s in students)
    status_counts = [{"status": st, "count": raw_status[st]} for st in STATUS_ORDER if raw_status[st] > 0]

    # 4. Grade distribution based on true averages
    raw_grades = Counter(get_grade(s["average_marks"]) for s in students)
    grade_distribution = [{"grade": g, "count": raw_grades[g]} for g in GRADE_ORDER if raw_grades[g] > 0]

    # 5. Class comparison based on true averages
    class_buckets = defaultdict(list)
    for s in students:
        cls = (s.get("class_name") or "UNKNOWN").upper()
        class_buckets[cls].append(s["average_marks"])
    class_summary = sorted(
        [{"class_name": k, "avg": round(sum(v)/len(v), 2), "count": len(v)} for k, v in class_buckets.items()],
        key=lambda d: d["avg"], reverse=True
    )

    # 6. Semester performance based on true averages
    sem_data = defaultdict(lambda: defaultdict(int))
    for s in students:
        sem = (s.get("semester") or "Unknown").strip()
        if sem:
            g = get_grade(s["average_marks"])
            sem_data[sem][g] += 1
    semester_summary = []
    for sem, grades in sorted(sem_data.items()):
        semester_summary.append({
            "semester": sem,
            "grades": [{"grade": g, "count": grades.get(g, 0)} for g in GRADE_ORDER]
        })

    # 7. Attendance summary
    att_totals = defaultdict(int)
    for s in students:
        status = (s.get("attendance_status") or "Not Recorded").strip()
        days = int(s.get("attendance_days") or 1)
        att_totals[status] += days
    total_att_days = sum(att_totals.values()) or 1
    attendance_summary = [
        {"status": k, "count": v, "percent": round((v / total_att_days) * 100)}
        for k, v in att_totals.items()
    ]

    # 8. Career distribution
    career_counter = Counter((s.get("future_career_plan") or "Not stated").strip() or "Not stated" for s in students)
    career_distribution = [{"career": k, "count": v} for k, v in career_counter.most_common(5)]

    # 9. Other stats
    study_hours = [float(s["study_hours_per_day"]) for s in students if s.get("study_hours_per_day") not in (None, "")]
    avg_study_hours = sum(study_hours) / len(study_hours) if study_hours else 0.0
    most_common_period = _safe_mode([s.get("study_period") for s in students])
    most_common_interest = _safe_mode([s.get("student_interest") for s in students])

    # 10. Rows for the table (attach true average, status, and grade)
    rows = []
    for s in students[:12]:
        rows.append({
            **s,
            "status": get_status(s["average_marks"]),
            "grade": get_grade(s["average_marks"]),
        })

    return {
        "total_students": total,
        "avg_marks": round(overall_avg, 2),
        "top_student": top["student_name"],
        "top_score": round(top["average_marks"], 2),
        "best_subject": best_subject,
        "best_subject_score": round(best_subject_score, 2),
        "weakest_subject": weakest_subject,
        "weakest_subject_score": round(weakest_subject_score, 2),
        "subject_summary": [{"subject": k, "avg": round(v, 2)} for k, v in sorted_subjects],
        "status_counts": status_counts,
        "grade_distribution": grade_distribution,
        "career_distribution": career_distribution,
        "class_summary": class_summary,
        "semester_summary": semester_summary,
        "attendance_summary": attendance_summary,
        "avg_study_hours": round(avg_study_hours, 2),
        "most_common_period": most_common_period,
        "most_common_interest": most_common_interest,
        "rows": rows,
    }