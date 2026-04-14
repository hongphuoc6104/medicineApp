import { jest } from '@jest/globals';
import request from 'supertest';

import app from '../../src/app.js';
import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';
import * as planService from '../../src/services/plan.service.js';
import { clearReconciliationCachesForTests } from '../../src/services/reconciliation.service.js';

const PREFIX = 'test_ci_route_reconcile_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;
let userId;

async function ensureSchema() {
  await query(`CREATE TABLE IF NOT EXISTS scans (
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
  )`);
  await query(`CREATE TABLE IF NOT EXISTS prescription_plans (
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
  )`);
  await query(`CREATE TABLE IF NOT EXISTS prescription_plan_drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    notes TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
  )`);
  await query(`CREATE TABLE IF NOT EXISTS prescription_plan_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    time VARCHAR(5) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, time)
  )`);
  await query(`CREATE TABLE IF NOT EXISTS prescription_plan_slot_drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id UUID REFERENCES prescription_plan_slots(id) ON DELETE CASCADE,
    drug_id UUID REFERENCES prescription_plan_drugs(id) ON DELETE CASCADE,
    pills INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(slot_id, drug_id)
  )`);
  await query(`CREATE TABLE IF NOT EXISTS prescription_plan_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES prescription_plans(id) ON DELETE CASCADE,
    occurrence_id VARCHAR(120) NOT NULL,
    slot_time VARCHAR(5) NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    taken_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, occurrence_id)
  )`);
}

async function clearUserData() {
  await query('DELETE FROM scans WHERE user_id = $1', [userId]);
  await query(
    `DELETE FROM prescription_plan_logs
     WHERE plan_id IN (SELECT id FROM prescription_plans WHERE user_id = $1)`,
    [userId]
  );
  await query(
    `DELETE FROM prescription_plan_slot_drugs
     WHERE slot_id IN (
       SELECT s.id
       FROM prescription_plan_slots s
       JOIN prescription_plans p ON p.id = s.plan_id
       WHERE p.user_id = $1
     )`,
    [userId]
  );
  await query(
    `DELETE FROM prescription_plan_slots
     WHERE plan_id IN (SELECT id FROM prescription_plans WHERE user_id = $1)`,
    [userId]
  );
  await query(
    `DELETE FROM prescription_plan_drugs
     WHERE plan_id IN (SELECT id FROM prescription_plans WHERE user_id = $1)`,
    [userId]
  );
  await query('DELETE FROM prescription_plans WHERE user_id = $1', [userId]);
}

function planPayload(drugName, dosage = '500mg') {
  return {
    title: 'Kế hoạch đang dùng',
    drugs: [{ id: 'drug-0', drugName, dosage, sortOrder: 0 }],
    slots: [{
      id: 'slot-0',
      time: '08:00',
      sortOrder: 0,
      items: [{ drugId: 'drug-0', drugName, dosage, pills: 1 }],
    }],
    startDate: '2026-03-10',
    totalDays: 7,
  };
}

function buildMedication({ ocrText, drugName, mappedDrugName = null }) {
  return {
    ocr_text: ocrText,
    drug_name: drugName,
    mapped_drug_name: mappedDrugName,
    mapping_status: 'confirmed',
    confidence: 0.94,
    match_score: 0.9,
    bbox: [1, 2, 20, 30],
  };
}

async function insertScan(result, scannedAt = '2026-03-10T08:00:00Z') {
  const inserted = await query(
    `INSERT INTO scans (user_id, result, drug_count, quality_state, scanned_at)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING id`,
    [
      userId,
      JSON.stringify(result),
      result.medication_candidates?.length || 0,
      result.quality_state || 'GOOD',
      scannedAt,
    ]
  );
  return inserted.rows[0].id;
}

function mockMetadata(profiles) {
  global.fetch = jest.fn(async (url) => {
    const rawName = decodeURIComponent(String(url).split('/api/drug-metadata/')[1] || '');
    const profile = profiles[rawName] || profiles[rawName.toLowerCase()];
    if (!profile) {
      return { ok: false, json: async () => ({}) };
    }
    return { ok: true, json: async () => profile };
  });
}

beforeAll(async () => {
  await ensureSchema();
  await cleanTestUsers(PREFIX);

  const user = await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Reconciliation Route Test',
  });
  userId = user.id;

  const tokens = await authService.login({
    email: EMAIL,
    password: 'Test1234!',
  });
  accessToken = tokens.accessToken;
});

beforeEach(async () => {
  clearReconciliationCachesForTests();
  await clearUserData();
  global.fetch = jest.fn();
});

afterAll(async () => {
  await clearUserData();
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('POST /api/reconciliation/scan-vs-active-plan', () => {
  test('returns structured diff and transition safety payload', async () => {
    await planService.createPlan(userId, planPayload('Panadol Extra'));
    const scanId = await insertScan({
      medications: [buildMedication({
        ocrText: 'Paracetamol STADA 500mg',
        drugName: 'Paracetamol STADA',
        mappedDrugName: 'Paracetamol STADA',
      })],
      medication_candidates: [buildMedication({
        ocrText: 'Paracetamol STADA 500mg',
        drugName: 'Paracetamol STADA',
        mappedDrugName: 'Paracetamol STADA',
      })],
      quality_state: 'GOOD',
      rejected: false,
    });

    mockMetadata({
      'Panadol Extra': {
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
        dosageForm: 'Viên nén',
        manufacturer: 'DHG',
        packaging: 'Hộp 10 vỉ',
        sources: ['ddi_vn'],
        identifiers: {},
      },
      'Paracetamol STADA': {
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
        dosageForm: 'Viên nén',
        manufacturer: 'STADA',
        packaging: 'Hộp 10 vỉ',
        sources: ['ddi_vn'],
        identifiers: {},
      },
    });

    const res = await request(app)
      .post('/api/reconciliation/scan-vs-active-plan')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ scanId });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.diff.possible_substitutions).toHaveLength(1);
    expect(Array.isArray(res.body.data.transitionOfCare.riskCards)).toBe(true);
  });
});

describe('POST /api/reconciliation/dispensed-text-vs-active-plan', () => {
  test('accepts text-first package items and compares them to active plan', async () => {
    await planService.createPlan(userId, planPayload('Panadol Extra'));

    mockMetadata({
      'Panadol Extra': {
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
        dosageForm: 'Viên nén',
        manufacturer: 'DHG',
        packaging: 'Hộp 10 vỉ',
        sources: ['ddi_vn'],
        identifiers: {},
      },
      'Paracetamol STADA 500mg': {
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
        dosageForm: 'Viên nén',
        manufacturer: 'STADA',
        packaging: 'Hộp 10 vỉ',
        sources: ['ddi_vn'],
        identifiers: {},
      },
    });

    const res = await request(app)
      .post('/api/reconciliation/dispensed-text-vs-active-plan')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        packagingType: 'box',
        items: [
          {
            rawName: 'Paracetamol STADA 500mg',
            ocrText: 'Paracetamol STADA 500mg',
            mappingStatus: 'confirmed',
            confidence: 0.96,
          },
        ],
      });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.compareType).toBe('dispensed_text_vs_active_plan');
    expect(res.body.data.diff.possible_substitutions).toHaveLength(1);
  });
});
