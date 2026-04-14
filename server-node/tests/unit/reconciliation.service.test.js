import { jest } from '@jest/globals';

import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';
import * as planService from '../../src/services/plan.service.js';
import {
  clearReconciliationCachesForTests,
  compareDispensedTextToActivePlan,
  compareScanToActivePlan,
  compareScanToPreviousScan,
} from '../../src/services/reconciliation.service.js';

const PREFIX = 'test_ci_reconciliation_';
const EMAIL = `${PREFIX}user@example.com`;

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

function planPayload(drugs, title = 'Kế hoạch đang dùng') {
  return {
    title,
    drugs: drugs.map((drug, index) => ({
      id: `drug-${index}`,
      drugName: drug.drugName,
      dosage: drug.dosage || '',
      sortOrder: index,
    })),
    slots: [
      {
        id: 'slot-0',
        time: '08:00',
        sortOrder: 0,
        items: drugs.map((drug, index) => ({
          drugId: `drug-${index}`,
          drugName: drug.drugName,
          dosage: drug.dosage || '',
          pills: 1,
        })),
      },
    ],
    startDate: '2026-03-10',
    totalDays: 7,
  };
}

function buildMedication({
  ocrText,
  drugName,
  mappedDrugName = null,
  mappingStatus = 'confirmed',
  confidence = 0.93,
  matchScore = 0.9,
}) {
  return {
    ocr_text: ocrText,
    drug_name: drugName,
    mapped_drug_name: mappedDrugName,
    mapping_status: mappingStatus,
    confidence,
    match_score: matchScore,
    bbox: [1, 2, 30, 40],
  };
}

function buildScanResult(drugs, qualityState = 'GOOD') {
  return {
    medications: drugs,
    medication_candidates: drugs,
    quality_state: qualityState,
    rejected: false,
    guidance: qualityState === 'GOOD' ? null : 'Ảnh cần kiểm tra lại',
  };
}

async function insertScan(userIdValue, result, scannedAt) {
  const inserted = await query(
    `INSERT INTO scans (user_id, result, drug_count, quality_state, scanned_at)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING id`,
    [
      userIdValue,
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
      return {
        ok: false,
        json: async () => ({}),
      };
    }
    return {
      ok: true,
      json: async () => profile,
    };
  });
}

function metadata({
  displayName,
  activeIngredients,
  dosageForm = 'Viên nén',
  manufacturer = 'DHG Pharma',
  packaging = 'Hộp 10 vỉ',
}) {
  return {
    displayName,
    dosageForm,
    manufacturer,
    packaging,
    activeIngredients,
    sources: ['ddi_vn'],
    identifiers: {},
  };
}

beforeAll(async () => {
  await ensureSchema();
  await cleanTestUsers(PREFIX);
  const user = await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Reconciliation Test',
  });
  userId = user.id;
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

