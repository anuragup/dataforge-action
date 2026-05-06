# DataForge — Data Quality Check

> Zero-config data quality checks for GitHub Actions. Drop it into any pipeline, get a health score and PR summary instantly.

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-DataForge-green?logo=github)](https://github.com/marketplace/actions/dataforge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What it does

DataForge scans your data files on every PR and tells you exactly what's wrong — before bad data hits your database, breaks your pipeline, or corrupts your analytics.

- ✅ **Auto-detects** CSV, TSV, JSON, Key=Value, and log formats
- ✅ **Cleans** whitespace, null values, email casing, type mismatches
- ✅ **Deduplicates** exact duplicate rows
- ✅ **Scores** your data 0–100 with a per-dimension breakdown
- ✅ **Posts a markdown summary** directly on your PR
- ✅ **Generates an HTML report** as a downloadable artifact
- ✅ **Fails the build** if quality drops below your threshold

No cloud account. No API keys. No config files required.

---

## Quickstart

```yaml
# .github/workflows/data-quality.yml
name: Data Quality

on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run DataForge
        uses: yourname/dataforge-action@v1
        with:
          input: data/customers.csv

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: data-quality-report
          path: "*_report.html"
```

That's it. DataForge will post a comment like this on your PR:

---

## Example PR Comment

### 🔍 DataForge — Data Quality Report

**File:** `customers.csv` | **Format:** `CSV`

### Health Score

| Score | Grade | Status |
|-------|-------|--------|
| **74/100** | **C** | 🟠 Fair |

#### Score Breakdown

| Dimension | Score | Max | Bar |
|-----------|-------|-----|-----|
| Completeness | 22 | 30 | `███████░░░` |
| Uniqueness | 20 | 25 | `████████░░` |
| Consistency | 17 | 25 | `██████░░░░` |
| Validity | 15 | 20 | `███████░░░` |

### Summary

| Metric | Value |
|--------|-------|
| Records in | 120 |
| Records out | 117 |
| Duplicates removed | 3 |
| Values cleaned | 14 |
| Fields | 6 |

### Changes Applied

| Row | Field | Change |
|-----|-------|--------|
| 1 | `email` | "ALICE@CO.COM" → "alice@co.com" (email normalized) |
| 3 | `salary` | "NULL" → null (nullish value) |
| 7 | `name` | " Bob " → "Bob" (whitespace trimmed) |

---

## All Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `input` | File path or glob (`data/*.csv`) | **required** |
| `output` | Path to write cleaned file | auto |
| `format` | `auto`, `csv`, `tsv`, `json`, `kv`, `logfile` | `auto` |
| `dedupe` | Remove duplicate rows | `true` |
| `normalize_nulls` | Treat NULL, N/A, none as null | `true` |
| `trim_whitespace` | Strip leading/trailing spaces | `true` |
| `normalize_email` | Lowercase email fields | `true` |
| `fail_below_score` | Fail build if score < N (0 = disabled) | `0` |
| `post_summary` | Post markdown summary on PR | `true` |
| `github_token` | Token for PR comments | `github.token` |

## All Outputs

| Output | Description |
|--------|-------------|
| `health_score` | 0–100 quality score |
| `records_in` | Input record count |
| `records_out` | Output record count after cleaning |
| `issues_found` | Total values cleaned |
| `dupes_removed` | Duplicate rows removed |
| `report_path` | Path to generated HTML report |

---

## Common Recipes

### Fail the build if data quality drops

```yaml
- uses: yourname/dataforge-action@v1
  with:
    input: data/customers.csv
    fail_below_score: 80
```

### Check multiple files

```yaml
- uses: yourname/dataforge-action@v1
  with:
    input: data/*.csv
```

### Use the score in later steps

```yaml
- uses: yourname/dataforge-action@v1
  id: dataforge
  with:
    input: data/leads.csv

- name: Notify if poor quality
  if: ${{ steps.dataforge.outputs.health_score < 70 }}
  run: echo "Data quality is low — review before importing"
```

### Write cleaned file back to repo

```yaml
- uses: yourname/dataforge-action@v1
  with:
    input: data/raw_export.csv
    output: data/clean_export.csv

- uses: stefanzweifel/git-auto-commit-action@v5
  with:
    commit_message: "chore: auto-clean data export"
    file_pattern: data/clean_export.csv
```

---

## How the Health Score Works

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Completeness | 30pts | % of non-null values across all columns |
| Uniqueness | 25pts | Penalises duplicate rows |
| Consistency | 25pts | Penalises values that needed cleaning |
| Validity | 20pts | % of records that survived cleaning |

| Score | Grade | Meaning |
|-------|-------|---------|
| 90–100 | A 🟢 | Excellent — production ready |
| 75–89 | B 🟡 | Good — minor issues |
| 60–74 | C 🟠 | Fair — review before importing |
| 40–59 | D 🔴 | Poor — significant issues |
| 0–39 | F 🔴 | Critical — do not use |

---

## License

MIT — free to use, modify and distribute.

---

## Contributing

Issues and PRs welcome. If DataForge helped you catch a data problem, consider leaving a ⭐ — it helps others find it.

## Security & Privacy

DataForge is designed to be safe for use with sensitive data files.

| Protection | Detail |
|-----------|--------|
| 🔒 Data stays on runner | Zero calls to external servers — your data never leaves GitHub infrastructure |
| 🔒 Privacy mode on by default | Actual values never appear in PR comments or reports — only change types and counts |
| 🔒 No telemetry | No analytics, no tracking, no phoning home |
| 🔒 One outbound call | Only to the GitHub API to post the PR comment |
| 🔒 Fully open source | Every line is auditable — verify before you trust |

### Pin to a commit SHA (recommended for production)

Tags can be silently updated. Pin to a commit SHA for guaranteed immutability:

```yaml
uses: yourname/dataforge-action@a1b2c3d4  # v1.0.0
```

### What privacy mode does

When `privacy_mode: true` (the default), the PR comment and HTML report show only change **types** and **counts** — never actual before/after values. For example instead of showing `"ALICE@CO.COM" → "alice@co.com"` it shows `email | email normalized | 1`.

See [SECURITY.md](.github/SECURITY.md) for full details.
# dataforge-action
