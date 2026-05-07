#!/usr/bin/env python3
"""
main.py — DataForge GitHub Action entry point
Reads inputs from environment variables, runs the pipeline,
posts a markdown summary on the PR, and writes the HTML report.
"""

import os
import sys
import json
import glob
import requests
from pathlib import Path

from processor import process
from scorer import compute_score
from reporter import generate_markdown, generate_html


# ── Helpers ───────────────────────────────────────────────────────────────────

def env_bool(key: str, default: bool = True) -> bool:
    return os.environ.get(key, str(default)).lower() in ("true", "1", "yes")

def env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def set_output(name: str, value: str):
    """Write GitHub Actions output variable."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"::set-output name={name}::{value}")

def post_pr_comment(token: str, markdown: str):
    """Post or update a PR comment via GitHub API."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF", "")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not token or not repo:
        print("⚠ Skipping PR comment: no token or repo context.")
        return

    # Get PR number from event payload
    pr_number = None
    if event_path and Path(event_path).exists():
        with open(event_path) as f:
            event = json.load(f)
        pr_number = event.get("pull_request", {}).get("number") or event.get("number")

    if not pr_number:
        print("⚠ Not a PR context — skipping comment.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    comments_url = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"

    # Check for existing DataForge comment to update instead of duplicating
    existing_id = None
    try:
        resp = requests.get(comments_url, headers=headers, timeout=10)
        if resp.ok:
            for comment in resp.json():
                if "DataForge" in comment.get("body", "") and "Data Quality Report" in comment.get("body", ""):
                    existing_id = comment["id"]
                    break
    except Exception as e:
        print(f"⚠ Could not fetch existing comments: {e}")

    body = {"body": markdown}

    try:
        if existing_id:
            url = f"{api_url}/repos/{repo}/issues/comments/{existing_id}"
            resp = requests.patch(url, json=body, headers=headers, timeout=10)
            print(f"✓ Updated existing PR comment (id={existing_id})")
        else:
            resp = requests.post(comments_url, json=body, headers=headers, timeout=10)
            print(f"✓ Posted new PR comment")

        if not resp.ok:
            print(f"⚠ GitHub API error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠ Failed to post PR comment: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Read inputs
    input_pattern = env_str("INPUT_FILE")
    output_file   = env_str("OUTPUT_FILE")
    fmt           = env_str("INPUT_FORMAT", "auto")
    dedupe        = env_bool("DEDUPE", True)
    norm_nulls    = env_bool("NORMALIZE_NULLS", True)
    trim_ws       = env_bool("TRIM_WHITESPACE", True)
    norm_email    = env_bool("NORMALIZE_EMAIL", True)
    fail_below    = int(env_str("FAIL_BELOW_SCORE", "0"))
    post_summary  = env_bool("POST_SUMMARY", True)
    token         = env_str("GITHUB_TOKEN")
    privacy_mode  = env_bool("PRIVACY_MODE", True)

    if not input_pattern:
        print("❌ ERROR: INPUT_FILE is required.")
        sys.exit(1)

    # Resolve glob
    files = glob.glob(input_pattern, recursive=True)
    if not files:
        print(f"❌ ERROR: No files matched pattern: {input_pattern}")
        sys.exit(1)

    options = {
        "format": fmt,
        "dedupe": dedupe,
        "normalize_nulls": norm_nulls,
        "trim_whitespace": trim_ws,
        "normalize_email": norm_email,
    }

    all_markdowns = []
    overall_scores = []
    failed = False

    for filepath in files:
        print(f"\n{'='*60}")
        print(f"📂 Processing: {filepath}")
        print(f"{'='*60}")

        # Read file
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
        except Exception as e:
            print(f"❌ Could not read {filepath}: {e}")
            continue

        if not raw.strip():
            print(f"⚠ Skipping empty file: {filepath}")
            continue

        # Process
        result = process(raw, options)
        score_data = compute_score(result)
        score = score_data["score"]
        overall_scores.append(score)

        # Console summary — no actual data values shown ever
        print(f"  Format detected : {result.format_detected.upper()}")
        print(f"  Records in      : {result.records_in}")
        print(f"  Records out     : {result.records_out}")
        print(f"  Dupes removed   : {result.dupes_removed}")
        print(f"  Values cleaned  : {len(result.changes)}")
        print(f"  Fields          : {len(result.fields)}")
        print(f"  Health score    : {score}/100 ({score_data['grade']} — {score_data['label']})")

        if result.changes:
            from collections import defaultdict
            grouped = defaultdict(int)
            for c in result.changes:
                key = c["reason"].split("(")[-1].rstrip(")") if "(" in c["reason"] else "cleaned"
                grouped[(c["field"], key)] += 1
            print(f"\n  Changes by type (no values shown):")
            for (field, ctype), count in sorted(grouped.items()):
                print(f"    {field}: {ctype} x{count}")

        # Write cleaned output
        out_path = output_file or filepath.replace(".", "_clean.", 1)
        if result.records and result.fields:
            import csv, io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=result.fields)
            writer.writeheader()
            writer.writerows(result.records)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(buf.getvalue())
            print(f"\n  ✓ Cleaned file written to: {out_path}")

        # Generate HTML report
        filename = Path(filepath).name
        html = generate_html(filename, result, score_data, privacy_mode=privacy_mode)
        report_path = filepath.replace(".csv", "_report.html").replace(".json", "_report.html").replace(".tsv", "_report.html")
        report_path = report_path if report_path != filepath else filepath + "_report.html"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ HTML report written to:  {report_path}")
        set_output("report_path", report_path)

        # Generate markdown summary
        md = generate_markdown(filename, result, score_data, privacy_mode=privacy_mode)
        all_markdowns.append(md)

        # Write to GitHub Step Summary — visible on every run, not just PRs
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write(md + "\n\n")
            print(f"  ✓ Step summary written")

        # Set outputs for last file (or aggregate later)
        set_output("health_score", str(score))
        set_output("records_in", str(result.records_in))
        set_output("records_out", str(result.records_out))
        set_output("issues_found", str(len(result.changes)))
        set_output("dupes_removed", str(result.dupes_removed))

        # Check fail threshold
        if fail_below > 0 and score < fail_below:
            print(f"\n  ❌ Health score {score} is below threshold {fail_below}")
            failed = True

    # Post PR comment (combined if multiple files)
    if post_summary and all_markdowns:
        combined_md = "\n\n---\n\n".join(all_markdowns)
        if len(files) > 1:
            avg = round(sum(overall_scores) / len(overall_scores))
            combined_md = f"## 🔍 DataForge — {len(files)} files scanned · Avg score: {avg}/100\n\n" + combined_md
        post_pr_comment(token, combined_md)

    print(f"\n{'='*60}")
    if overall_scores:
        avg = round(sum(overall_scores) / len(overall_scores))
        print(f"✅ DataForge complete · {len(files)} file(s) · Avg score: {avg}/100")
    print(f"{'='*60}\n")

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