describe('compareScanToActivePlan()', () => {
  test('flags brand substitution using same active ingredient', async () => {
    await planService.createPlan(userId, planPayload([
      { drugName: 'Panadol Extra', dosage: '500mg' },
    ]));

    const scanId = await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Paracetamol STADA 500mg',
        drugName: 'Paracetamol STADA',
        mappedDrugName: 'Paracetamol STADA',
      }),
    ]), '2026-03-10T08:00:00Z');

    mockMetadata({
      'Panadol Extra': metadata({
        displayName: 'Panadol Extra',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
      'Paracetamol STADA': metadata({
        displayName: 'Paracetamol STADA',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
    });

    const result = await compareScanToActivePlan(userId, scanId);

    expect(result.diff.possible_substitutions).toHaveLength(1);
    expect(result.diff.added_medications).toHaveLength(0);
    expect(result.diff.removed_medications).toHaveLength(0);
    expect(result.transitionOfCare.riskCards.some((card) => card.label === 'Có thể đổi thuốc')).toBe(true);
  });

  test('returns added and removed medications as structured diff', async () => {
    await planService.createPlan(userId, planPayload([
      { drugName: 'Paracetamol', dosage: '500mg' },
      { drugName: 'Amoxicillin', dosage: '500mg' },
    ]));

    const scanId = await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Paracetamol 500mg',
        drugName: 'Paracetamol',
        mappedDrugName: 'Paracetamol',
      }),
      buildMedication({
        ocrText: 'Vitamin C 500mg',
        drugName: 'Vitamin C',
        mappedDrugName: 'Vitamin C',
      }),
    ]), '2026-03-10T08:00:00Z');

    mockMetadata({
      Paracetamol: metadata({
        displayName: 'Paracetamol',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
      Amoxicillin: metadata({
        displayName: 'Amoxicillin',
        activeIngredients: [{ name: 'Amoxicillin', strength: '500mg', source: 'ddi_vn' }],
      }),
      'Vitamin C': metadata({
        displayName: 'Vitamin C',
        activeIngredients: [{ name: 'Ascorbic Acid', strength: '500mg', source: 'ddi_vn' }],
      }),
    });

    const result = await compareScanToActivePlan(userId, scanId);

    expect(result.diff.added_medications).toHaveLength(1);
    expect(result.diff.added_medications[0].matchedDrugName).toBe('Vitamin C');
    expect(result.diff.removed_medications).toHaveLength(1);
    expect(result.diff.removed_medications[0].matchedDrugName).toBe('Amoxicillin');
  });

  test('flags strength mismatch and duplicate active ingredients', async () => {
    await planService.createPlan(userId, planPayload([
      { drugName: 'Paracetamol', dosage: '500mg' },
    ]));

    const scanId = await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Paracetamol 650mg',
        drugName: 'Paracetamol',
        mappedDrugName: 'Paracetamol',
      }),
      buildMedication({
        ocrText: 'Panadol 650mg',
        drugName: 'Panadol',
        mappedDrugName: 'Panadol',
      }),
    ]), '2026-03-10T08:00:00Z');

    mockMetadata({
      Paracetamol: metadata({
        displayName: 'Paracetamol',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
      Panadol: metadata({
        displayName: 'Panadol',
        activeIngredients: [{ name: 'Paracetamol', strength: '650mg', source: 'ddi_vn' }],
      }),
    });

    const result = await compareScanToActivePlan(userId, scanId);

    expect(result.diff.strength_changed.length).toBeGreaterThan(0);
    expect(result.diff.duplicate_active_ingredients).toHaveLength(1);
    expect(result.diff.duplicate_active_ingredients[0].ingredient).toBe('Paracetamol');
  });

  test('sends low-confidence OCR items to manual review instead of auto-adding', async () => {
    const scanId = await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Mys tery Cap',
        drugName: 'Mys tery Cap',
        mappingStatus: 'unmapped_candidate',
        confidence: 0.54,
      }),
    ], 'WARNING'), '2026-03-10T08:00:00Z');

    mockMetadata({});

    const result = await compareScanToActivePlan(userId, scanId);

    expect(result.diff.added_medications).toHaveLength(0);
    expect(result.diff.needs_manual_review).toHaveLength(1);
    expect(result.summary.requiresManualReview).toBe(true);
  });
});

describe('compareScanToPreviousScan()', () => {
  test('uses the nearest previous scan when previousScanId is omitted', async () => {
    mockMetadata({
      Paracetamol: metadata({
        displayName: 'Paracetamol',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
      'Vitamin C': metadata({
        displayName: 'Vitamin C',
        activeIngredients: [{ name: 'Ascorbic Acid', strength: '500mg', source: 'ddi_vn' }],
      }),
    });

    await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Paracetamol 500mg',
        drugName: 'Paracetamol',
        mappedDrugName: 'Paracetamol',
      }),
    ]), '2026-03-10T08:00:00Z');

    const currentScanId = await insertScan(userId, buildScanResult([
      buildMedication({
        ocrText: 'Paracetamol 500mg',
        drugName: 'Paracetamol',
        mappedDrugName: 'Paracetamol',
      }),
      buildMedication({
        ocrText: 'Vitamin C 500mg',
        drugName: 'Vitamin C',
        mappedDrugName: 'Vitamin C',
      }),
    ]), '2026-03-11T08:00:00Z');

    const result = await compareScanToPreviousScan(userId, currentScanId);

    expect(result.compareType).toBe('scan_vs_previous_scan');
    expect(result.diff.added_medications).toHaveLength(1);
    expect(result.diff.added_medications[0].matchedDrugName).toBe('Vitamin C');
  });
});

describe('compareDispensedTextToActivePlan()', () => {
  test('supports text-first package comparison without loose-pill logic', async () => {
    await planService.createPlan(userId, planPayload([
      { drugName: 'Panadol Extra', dosage: '500mg' },
    ]));

    mockMetadata({
      'Panadol Extra': metadata({
        displayName: 'Panadol Extra',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
      'Paracetamol STADA 500mg': metadata({
        displayName: 'Paracetamol STADA',
        activeIngredients: [{ name: 'Paracetamol', strength: '500mg', source: 'ddi_vn' }],
      }),
    });

    const result = await compareDispensedTextToActivePlan(userId, {
      sourceRef: 'package-batch-1',
      packagingType: 'box',
      items: [
        {
          ocrText: 'Paracetamol STADA 500mg',
          rawName: 'Paracetamol STADA 500mg',
          mappingStatus: 'confirmed',
          confidence: 0.97,
        },
      ],
    });

    expect(result.compareType).toBe('dispensed_text_vs_active_plan');
    expect(result.diff.possible_substitutions).toHaveLength(1);
    expect(result.candidate.sourceType).toBe('dispensed_text');
  });
});
