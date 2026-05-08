# DataForge — Data Quality Check

> Zero-config data quality checks for GitHub Actions. Health scores, PR comments, and clean output — no cloud account needed.

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-DataForge-green?logo=github)](https://github.com/marketplace/actions/dataforge-data-quality-check)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quickstart

```yaml
name: Data Quality
on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Run DataForge
        uses: anuragup/dataforge-action@v3
        with:
          input: data/customers.csv

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: data-quality-report
          path: "**/*_report.html"

      - name: Upload Cleaned Data
        uses: actions/upload-artifact@v4
        with:
          name: cleaned-data
          path: "**/*_clean.csv"
```

That's it. You get:
- A **health score** in the Step Summary tab (every run)
- A **markdown comment** on your PR
- A downloadable **HTML report**
- A **cleaned file** ready to use

---

## What it does

- ✅ Auto-detects CSV, TSV, JSON, Key=Value, and log formats
- ✅ Cleans whitespace, null values, email casing, type mismatches
- ✅ Deduplicates rows and removes empty records
- ✅ Scores your data 0–100 across 4 dimensions
- ✅ Outputs a cleaned file
- 🔒 Privacy mode on by default — actual values never appear in reports or logs

---

## Example Output

| Score | Grade | Status |
|-------|-------|--------|
| **74/100** | **C** | 🟠 Fair |

| Metric | Value | Note |
|--------|-------|------|
| Records in | 120 | original count |
| Records out | **115** | ✅ cleaned & kept |
| Duplicates removed | 3 | intentional |
| Empty rows removed | 2 | intentional |
| Parse errors | 0 | ✅ none |

| Field | Change Type | Count |
|-------|-------------|-------|
| `email` | normalized to lowercase | 8 |
| `name` | whitespace trimmed | 5 |
| `salary` | normalized to null | 6 |

> 🔒 Privacy mode on — only change types shown, never actual values.

---

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `input` | File path or glob (`data/*.csv`) | **required** |
| `output` | Path for cleaned file | auto (`*_clean.*`) |
| `format` | `auto`, `csv`, `tsv`, `json`, `kv`, `logfile` | `auto` |
| `dedupe` | Remove duplicate rows | `true` |
| `normalize_nulls` | Treat NULL, N/A, none as null | `true` |
| `trim_whitespace` | Strip leading/trailing spaces | `true` |
| `normalize_email` | Lowercase email fields | `true` |
| `privacy_mode` | Hide actual values from reports | `true` |
| `fail_below_score` | Fail if score < N (0 = disabled) | `0` |
| `post_summary` | Post markdown on PR | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `health_score` | 0–100 quality score |
| `records_in` | Input record count |
| `records_out` | Records after cleaning |
| `issues_found` | Values cleaned |
| `dupes_removed` | Duplicates removed |
| `report_path` | Path to HTML report |

---

## Recipes

**Fail the build if quality drops:**
```yaml
- uses: anuragup/dataforge-action@v3
  with:
    input: data/customers.csv
    fail_below_score: 80
```

**Check multiple files:**
```yaml
- uses: anuragup/dataforge-action@v3
  with:
    input: data/*.csv
```

**Use score in later steps:**
```yaml
- uses: anuragup/dataforge-action@v3
  id: dataforge
  with:
    input: data/leads.csv

- if: ${{ steps.dataforge.outputs.health_score < 70 }}
  run: echo "⚠ Data quality is low"
```

---

## Health Score

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Completeness | 30pts | % non-null values |
| Uniqueness | 25pts | Duplicate rows |
| Consistency | 25pts | Values needing cleanup |
| Validity | 20pts | Records surviving cleaning |

| Score | Grade |
|-------|-------|
| 90–100 | A 🟢 Excellent |
| 75–89 | B 🟡 Good |
| 60–74 | C 🟠 Fair |
| 40–59 | D 🟠 Poor |
| 0–39 | F 🔴 Critical |

---

## Tested At Scale

| Dataset | Rows | Time | Score |
|---------|------|------|-------|
| Clean CSV | 3 | <1s | 100/100 |
| Messy CSV | 10 | <1s | 53/100 |
| Messy JSON | 5,000 | <1s | 78/100 |
| Messy TSV | 20,000 | <1s | 73/100 |
| Large CSV | 50,000 | ~15s | 74/100 |

---

## Security & Privacy

| | |
|---|---|
| 🔒 Data stays on runner | Zero external calls — data never leaves GitHub |
| 🔒 Privacy mode default | Only change types shown, never values |
| 🔒 No telemetry | No tracking, no analytics |
| 🔒 Open source | Every line auditable |

For production, pin to a commit SHA:
```yaml
uses: anuragup/dataforge-action@COMMIT_SHA
```

See [SECURITY.md](.github/SECURITY.md) for details.

---

MIT Licensed · [Issues & PRs welcome](https://github.com/anuragup/dataforge-action/issues) · ⭐ if it helped
