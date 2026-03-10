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
    image_url TEXT,
    result JSONB NOT NULL,
    drug_count INTEGER DEFAULT 0,
    scanned_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_scans_user
   ON scans(user_id, scanned_at DESC);`,

  // 006: Medication Plans
  `CREATE TABLE IF NOT EXISTS medication_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(50) NOT NULL,
    times JSONB NOT NULL,
    pills_per_dose INTEGER DEFAULT 1,
    total_days INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );`,
  `CREATE INDEX IF NOT EXISTS idx_plans_user
   ON medication_plans(user_id, is_active);`,

  // 007: Medication Logs
  `CREATE TABLE IF NOT EXISTS medication_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES medication_plans(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMPTZ NOT NULL,
    taken_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    note TEXT
  );`,
  `CREATE INDEX IF NOT EXISTS idx_logs_plan
   ON medication_logs(plan_id, scheduled_time DESC);`,
  `CREATE INDEX IF NOT EXISTS idx_logs_status
   ON medication_logs(plan_id, status)
   WHERE status IN ('taken', 'missed');`,
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
