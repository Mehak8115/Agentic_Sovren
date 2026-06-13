"""
migrate_to_postgres.py
----------------------
One-time migration script: MongoDB → PostgreSQL

Migrates structured collections only:
  - applications
  - hr_jobs
  - hr_notifications
  - available_jobs

Flexible/nested data (candidates, boats, bookings, users) stays in MongoDB.

Usage:
  1. Install psycopg2:  pip install psycopg2-binary
  2. Create the database in postgres:  createdb sovren
  3. Update PG_DSN below with your credentials
  4. Run: python database/migrate_to_postgres.py
"""

import json
from datetime import datetime
from pymongo import MongoClient
import psycopg2
from psycopg2.extras import execute_values

# ── Config ──────────────────────────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB  = "sovren"

PG_DSN = "dbname=sovren user=postgres password=Post123 host=localhost port=5432"

# ── Helpers ─────────────────────────────────────────────────────────────────
def safe_str(val):
    if val is None:
        return None
    return str(val)

def safe_list(val):
    """Convert list/array to comma-separated string for PostgreSQL text column."""
    if not val:
        return ""
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def safe_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val) if val is not None else False

def safe_ts(val):
    """Parse ISO string or return None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

# ── Create tables ─────────────────────────────────────────────────────────────
CREATE_TABLES = """
-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id                  SERIAL PRIMARY KEY,
    mongo_id            TEXT UNIQUE,
    candidate_id        TEXT NOT NULL,
    candidate_name      TEXT,
    job_id              TEXT NOT NULL,
    job_title           TEXT,
    job_role            TEXT,
    gap_score           NUMERIC(5,1),
    skill_match_pct     NUMERIC(5,1),
    is_eligible         BOOLEAN DEFAULT FALSE,
    missing_mandatory   TEXT,           -- comma-separated skills
    missing_certs       TEXT,           -- comma-separated certs
    present_skills      TEXT,           -- comma-separated skills
    status              TEXT DEFAULT 'submitted',
    applied_at          TIMESTAMPTZ
);

-- HR Jobs table
CREATE TABLE IF NOT EXISTS hr_jobs (
    id                  SERIAL PRIMARY KEY,
    mongo_id            TEXT UNIQUE,
    title               TEXT,
    role                TEXT,
    location            TEXT,
    salary              TEXT,
    vacancies           INTEGER DEFAULT 1,
    minimum_experience  INTEGER DEFAULT 0,
    summary             TEXT,
    department          TEXT,
    mandatory_skills    TEXT,           -- comma-separated
    optional_skills     TEXT,           -- comma-separated
    required_certs      TEXT,           -- comma-separated
    responsibilities    TEXT,           -- comma-separated
    benefits            TEXT,           -- comma-separated
    status              TEXT DEFAULT 'draft',
    created_at          TIMESTAMPTZ,
    published_at        TIMESTAMPTZ
);

-- HR Notifications table
CREATE TABLE IF NOT EXISTS hr_notifications (
    id                  SERIAL PRIMARY KEY,
    mongo_id            TEXT UNIQUE,
    type                TEXT DEFAULT 'new_application',
    candidate_id        TEXT,
    candidate_name      TEXT,
    job_id              TEXT,
    job_title           TEXT,
    gap_score           NUMERIC(5,1),
    skill_match_pct     NUMERIC(5,1),
    is_eligible         BOOLEAN DEFAULT FALSE,
    is_read             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ
);

