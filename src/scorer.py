"""
scorer.py — Computes a 0-100 data health score from a ProcessResult
"""

from processor import ProcessResult


def compute_score(result: ProcessResult) -> dict:
    if result.records_in == 0:
        return {"score": 0, "grade": "F", "label": "No data", "breakdown": {}}

    total = result.records_in

    # ── Completeness (30 pts) ─────────────────────────────────────────────────
    # Average % of non-null values across all columns
    if result.column_stats and result.fields:
        avg_complete = sum(
            s["complete_pct"] for s in result.column_stats.values()
        ) / len(result.column_stats)
        completeness_score = round(avg_complete * 0.30)
    else:
        completeness_score = 30

    # ── Uniqueness (25 pts) ───────────────────────────────────────────────────
    # Graceful curve — small number of dupes should not zero the score
    # 0% dupes = 25, 10% dupes = 20, 25% dupes = 12, 50%+ dupes = 0
    dupe_pct = (result.dupes_removed / total * 100) if total > 0 else 0
    if dupe_pct == 0:
        uniqueness_score = 25
    elif dupe_pct <= 5:
        uniqueness_score = 22
    elif dupe_pct <= 10:
        uniqueness_score = 18
    elif dupe_pct <= 25:
        uniqueness_score = 12
    elif dupe_pct <= 50:
        uniqueness_score = 6
    else:
        uniqueness_score = 0

    # ── Consistency (25 pts) ──────────────────────────────────────────────────
    # Graceful curve — a few cleanups should not zero the score
    # changes per record: 0=25, 0.5=20, 1=15, 2=8, 3+=0
    changes_per_record = len(result.changes) / total if total > 0 else 0
    if changes_per_record == 0:
        consistency_score = 25
    elif changes_per_record <= 0.5:
        consistency_score = 20
    elif changes_per_record <= 1:
        consistency_score = 15
    elif changes_per_record <= 2:
        consistency_score = 8
    elif changes_per_record <= 3:
        consistency_score = 3
    else:
        consistency_score = 0

    # ── Validity (20 pts) ─────────────────────────────────────────────────────
    # % of records that survived cleaning (empty rows removed)
    survival_pct = (result.records_out / total * 100) if total > 0 else 0
    validity_score = round(survival_pct * 0.20)

    score = completeness_score + uniqueness_score + consistency_score + validity_score
    score = max(0, min(100, score))

    if score >= 90:
        grade, label = "A", "Excellent"
    elif score >= 75:
        grade, label = "B", "Good"
    elif score >= 60:
        grade, label = "C", "Fair"
    elif score >= 40:
        grade, label = "D", "Poor"
    else:
        grade, label = "F", "Critical"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "breakdown": {
            "completeness": {"score": completeness_score, "max": 30, "label": "Completeness"},
            "uniqueness":   {"score": uniqueness_score,   "max": 25, "label": "Uniqueness"},
            "consistency":  {"score": consistency_score,  "max": 25, "label": "Consistency"},
            "validity":     {"score": validity_score,     "max": 20, "label": "Validity"},
        }
    }


def score_emoji(score: int) -> str:
    if score >= 90: return "🟢"
    if score >= 75: return "🟡"
    if score >= 60: return "🟠"
    if score >= 40: return "🟠"
    return "🔴"
