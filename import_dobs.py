#!/usr/bin/env python3
"""
Import DOBs into the User table by matching on email.

Usage:
  python import_dobs.py path/to/dobs.csv [--dry-run]

CSV columns:
  - email (required)
  - dob (optional): e.g. 1990-07-15, 15/07/1990, 07/15/1990, 1990/07/15
  - pub_dob (optional): true/false/1/0/yes/no
"""

import argparse
import csv
from datetime import datetime, date
from pathlib import Path

# Try to use dateutil for robust parsing if available; otherwise fall back.
try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

# ---- Adjust these imports to your app structure ----
from dgp_intra import create_app   # your factory function
from dgp_intra.extensions import db
from dgp_intra.models import User  # where your User model lives
# ---------------------------------------------------

TRUE_SET = {"true", "1", "yes", "y", "on"}
FALSE_SET = {"false", "0", "no", "n", "off", ""}

KNOWN_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
]

def parse_bool(value, default=None):
    if value is None:
        return default
    s = str(value).strip().lower()
    if s in TRUE_SET:
        return True
    if s in FALSE_SET:
        return False
    return default

def parse_date(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # dateutil if present
    if date_parser:
        try:
            dt = date_parser.parse(s, dayfirst=False, yearfirst=False)
            return dt.date()
        except Exception:
            pass

    # fallback to common formats
    for fmt in KNOWN_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unrecognized date format: {s}")

def main():
    parser = argparse.ArgumentParser(description="Import DOBs by matching email.")
    parser.add_argument("csv_path", type=Path, help="Path to CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Do not commit changes")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        total_rows = 0
        matched = 0
        updated = 0
        missing_email = 0
        not_found = 0
        errors = 0

        with args.csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # Normalize header keys to lowercase for convenience
            field_map = {k: k.lower() for k in reader.fieldnames or []}

            if "email" not in [k.lower() for k in (reader.fieldnames or [])]:
                raise SystemExit("CSV must include an 'email' column.")

            for row in reader:
                total_rows += 1
                # Lowercase-keyed dict
                row_l = {field_map.get(k, k).lower(): v for k, v in row.items()}

                email = (row_l.get("email") or "").strip()
                if not email:
                    missing_email += 1
                    continue

                user = User.query.filter_by(email=email).first()
                if not user:
                    not_found += 1
                    continue

                matched += 1

                # Parse dob and pub_dob if present
                dob_val = row_l.get("dob")
                pub_dob_val = row_l.get("pub_dob")

                dob_parsed = None
                pub_dob_parsed = None

                try:
                    if dob_val is not None:
                        dob_parsed = parse_date(dob_val)
                except Exception as e:
                    errors += 1
                    print(f"[ERROR] {email}: {e}")
                    continue

                pub_dob_parsed = parse_bool(pub_dob_val, default=None)

                changed = False
                if dob_val is not None and user.dob != dob_parsed:
                    user.dob = dob_parsed
                    changed = True

                if pub_dob_val is not None and pub_dob_parsed is not None and user.pub_dob != pub_dob_parsed:
                    user.pub_dob = pub_dob_parsed
                    changed = True

                if changed:
                    updated += 1

            if args.dry_run:
                db.session.rollback()
            else:
                db.session.commit()

        print("---- Import summary ----")
        print(f"Total CSV rows:        {total_rows}")
        print(f"Matched existing users:{matched}")
        print(f"Updated users:         {updated}")
        print(f"Rows w/o email:        {missing_email}")
        print(f"Emails not found:      {not_found}")
        print(f"Errors:                {errors}")
        print(f"Committed:             {not args.dry_run}")

if __name__ == "__main__":
    main()

