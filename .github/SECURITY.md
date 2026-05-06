# Security Policy

## Your Data Stays on Your Runner

DataForge processes files **entirely inside your GitHub Actions runner VM**.

- ✅ Zero network calls to external servers
- ✅ No telemetry, no analytics, no tracking
- ✅ The only outbound call is posting a comment to GitHub's own API
- ✅ Privacy mode is ON by default — actual data values never appear in reports or PR comments
- ✅ Fully open source — every line is auditable

## Verify It Yourself

Pin to a specific commit SHA rather than a tag:

```yaml
uses: yourname/dataforge-action@SHA_HERE  # v1.0.0
```

This guarantees you're running exactly the code you reviewed.

## Sensitive Columns

Use `ignore_columns` in your config to skip columns entirely:

```yaml
# dataforge.yml
ignore_columns:
  - password
  - ssn
  - credit_card
  - api_key
```

## Reporting a Vulnerability

Please open a GitHub Issue marked `[SECURITY]` or email security@yourdomain.com.
We aim to respond within 48 hours.
