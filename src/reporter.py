"""
reporter.py — Generates markdown PR summary and HTML report artifact
Privacy mode ON by default: real values never appear in output.
"""

from processor import ProcessResult
from scorer import score_emoji


def _change_type(reason: str) -> str:
    """Extract the change type label from a reason string, never the actual value."""
    if "email normalized" in reason:
        return "email normalized to lowercase"
    if "whitespace" in reason:
        return "whitespace trimmed"
    if "nullish" in reason:
        return "normalized to null"
    if "boolean" in reason:
        return "normalized to boolean"
    if "numeric" in reason:
        return "normalized to number"
    return "value cleaned"


def generate_markdown(filename: str, result: ProcessResult, score_data: dict, privacy_mode: bool = True) -> str:
    score = score_data["score"]
    grade = score_data["grade"]
    label = score_data["label"]
    emoji = score_emoji(score)
    breakdown = score_data["breakdown"]

    lines = []

    # Header
    lines.append("## 🔍 DataForge — Data Quality Report")
    lines.append("")
    lines.append(f"**File:** `{filename}`  &nbsp;|&nbsp; **Format:** `{result.format_detected.upper()}`  &nbsp;|&nbsp; **Privacy mode:** `{'on' if privacy_mode else 'off'}`")
    lines.append("")

    # Score card
    lines.append("### Health Score")
    lines.append("")
    lines.append("| Score | Grade | Status |")
    lines.append("|-------|-------|--------|")
    lines.append(f"| **{score}/100** | **{grade}** | {emoji} {label} |")
    lines.append("")

    # Score breakdown
    lines.append("#### Score Breakdown")
    lines.append("")
    lines.append("| Dimension | Score | Max | Bar |")
    lines.append("|-----------|-------|-----|-----|")
    for dim, d in breakdown.items():
        pct = d["score"] / d["max"] if d["max"] > 0 else 0
        filled = round(pct * 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"| {d['label']} | {d['score']} | {d['max']} | `{bar}` |")
    lines.append("")

    # Summary stats
    lines.append("### Summary")
    lines.append("")
    lines.append("| Metric | Value | Note |")
    lines.append("|--------|-------|------|")
    lines.append(f"| Records in | {result.records_in} | original count |")
    lines.append(f"| Records out | **{result.records_out}** | ✅ cleaned & kept |")
    lines.append(f"| Duplicates removed | {result.dupes_removed} | intentional removal |")
    lines.append(f"| Empty rows removed | {result.empty_removed} | intentional removal |")
    lines.append(f"| Parse errors | {result.parse_errors} | {'✅ none' if result.parse_errors == 0 else '⚠️ check format'} |")
    lines.append(f"| Values cleaned | {len(result.changes)} | normalizations applied |")
    lines.append(f"| Fields | {len(result.fields)} | |")
    lines.append("")
    # Add clarity note
    total_removed = result.dupes_removed + result.empty_removed
    if result.parse_errors == 0 and total_removed > 0:
        lines.append(f"> ✅ **{result.records_in} → {result.records_out} records**: {result.dupes_removed} duplicates + {result.empty_removed} empty rows removed intentionally. No processing errors.")
    elif result.parse_errors > 0:
        lines.append(f"> ⚠️ **{result.parse_errors} rows failed to parse** — check your data format.")
    lines.append("")

    # Column completeness — stats only, no values
    if result.column_stats:
        lines.append("### Column Completeness")
        lines.append("")
        lines.append("| Column | Complete | Nulls | Unique Values |")
        lines.append("|--------|----------|-------|---------------|")
        for col, stats in result.column_stats.items():
            pct = stats["complete_pct"]
            flag = " ⚠️" if pct < 80 else ""
            lines.append(
                f"| `{col}` | {pct}%{flag} | {stats['null_count']} | {stats['unique_count']} |"
            )
        lines.append("")

    # Changes log — type only in privacy mode, never actual values
    if result.changes:
        lines.append(f"### Changes Applied ({len(result.changes)} total)")
        lines.append("")

        if privacy_mode:
            # Group by field + change type — no actual values shown
            from collections import defaultdict
            grouped = defaultdict(int)
            for c in result.changes:
                key = (c["field"], _change_type(c["reason"]))
                grouped[key] += 1

            lines.append("| Field | Change Type | Count |")
            lines.append("|-------|-------------|-------|")
            for (field, change_type), count in sorted(grouped.items()):
                lines.append(f"| `{field}` | {change_type} | {count} |")
            lines.append("")
            lines.append("> 🔒 **Privacy mode is on** — actual values are not shown in this report.")
        else:
            lines.append("| Row | Field | Change |")
            lines.append("|-----|-------|--------|")
            shown = result.changes[:20]
            for c in shown:
                lines.append(f"| {c['row']} | `{c['field']}` | {c['reason']} |")
            if len(result.changes) > 20:
                lines.append(f"| ... | ... | _+{len(result.changes) - 20} more changes_ |")
        lines.append("")
    else:
        lines.append("### ✅ No Changes Needed")
        lines.append("")
        lines.append("Data was already clean — no values needed normalization.")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("_Generated by [DataForge](https://github.com/marketplace/actions/dataforge-data-quality-check) · Your data never leaves your GitHub runner · [Security policy](https://github.com/anuragup/dataforge-action/security/policy)_")

    return "\n".join(lines)


