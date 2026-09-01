#!/usr/bin/env python3
"""
Backfill .ai-log/*.jsonl (the live session log plus every archived day) into
Braintrust, for the user's own visibility.

This is separate from scripts/submit_log.py, which POSTs the same log
directory to the AI20K grading server (a different destination, different
credential) -- this script only mirrors a copy into the user's personal
Braintrust project.

Secret-looking strings (GitHub/OpenAI/Anthropic-style tokens, Gemini "AQ."
keys, AWS access keys, the course's own ai20k_ log key, PEM private key
blocks, database URLs with an embedded password) are redacted before upload:
months of session logs that quote `git remote -v`, `cat .env`, etc. carry
real credentials verbatim, and Braintrust is a third-party service.

Usage:
  python scripts/upload_ailog_to_braintrust.py            # upload everything
  python scripts/upload_ailog_to_braintrust.py --dry-run  # count + redaction preview only, no network calls
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

LOG_DIR = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))

REDACT_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"ai20k_[A-Za-z0-9_-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    # DB connection strings: keep the scheme/host, drop user:password.
    re.compile(r"((?:postgresql|postgres|mysql|mongodb)(?:\+\w+)?://)[^:\s]+:[^@\s]+@"),
]


def redact(value):
    if isinstance(value, str):
        for pat in REDACT_PATTERNS:
            value = pat.sub(
                r"\1[REDACTED]@" if pat.groups else "[REDACTED]",
                value,
            )
        return value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def iter_log_files():
    archive_dir = LOG_DIR / "archive"
    if archive_dir.is_dir():
        yield from sorted(archive_dir.glob("*.jsonl"))
    live = LOG_DIR / "session.jsonl"
    if live.exists():
        yield live


def entry_to_log_fields(entry: dict) -> dict:
    event = entry.get("event", "")
    if event == "UserPromptSubmit":
        input_val = entry.get("prompt", "")
        output_val = None
    else:
        input_val = {"tool_name": entry.get("tool_name"), "tool_input": entry.get("tool_input")}
        output_val = entry.get("tool_response")

    metadata = {k: v for k, v in entry.items() if k not in ("prompt", "tool_input", "tool_response")}
    tags = [t for t in (entry.get("tool"), event) if t]
    return {"input": input_val, "output": output_val, "metadata": metadata, "tags": tags}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Count + preview redaction, no upload.")
    args = parser.parse_args()

    api_key = os.environ.get("BRAINTRUST_API_KEY")
    project_id = os.environ.get("BRAINTRUST_PROJECT_ID")
    if not args.dry_run and (not api_key or not project_id):
        print("BRAINTRUST_API_KEY / BRAINTRUST_PROJECT_ID not set in .env.", file=sys.stderr)
        sys.exit(1)

    logger = None
    if not args.dry_run:
        import braintrust
        logger = braintrust.init_logger(project_id=project_id, api_key=api_key)

    total = 0
    redacted_count = 0
    skipped = 0

    for path in iter_log_files():
        file_total = 0
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                redacted_entry = redact(entry)
                if redacted_entry != entry:
                    redacted_count += 1
                fields = entry_to_log_fields(redacted_entry)
                if logger is not None:
                    logger.log(id=f"{path.stem}-{line_no}", **fields)
                total += 1
                file_total += 1
        print(f"[{path.relative_to(LOG_DIR.parent) if LOG_DIR.parent != Path('.') else path}] {file_total} entries")

    if logger is not None:
        import braintrust
        braintrust.flush()

    mode = "DRY RUN — nothing uploaded" if args.dry_run else "uploaded to Braintrust"
    print(f"\nDone ({mode}). Total entries: {total}, redacted: {redacted_count}, skipped (bad json): {skipped}")


if __name__ == "__main__":
    main()
