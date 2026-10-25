-- ============================================================================
-- Canonical SQLite Database Schema for Stage AI Application Ecosystem
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Scraped Job Postings & Qualification Table
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    job_url TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL, -- 'linkedin', 'wttj', 'direct'
    workplace_type TEXT NOT NULL, -- 'hybrid', 'on-site', 'remote'
    start_date TEXT,
    duration_weeks INTEGER,
    description TEXT NOT NULL,
    raw_requirements TEXT,
    is_iad_compliant BOOLEAN NOT NULL DEFAULT 0,
    compliance_score REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Application Tracking Pipeline (Kanban Statuses)
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'wishlist', -- 'wishlist', 'to_apply', 'applied', 'interview', 'offer', 'rejected'
    application_mode TEXT NOT NULL DEFAULT 'semi_auto', -- 'auto', 'semi_auto'
    cv_pdf_path TEXT,
    cover_letter_pdf_path TEXT,
    requires_cover_letter BOOLEAN NOT NULL DEFAULT 0,
    applied_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- 3. Human-in-the-Loop Doubt & Resolution Queue
CREATE TABLE IF NOT EXISTS doubts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    doubt_type TEXT NOT NULL, -- 'form_question', 'unclear_stack', 'unclear_duration', 'date_conflict'
    question_text TEXT NOT NULL,
    suggested_answer TEXT,
    user_decision TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'resolved', 'ignored'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- 4. Cold Outreach Targets & Mapping
CREATE TABLE IF NOT EXISTS cold_outreach_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    website TEXT NOT NULL,
    ai_domain TEXT NOT NULL,
    tech_stack TEXT,
    key_contacts TEXT, -- JSON array of [{name, role, linkedin, email}]
    recommended_approach TEXT,
    status TEXT NOT NULL DEFAULT 'mapped', -- 'mapped', 'contacted', 'replied', 'closed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Persistent System Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Fast Querying
CREATE INDEX IF NOT EXISTS idx_jobs_compliance ON jobs(is_iad_compliant);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_doubts_status ON doubts(status);
CREATE INDEX IF NOT EXISTS idx_cold_outreach_status ON cold_outreach_targets(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