def generate_html(filename: str, result: ProcessResult, score_data: dict, privacy_mode: bool = True) -> str:
    score = score_data["score"]
    grade = score_data["grade"]
    label = score_data["label"]
    emoji = score_emoji(score)
    breakdown = score_data["breakdown"]

    if score >= 90:
        score_color = "#10b981"
    elif score >= 75:
        score_color = "#f59e0b"
    elif score >= 60:
        score_color = "#f97316"
    else:
        score_color = "#ef4444"

    # Changes — grouped by type in privacy mode
    changes_rows = ""
    if result.changes:
        if privacy_mode:
            from collections import defaultdict
            grouped = defaultdict(int)
            for c in result.changes:
                key = (c["field"], _change_type(c["reason"]))
                grouped[key] += 1
            for (field, change_type), count in sorted(grouped.items()):
                changes_rows += f"<tr><td><code>{field}</code></td><td>{change_type}</td><td>{count}</td></tr>\n"
        else:
            for c in result.changes[:50]:
                changes_rows += f"<tr><td>{c['row']}</td><td><code>{c['field']}</code></td><td>{c['reason']}</td></tr>\n"
            if len(result.changes) > 50:
                changes_rows += f"<tr><td colspan='3' style='text-align:center;color:#6b7280'>+{len(result.changes)-50} more</td></tr>"

    # Column stats rows — each column gets its own color based on its completeness
    col_rows = ""
    for col, stats in result.column_stats.items():
        pct = stats["complete_pct"]
        warn = "⚠️" if pct < 80 else ""
        if pct >= 95:   col_color = "#10b981"  # green
        elif pct >= 80: col_color = "#f59e0b"  # yellow
        elif pct >= 60: col_color = "#f97316"  # orange
        else:           col_color = "#ef4444"  # red
        col_rows += f"""
        <tr>
            <td><code>{col}</code></td>
            <td>
                <div style="display:flex;align-items:center;gap:8px">
                    <div style="width:100px;height:6px;background:#1a1a26;border-radius:3px">
                        <div style="width:{pct}%;height:100%;background:{col_color};border-radius:3px"></div>
                    </div>
                    <span style="color:{col_color}">{pct}% {warn}</span>
                </div>
            </td>
            <td>{stats['null_count']}</td>
            <td>{stats['unique_count']}</td>
        </tr>"""

    # Breakdown bars
    breakdown_html = ""
    for dim, d in breakdown.items():
        pct = round(d["score"] / d["max"] * 100) if d["max"] > 0 else 0
        breakdown_html += f"""
        <div style="margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-size:0.8rem;color:#9ca3af">{d['label']}</span>
                <span style="font-size:0.8rem;font-weight:700;color:#e8e8f0">{d['score']}/{d['max']}</span>
            </div>
            <div style="height:6px;background:#1a1a26;border-radius:3px">
                <div style="width:{pct}%;height:100%;background:{score_color};border-radius:3px"></div>
            </div>
        </div>"""

    # Changes table headers differ by mode
    if privacy_mode:
        changes_thead = "<tr><th>Field</th><th>Change Type</th><th>Count</th></tr>"
        privacy_notice = "<div style='margin-top:12px;padding:10px 14px;background:rgba(0,245,160,0.06);border:1px solid rgba(0,245,160,0.2);border-radius:6px;font-size:0.72rem;color:#00f5a0'>🔒 Privacy mode is on — actual data values are never stored or displayed in this report.</div>"
    else:
        changes_thead = "<tr><th>Row</th><th>Field</th><th>Change</th></tr>"
        privacy_notice = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DataForge Report — {filename}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root {{--bg:#0a0a0f;--surface:#111118;--surface2:#1a1a26;--border:#2a2a3d;--text:#e8e8f0;--muted:#6b7280}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;padding:40px;min-height:100vh}}
  body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,245,160,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(0,245,160,0.02) 1px,transparent 1px);background-size:40px 40px;pointer-events:none}}
  .container{{max-width:900px;margin:0 auto;position:relative;z-index:1}}
  .logo{{font-size:1.4rem;font-weight:800;color:#00f5a0;margin-bottom:4px}}
  .subtitle{{color:var(--muted);font-family:'Space Mono',monospace;font-size:0.75rem;margin-bottom:32px}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:20px}}
  .card-title{{font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);margin-bottom:16px;font-family:'Space Mono',monospace}}
  .score-big{{font-size:4rem;font-weight:800;color:{score_color};line-height:1}}
  .stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:20px}}
  .stat{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;text-align:center}}
  .stat-val{{font-size:1.6rem;font-weight:700;color:#00f5a0;font-family:'Space Mono',monospace}}
  .stat-label{{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-top:4px}}
  table{{width:100%;border-collapse:collapse;font-family:'Space Mono',monospace;font-size:0.75rem}}
  th{{text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);color:var(--muted);font-weight:400;text-transform:uppercase;letter-spacing:0.06em;font-size:0.65rem}}
  td{{padding:8px 12px;border-bottom:1px solid rgba(42,42,61,0.5);color:var(--text)}}
  tr:last-child td{{border-bottom:none}}
  code{{background:var(--surface2);padding:2px 6px;border-radius:4px;font-size:0.8em}}
  .grade-badge{{display:inline-block;width:48px;height:48px;border-radius:8px;background:{score_color}22;border:2px solid {score_color};color:{score_color};font-size:1.4rem;font-weight:800;text-align:center;line-height:44px;margin-left:16px}}
  .footer{{text-align:center;color:var(--muted);font-family:'Space Mono',monospace;font-size:0.65rem;margin-top:32px;padding-top:20px;border-top:1px solid var(--border)}}
  a{{color:#00f5a0}}
</style>
</head>
<body>
<div class="container">
  <div class="logo">DataForge</div>
  <div class="subtitle">Data Quality Report &nbsp;·&nbsp; {filename} &nbsp;·&nbsp; 🔒 Privacy mode {'on' if privacy_mode else 'off'}</div>

  <div class="card">
    <div class="card-title">Health Score</div>
    <div style="display:flex;align-items:flex-end;gap:0">
      <div class="score-big">{score}</div>
      <div style="font-size:2rem;font-weight:800;color:var(--muted);margin-bottom:8px">/100</div>
      <div class="grade-badge">{grade}</div>
    </div>
    <div style="font-size:1rem;color:var(--muted);margin-top:4px">{emoji} {label}</div>
    <div style="margin-top:24px">{breakdown_html}</div>
  </div>

  <div class="stat-grid">
    <div class="stat"><div class="stat-val">{result.records_in}</div><div class="stat-label">Records In</div></div>
    <div class="stat"><div class="stat-val" style="color:#00f5a0">{result.records_out}</div><div class="stat-label">Records Out ✅</div></div>
    <div class="stat"><div class="stat-val" style="color:#f59e0b">{result.dupes_removed}</div><div class="stat-label">Dupes Removed</div></div>
    <div class="stat"><div class="stat-val" style="color:#f59e0b">{result.empty_removed}</div><div class="stat-label">Empty Removed</div></div>
    <div class="stat"><div class="stat-val">{len(result.changes)}</div><div class="stat-label">Values Cleaned</div></div>
    <div class="stat"><div class="stat-val">{result.format_detected.upper()}</div><div class="stat-label">Format</div></div>
  </div>

  <div style="background:#111118;border:1px solid #2a2a3d;border-radius:8px;padding:14px 18px;margin-bottom:20px;font-family:'Space Mono',monospace;font-size:0.72rem">
    <span style="color:#6b7280">RECORD BREAKDOWN &nbsp;·&nbsp;</span>
    <span style="color:#e8e8f0">{result.records_in} in</span>
    <span style="color:#6b7280"> = </span>
    <span style="color:#00f5a0">{result.records_out} kept</span>
    <span style="color:#6b7280"> + </span>
    <span style="color:#f59e0b">{result.dupes_removed} dupes</span>
    <span style="color:#6b7280"> + </span>
    <span style="color:#f59e0b">{result.empty_removed} empty</span>
    <span style="color:#6b7280"> + </span>
    <span style="color:#{"ef4444" if result.parse_errors > 0 else "6b7280"}">{result.parse_errors} errors</span>
    {"&nbsp;&nbsp;<span style='color:#10b981'>✓ All removals intentional — nothing failed to process</span>" if result.parse_errors == 0 else "&nbsp;&nbsp;<span style='color:#ef4444'>⚠ Some rows failed to parse — check your data format</span>"}
  </div>

  <div class="card">
    <div class="card-title">Column Completeness</div>
    <table>
      <thead><tr><th>Column</th><th>Completeness</th><th>Nulls</th><th>Unique Values</th></tr></thead>
      <tbody>{col_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">Changes Applied ({len(result.changes)})</div>
    {"<p style='color:#10b981;font-size:0.85rem'>✅ Data was already clean — no changes needed.</p>" if not result.changes else f"<table><thead>{changes_thead}</thead><tbody>{changes_rows}</tbody></table>{privacy_notice}"}
  </div>

  <div class="footer">
    Generated by <strong>DataForge</strong> · Your data never leaves your GitHub runner · Zero telemetry<br>
    <a href="https://github.com/marketplace/actions/dataforge-data-quality-check">github.com/marketplace/actions/dataforge-data-quality-check
</a>
  </div>
</div>
</body>
</html>"""
