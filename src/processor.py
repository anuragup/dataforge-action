"""
processor.py — Core data cleaning engine for DataForge
Handles: CSV, TSV, JSON, Key=Value, Log files
"""

import csv
import json
import io
import re
from dataclasses import dataclass, field
from typing import Any

NULLISH = {"null", "none", "n/a", "na", "nil", "undefined", "", "—", "-", "nan"}

@dataclass
class ProcessResult:
    records_in: int = 0
    records_out: int = 0
    dupes_removed: int = 0
    empty_removed: int = 0   # rows where all fields were null/empty
    parse_errors: int = 0    # rows that failed to parse
    fields: list = field(default_factory=list)
    records: list = field(default_factory=list)
    changes: list = field(default_factory=list)
    format_detected: str = "unknown"
    column_stats: dict = field(default_factory=dict)


# ── Format Detection ──────────────────────────────────────────────────────────

def detect_format(raw: str) -> str:
    t = raw.strip()
    if not t:
        return "text"
    if (t.startswith("{") or t.startswith("[")) and (t.endswith("}") or t.endswith("]")):
        try:
            json.loads(t)
            return "json"
        except Exception:
            pass
    if re.search(r"^\[\d{4}-\d{2}-\d{2}.*?\]\s+(INFO|ERROR|WARN|DEBUG)", t, re.MULTILINE):
        return "logfile"
    lines = [l for l in t.split("\n") if l.strip()]
    if len(lines) > 1:
        tab_lines = sum(1 for l in lines if "\t" in l)
        if tab_lines > len(lines) * 0.5:
            return "tsv"
        comma_lines = sum(1 for l in lines if "," in l)
        if comma_lines > len(lines) * 0.6:
            return "csv"
    first_line = lines[0] if lines else ""
    if re.match(r"^[\w\-\.]+\s*=\s*.+", t, re.MULTILINE) and "," not in first_line:
        return "kv"
    return "text"


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_csv(raw: str, sep: str = ",") -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(raw.strip()), delimiter=sep)
    fields = reader.fieldnames or []
    records = [dict(row) for row in reader]
    return records, list(fields)


def parse_json(raw: str) -> tuple[list[dict], list[str]]:
    data = json.loads(raw)
    if isinstance(data, list):
        fields = list(data[0].keys()) if data else []
        return data, fields
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and v:
                fields = list(v[0].keys()) if isinstance(v[0], dict) else ["value"]
                records = v if isinstance(v[0], dict) else [{"value": i} for i in v]
                return records, fields
        return [data], list(data.keys())
    return [{"value": data}], ["value"]


def parse_kv(raw: str) -> tuple[list[dict], list[str]]:
    record = {}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if "=" in line:
            k, _, v = line.partition("=")
            record[k.strip()] = v.strip()
    fields = list(record.keys())
    return [record], fields


def parse_log(raw: str) -> tuple[list[dict], list[str]]:
    records = []
    pattern = re.compile(r"^\[(.+?)\]\s+(\w+)\s+(.+)$")
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            records.append({"timestamp": m.group(1), "level": m.group(2), "message": m.group(3)})
        else:
            records.append({"timestamp": "", "level": "", "message": line})
    return records, ["timestamp", "level", "message"]


def parse(raw: str, fmt: str) -> tuple[list[dict], list[str]]:
    if fmt == "json":
        return parse_json(raw)
    if fmt == "csv":
        return parse_csv(raw, ",")
    if fmt == "tsv":
        return parse_csv(raw, "\t")
    if fmt == "kv":
        return parse_kv(raw)
    if fmt == "logfile":
        return parse_log(raw)
    # plain text — one record per line
    lines = raw.split("\n")
    return [{"line": i + 1, "content": l} for i, l in enumerate(lines)], ["line", "content"]


# ── Cleaners ─────────────────────────────────────────────────────────────────

