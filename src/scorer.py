"""
scorer.py — Computes a 0-100 data health score from a ProcessResult
"""

from processor import ProcessResult


def compute_score(result: ProcessResult) -> dict:
    """
    Returns a score dict:
    {
        "score": int,          # 0-100
        "grade": str,          # A/B/C/D/F
        "label": str,          # human label
        "breakdown": dict      # per-dimension scores
    }
    """
    if result.records_in == 0:
        return {"score": 0, "grade": "F", "label": "No data", "breakdown": {}}

    total = result.records_in

    # ── Dimension 1: Completeness (30 pts) ──────────────────────────────────
    # How many values are non-null across all fields
    if result.column_stats and result.fields:
        avg_complete = sum(
            s["complete_pct"] for s in result.column_stats.values()
        ) / len(result.column_stats)
        completeness_score = round(avg_complete * 0.30)
    else:
        completeness_score = 30

    # ── Dimension 2: Uniqueness (25 pts) ────────────────────────────────────
    # Penalize for duplicates
    dupe_pct = result.dupes_removed / total * 100 if total > 0 else 0
    uniqueness_score = round(max(0, 25 - (dupe_pct * 2.5)))

    # ── Dimension 3: Consistency (25 pts) ────────────────────────────────────
    # Penalize for number of changes needed (more changes = dirtier data)
    changes_per_record = len(result.changes) / total if total > 0 else 0
    # 0 changes = 25pts, 2+ changes per record = 0pts
    consistency_score = round(max(0, 25 - (changes_per_record * 12.5)))

    # ── Dimension 4: Validity (20 pts) ──────────────────────────────────────
    # Based on how many records survived cleaning vs came in
    survival_pct = result.records_out / total * 100 if total > 0 else 0
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
            "uniqueness": {"score": uniqueness_score, "max": 25, "label": "Uniqueness"},
            "consistency": {"score": consistency_score, "max": 25, "label": "Consistency"},
            "validity": {"score": validity_score, "max": 20, "label": "Validity"},
        }
    }


def score_emoji(score: int) -> str:
    if score >= 90:
        return "🟢"
    if score >= 75:
        return "🟡"
    if score >= 60:
        return "🟠"
    return "🔴"