-- Available Jobs table (published jobs visible to crew)
CREATE TABLE IF NOT EXISTS available_jobs (
    id                  SERIAL PRIMARY KEY,
    mongo_id            TEXT UNIQUE,
    hr_job_id           TEXT,
    title               TEXT,
    role                TEXT,
    location            TEXT,
    salary              TEXT,
    vacancies           INTEGER DEFAULT 1,
    minimum_experience  INTEGER DEFAULT 0,
    mandatory_skills    TEXT,           -- comma-separated
    optional_skills     TEXT,           -- comma-separated
    required_certs      TEXT,           -- comma-separated
    status              TEXT DEFAULT 'published'
);
"""

# ── Migration functions ────────────────────────────────────────────────────────

def migrate_applications(mongo_db, pg_cur):
    print("\n[1/4] Migrating applications...")
    docs = list(mongo_db.applications.find({}))
    if not docs:
        print("  No documents found.")
        return 0

    rows = []
    for d in docs:
        rows.append((
            safe_str(d.get("_id")),
            safe_str(d.get("candidate_id")),
            safe_str(d.get("candidate_name")),
            safe_str(d.get("job_id")),
            safe_str(d.get("job_title")),
            safe_str(d.get("job_role")),
            safe_float(d.get("gap_score")),
            safe_float(d.get("skill_match_pct")),
            safe_bool(d.get("is_eligible")),
            safe_list(d.get("missing_mandatory")),
            safe_list(d.get("missing_certs")),
            safe_list(d.get("present_skills")),
            safe_str(d.get("status", "submitted")),
            safe_ts(d.get("applied_at")),
        ))

    execute_values(pg_cur, """
        INSERT INTO applications
            (mongo_id, candidate_id, candidate_name, job_id, job_title, job_role,
             gap_score, skill_match_pct, is_eligible, missing_mandatory,
             missing_certs, present_skills, status, applied_at)
        VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
    """, rows)
    print(f"  ✅ {len(rows)} applications migrated.")
    return len(rows)


def migrate_hr_jobs(mongo_db, pg_cur):
    print("\n[2/4] Migrating hr_jobs...")
    docs = list(mongo_db.hr_jobs.find({}))
    if not docs:
        print("  No documents found.")
        return 0

    rows = []
    for d in docs:
        rows.append((
            safe_str(d.get("_id")),
            safe_str(d.get("title")),
            safe_str(d.get("role")),
            safe_str(d.get("location")),
            safe_str(d.get("salary")),
            safe_int(d.get("vacancies", 1)),
            safe_int(d.get("minimum_experience", 0)),
            safe_str(d.get("summary")),
            safe_str(d.get("department")),
            safe_list(d.get("mandatory_skills")),
            safe_list(d.get("optional_skills")),
            safe_list(d.get("required_certifications")),
            safe_list(d.get("responsibilities")),
            safe_list(d.get("benefits")),
            safe_str(d.get("status", "draft")),
            safe_ts(d.get("created_at")),
            safe_ts(d.get("published_at")),
        ))

    execute_values(pg_cur, """
        INSERT INTO hr_jobs
            (mongo_id, title, role, location, salary, vacancies, minimum_experience,
             summary, department, mandatory_skills, optional_skills, required_certs,
             responsibilities, benefits, status, created_at, published_at)
        VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
    """, rows)
    print(f"  ✅ {len(rows)} HR jobs migrated.")
    return len(rows)


def migrate_hr_notifications(mongo_db, pg_cur):
    print("\n[3/4] Migrating hr_notifications...")
    docs = list(mongo_db.hr_notifications.find({}))
    if not docs:
        print("  No documents found.")
        return 0

    rows = []
    for d in docs:
        rows.append((
            safe_str(d.get("_id")),
            safe_str(d.get("type", "new_application")),
            safe_str(d.get("candidate_id")),
            safe_str(d.get("candidate_name")),
            safe_str(d.get("job_id")),
            safe_str(d.get("job_title")),
            safe_float(d.get("gap_score")),
            safe_float(d.get("skill_match_pct")),
            safe_bool(d.get("is_eligible")),
            safe_bool(d.get("read", False)),
            safe_ts(d.get("created_at")),
        ))

    execute_values(pg_cur, """
        INSERT INTO hr_notifications
            (mongo_id, type, candidate_id, candidate_name, job_id, job_title,
             gap_score, skill_match_pct, is_eligible, is_read, created_at)
        VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
    """, rows)
    print(f"  ✅ {len(rows)} notifications migrated.")
    return len(rows)


def migrate_available_jobs(mongo_db, pg_cur):
    print("\n[4/4] Migrating available_jobs...")
    docs = list(mongo_db.available_jobs.find({}))
    if not docs:
        print("  No documents found.")
        return 0

    rows = []
    for d in docs:
        rows.append((
            safe_str(d.get("_id")),
            safe_str(d.get("hr_job_id")),
            safe_str(d.get("title")),
            safe_str(d.get("role")),
            safe_str(d.get("location")),
            safe_str(d.get("salary")),
            safe_int(d.get("vacancies", 1)),
            safe_int(d.get("minimum_experience", 0)),
            safe_list(d.get("mandatory_skills")),
            safe_list(d.get("optional_skills")),
            safe_list(d.get("required_certifications")),
            safe_str(d.get("status", "published")),
        ))

    execute_values(pg_cur, """
        INSERT INTO available_jobs
            (mongo_id, hr_job_id, title, role, location, salary, vacancies,
             minimum_experience, mandatory_skills, optional_skills,
             required_certs, status)
        VALUES %s
        ON CONFLICT (mongo_id) DO NOTHING
    """, rows)
    print(f"  ✅ {len(rows)} available jobs migrated.")
    return len(rows)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Sovren · MongoDB → PostgreSQL Migration")
    print("=" * 55)

    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    mongo_client = MongoClient(MONGO_URI)
    mongo_db     = mongo_client[MONGO_DB]
    print(f"  ✅ Connected to MongoDB · database: {MONGO_DB}")

    # Connect to PostgreSQL
    print("\nConnecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(PG_DSN)
        pg_cur  = pg_conn.cursor()
        print("  ✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"  ❌ PostgreSQL connection failed: {e}")
        print("  Make sure PostgreSQL is running and PG_DSN is correct.")
        return

    # Create tables
    print("\nCreating tables (if not exist)...")
    pg_cur.execute(CREATE_TABLES)
    pg_conn.commit()
    print("  ✅ Tables ready")

    # Run migrations
    total = 0
    total += migrate_applications(mongo_db, pg_cur)
    total += migrate_hr_jobs(mongo_db, pg_cur)
    total += migrate_hr_notifications(mongo_db, pg_cur)
    total += migrate_available_jobs(mongo_db, pg_cur)

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()
    mongo_client.close()

    print("\n" + "=" * 55)
    print(f"  Migration complete · {total} total records moved")
    print("  MongoDB (stays): candidates, boats, bookings, users")
    print("  PostgreSQL (new): applications, hr_jobs,")
    print("                    hr_notifications, available_jobs")
    print("=" * 55)


if __name__ == "__main__":
    main()