def clean_value(val: Any, field_name: str, options: dict) -> tuple[Any, str | None]:
    """Clean a single value. Returns (new_value, reason_string | None)"""
    if val is None:
        return val, None

    original = val

    # Work on strings
    if isinstance(val, str):
        # Trim whitespace
        if options.get("trim_whitespace") and val != val.strip():
            val = val.strip()

        # Nullish normalization
        if options.get("normalize_nulls") and val.lower() in NULLISH:
            return None, f'"{original}" → null (nullish value)'

        # Boolean normalization
        if val.lower() == "true":
            return True, f'"{original}" → true (boolean)'
        if val.lower() == "false":
            return False, f'"{original}" → false (boolean)'

        # Number normalization
        if val != "" and re.match(r"^-?\d+(\.\d+)?$", val):
            num = float(val) if "." in val else int(val)
            if str(num) != original:
                return num, f'"{original}" → {num} (numeric)'
            return num, None

        # Email normalization
        if options.get("normalize_email"):
            email_fields = {"email", "mail", "e-mail", "email_address"}
            if any(e in field_name.lower() for e in email_fields):
                lowered = val.lower()
                if lowered != val:
                    return lowered, f'"{original}" → "{lowered}" (email normalized)'

        # Whitespace change only
        if isinstance(original, str) and val != original:
            return val, f'"{original}" → "{val}" (whitespace trimmed)'

    return val, None


def clean_records(records: list[dict], fields: list[str], options: dict) -> tuple[list[dict], list[dict]]:
    """Clean all records. Returns (cleaned_records, list_of_changes)"""
    cleaned = []
    all_changes = []

    for i, record in enumerate(records):
        new_record = {}
        row_changes = []
        for f in fields:
            val = record.get(f)
            new_val, reason = clean_value(val, f, options)
            new_record[f] = new_val
            if reason:
                row_changes.append({"row": i + 1, "field": f, "reason": reason})

        cleaned.append(new_record)
        all_changes.extend(row_changes)

    return cleaned, all_changes


def deduplicate(records: list[dict], fields: list[str]) -> tuple[list[dict], int]:
    seen = set()
    result = []
    for r in records:
        key = json.dumps([r.get(f) for f in fields], sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result, len(records) - len(result)


def remove_empty_rows(records: list[dict], fields: list[str]) -> tuple[list[dict], int]:
    filtered = [
        r for r in records
        if any(r.get(f) not in (None, "", []) for f in fields)
    ]
    return filtered, len(records) - len(filtered)


# ── Column Stats ──────────────────────────────────────────────────────────────

def compute_column_stats(records: list[dict], fields: list[str]) -> dict:
    stats = {}
    total = len(records)
    if total == 0:
        return stats
    for f in fields:
        values = [r.get(f) for r in records]
        null_count = sum(1 for v in values if v is None or v == "")
        unique_vals = set(str(v) for v in values if v is not None and v != "")
        stats[f] = {
            "total": total,
            "null_count": null_count,
            "null_pct": round(null_count / total * 100, 1),
            "unique_count": len(unique_vals),
            "complete_pct": round((total - null_count) / total * 100, 1),
        }
    return stats


# ── Main Entry ────────────────────────────────────────────────────────────────

def process(raw: str, options: dict) -> ProcessResult:
    result = ProcessResult()

    # Detect format
    fmt = options.get("format", "auto")
    if fmt == "auto":
        fmt = detect_format(raw)
    result.format_detected = fmt

    # Parse
    records, fields = parse(raw, fmt)
    result.records_in = len(records)
    result.fields = fields

    # Remove empty rows before cleaning
    records, empty_removed = remove_empty_rows(records, fields)
    result.empty_removed = empty_removed

    # Clean
    records, changes = clean_records(records, fields, options)
    result.changes = changes

    # Dedupe
    if options.get("dedupe", True):
        records, dupes = deduplicate(records, fields)
        result.dupes_removed = dupes

    result.records = records
    result.records_out = len(records)
    result.column_stats = compute_column_stats(records, fields)

    return result
