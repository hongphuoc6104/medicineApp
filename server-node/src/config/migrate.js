/**
 * Database migration script.
 * Creates all tables for MedicineApp.
 *
 * Usage: node src/config/migrate.js
 */
import { pool, query } from './database.js';

const MIGRATIONS = [
  // 001: Extensions
  `CREATE EXTENSION IF NOT EXISTS "pgcrypto";`,
  `CREATE EXTENSION IF NOT EXISTS "pg_trgm";`,

  // 002: Users
  `CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);`,

  // 003: Refresh Tokens (JWT Revocation)
  `CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    device_info TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
  );`,
  `CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
   ON refresh_tokens(user_id, revoked_at);`,

  // 004: Drug Cache
  `CREATE TABLE IF NOT EXISTS drug_cache (
    id SERIAL PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'ddi',
    data JSONB NOT NULL,
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    UNIQUE(drug_name, source)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_drug_cache_name_trgm
   ON drug_cache USING GIN (drug_name gin_trgm_ops);`,

  // 005: Scans
  `CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID,
    image_url TEXT,
    result JSONB NOT NULL,
    drug_count INTEGER DEFAULT 0,
    quality_state VARCHAR(20) DEFAULT 'GOOD',
    reject_reason VARCHAR(80),
    quality_score NUMERIC(6,3),
    scanned_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `ALTER TABLE scans ADD COLUMN IF NOT EXISTS session_id UUID;`,
  `ALTER TABLE scans ADD COLUMN IF NOT EXISTS quality_state VARCHAR(20) DEFAULT 'GOOD';`,
  `ALTER TABLE scans ADD COLUMN IF NOT EXISTS reject_reason VARCHAR(80);`,
  `ALTER TABLE scans ADD COLUMN IF NOT EXISTS quality_score NUMERIC(6,3);`,
  `CREATE INDEX IF NOT EXISTS idx_scans_user
   ON scans(user_id, scanned_at DESC);`,
  `CREATE INDEX IF NOT EXISTS idx_scans_session
   ON scans(session_id, scanned_at DESC);`,

  // 005b: Scan Sessions
  `CREATE TABLE IF NOT EXISTS scan_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    converged BOOLEAN DEFAULT false,
    convergence_reason VARCHAR(80),
    merged_result JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
  );`,
  `CREATE INDEX IF NOT EXISTS idx_scan_sessions_user
   ON scan_sessions(user_id, created_at DESC);`,

  // 006: Medication Plans
  `CREATE TABLE IF NOT EXISTS medication_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(50) NOT NULL,
    times JSONB NOT NULL,
    pills_per_dose INTEGER DEFAULT 1,
    dose_schedule JSONB DEFAULT '[]'::jsonb,
    total_days INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `ALTER TABLE medication_plans ADD COLUMN IF NOT EXISTS dose_schedule JSONB DEFAULT '[]'::jsonb;`,
  `CREATE INDEX IF NOT EXISTS idx_plans_user
   ON medication_plans(user_id, is_active);`,

  // 007: Medication Logs
  `CREATE TABLE IF NOT EXISTS medication_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES medication_plans(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMPTZ NOT NULL,
    taken_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    note TEXT,
    occurrence_id VARCHAR(120)
  );`,
  `ALTER TABLE medication_logs ADD COLUMN IF NOT EXISTS occurrence_id VARCHAR(120);`,
  `CREATE INDEX IF NOT EXISTS idx_logs_plan
   ON medication_logs(plan_id, scheduled_time DESC);`,
  `DROP INDEX IF EXISTS uq_logs_plan_occurrence;`,
  `CREATE UNIQUE INDEX IF NOT EXISTS uq_logs_plan_occurrence_all
   ON medication_logs(plan_id, occurrence_id);`,
  `CREATE INDEX IF NOT EXISTS idx_logs_status
   ON medication_logs(plan_id, status)
   WHERE status IN ('taken', 'missed');`,

  // 008: Pill Verification Sessions
  `CREATE TABLE IF NOT EXISTS pill_verification_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    occurrence_id VARCHAR(120) NOT NULL,
    dose_payload JSONB NOT NULL,
    result JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
  );`,
  `CREATE INDEX IF NOT EXISTS idx_pill_verification_sessions_user
   ON pill_verification_sessions(user_id, created_at DESC);`,
  `CREATE INDEX IF NOT EXISTS idx_pill_verification_sessions_occurrence
   ON pill_verification_sessions(occurrence_id, status);`,

  // 009: Pill Verification Assignments
  `CREATE TABLE IF NOT EXISTS pill_verification_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES pill_verification_sessions(id) ON DELETE CASCADE,
    detection_idx INTEGER NOT NULL,
    assigned_drug_name VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'assigned',
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, detection_idx)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_pill_verification_assignments_session
   ON pill_verification_assignments(session_id, detection_idx);`,

  // 010: Pill Reference Sets (per user-plan)
  `CREATE TABLE IF NOT EXISTS pill_reference_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES medication_plans(id) ON DELETE CASCADE,
    drug_name_snapshot VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plan_id)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_pill_reference_sets_user
   ON pill_reference_sets(user_id, updated_at DESC);`,
  `CREATE INDEX IF NOT EXISTS idx_pill_reference_sets_plan
   ON pill_reference_sets(plan_id, status);`,

  // 011: Pill Reference Images
  `CREATE TABLE IF NOT EXISTS pill_reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_set_id UUID REFERENCES pill_reference_sets(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    side VARCHAR(20) DEFAULT 'front',
    quality_score NUMERIC(6,3),
    embedding JSONB,
    confirmed_by_user BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_pill_reference_images_set
   ON pill_reference_images(reference_set_id, created_at DESC);`,

  // 012: Dose Verification Sessions (occurrence-centric)
  `CREATE TABLE IF NOT EXISTS dose_verification_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    occurrence_id VARCHAR(120) NOT NULL,
    scheduled_time TIMESTAMPTZ,
    expected_medications JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    result JSONB DEFAULT '{}'::jsonb,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_dose_verification_sessions_user
   ON dose_verification_sessions(user_id, created_at DESC);`,
  `CREATE INDEX IF NOT EXISTS idx_dose_verification_sessions_occurrence
   ON dose_verification_sessions(occurrence_id, status);`,

  // 013: Dose Verification Detections
  `CREATE TABLE IF NOT EXISTS dose_verification_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES dose_verification_sessions(id) ON DELETE CASCADE,
    detection_idx INTEGER NOT NULL,
    bbox JSONB,
    score NUMERIC(8,4),
    assigned_plan_id VARCHAR(120),
    assigned_drug_name VARCHAR(255),
    confidence NUMERIC(8,4),
    status VARCHAR(20) NOT NULL DEFAULT 'unassigned',
    note TEXT,
    suggestions JSONB DEFAULT '[]'::jsonb,
    source VARCHAR(20) DEFAULT 'auto',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, detection_idx)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_dose_verification_detections_session
   ON dose_verification_detections(session_id, detection_idx);`,

  // 014: Dose Verification Feedback Events
  `CREATE TABLE IF NOT EXISTS dose_verification_feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES dose_verification_sessions(id) ON DELETE CASCADE,
    detection_idx INTEGER,
    action VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_dose_verification_feedback_events_session
   ON dose_verification_feedback_events(session_id, created_at DESC);`,

  // 044: Prescription plan groups (new model)
  `CREATE TABLE IF NOT EXISTS prescription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    total_days INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_prescription_plans_user
   ON prescription_plans(user_id, is_active, created_at DESC);`,

  // 045: Drugs inside one prescription plan
  `CREATE TABLE IF NOT EXISTS prescription_plan_drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    notes TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_prescription_plan_drugs_plan
   ON prescription_plan_drugs(plan_id, sort_order, created_at);`,

  // 046: Time slots inside one prescription plan
  `CREATE TABLE IF NOT EXISTS prescription_plan_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    time VARCHAR(5) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, time)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_prescription_plan_slots_plan
   ON prescription_plan_slots(plan_id, sort_order, time);`,

  // 047: Drug quantities per slot
  `CREATE TABLE IF NOT EXISTS prescription_plan_slot_drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id UUID REFERENCES prescription_plan_slots(id) ON DELETE CASCADE,
    drug_id UUID REFERENCES prescription_plan_drugs(id) ON DELETE CASCADE,
    pills INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(slot_id, drug_id)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_prescription_plan_slot_drugs_slot
   ON prescription_plan_slot_drugs(slot_id);`,

  // 048: Logs for slot occurrences
  `CREATE TABLE IF NOT EXISTS prescription_plan_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    occurrence_id VARCHAR(120) NOT NULL,
    slot_time VARCHAR(5) NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    taken_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL CHECK (status IN ('taken', 'missed', 'skipped', 'pending')),
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, occurrence_id)
  );`,
  `CREATE INDEX IF NOT EXISTS idx_prescription_plan_logs_plan
   ON prescription_plan_logs(plan_id, scheduled_time DESC);`,
];

async function migrate() {
  console.log('🔧 Running migrations...');
  for (let i = 0; i < MIGRATIONS.length; i++) {
    const sql = MIGRATIONS[i];
    const label = sql.substring(0, 60).replace(/\n/g, ' ').trim();
    try {
      await query(sql);
      console.log(`  ✅ [${i + 1}/${MIGRATIONS.length}] ${label}...`);
    } catch (err) {
      console.error(`  ❌ [${i + 1}] ${label}`);
      console.error(`     ${err.message}`);
      process.exit(1);
    }
  }
  console.log('✅ All migrations complete');
  await pool.end();
}

migrate();
