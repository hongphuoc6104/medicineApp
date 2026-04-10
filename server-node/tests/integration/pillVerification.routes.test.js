import { jest } from '@jest/globals';
import request from 'supertest';

import app from '../../src/app.js';
import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';

const PREFIX = 'test_ci_route_dose_verify_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;
let userId;
let planA;
let planB;
let referenceSetA;
let referenceSetB;

const tinyPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7YtF4AAAAASUVORK5CYII=',
  'base64'
);

async function ensureSchema() {
  await query(`CREATE TABLE IF NOT EXISTS pill_reference_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES medication_plans(id) ON DELETE CASCADE,
    drug_name_snapshot VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plan_id)
  )`);
  await query(`CREATE TABLE IF NOT EXISTS pill_reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_set_id UUID REFERENCES pill_reference_sets(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    side VARCHAR(20) DEFAULT 'front',
    quality_score NUMERIC(6,3),
    embedding JSONB,
    confirmed_by_user BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
  )`);
  await query(`CREATE TABLE IF NOT EXISTS dose_verification_sessions (
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
  )`);
  await query(`CREATE TABLE IF NOT EXISTS dose_verification_detections (
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
  )`);
  await query(`CREATE TABLE IF NOT EXISTS dose_verification_feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES dose_verification_sessions(id) ON DELETE CASCADE,
    detection_idx INTEGER,
    action VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
  )`);
}

beforeAll(async () => {
  await ensureSchema();
  await cleanTestUsers(PREFIX);

  const user = await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Dose Verification Test',
  });
  userId = user.id;

  const tokens = await authService.login({
    email: EMAIL,
    password: 'Test1234!',
  });
  accessToken = tokens.accessToken;

  const planRows = await query(
    `INSERT INTO medication_plans
       (user_id, drug_name, dosage, frequency, times, pills_per_dose,
        total_days, start_date, notes)
     VALUES
       ($1, 'Paracetamol', '500mg', 'daily', '["08:00"]'::jsonb, 2, 10, '2026-03-20', null),
       ($1, 'Vitamin C', '500mg', 'daily', '["08:00"]'::jsonb, 1, 10, '2026-03-20', null)
     RETURNING id, drug_name`,
    [userId]
  );

  const planMap = new Map(planRows.rows.map((row) => [row.drug_name, row.id]));
  planA = planMap.get('Paracetamol');
  planB = planMap.get('Vitamin C');

  referenceSetA = await query(
    `INSERT INTO pill_reference_sets (user_id, plan_id, drug_name_snapshot, status)
     VALUES ($1, $2, 'Paracetamol', 'ready')
     RETURNING id`,
    [userId, planA]
  );
  referenceSetB = await query(
    `INSERT INTO pill_reference_sets (user_id, plan_id, drug_name_snapshot, status)
     VALUES ($1, $2, 'Vitamin C', 'ready')
     RETURNING id`,
    [userId, planB]
  );

  await query(
    `INSERT INTO pill_reference_images
       (reference_set_id, image_path, side, quality_score, confirmed_by_user)
     VALUES
       ($1, '/tmp/paracetamol.jpg', 'front', 0.95, true),
       ($2, '/tmp/vitamin-c.jpg', 'front', 0.92, true)`,
    [referenceSetA.rows[0].id, referenceSetB.rows[0].id]
  );
});

beforeEach(async () => {
  global.fetch = jest.fn();
  await query('DELETE FROM dose_verification_feedback_events WHERE session_id IN (SELECT id FROM dose_verification_sessions WHERE user_id = $1)', [userId]);
  await query('DELETE FROM dose_verification_detections WHERE session_id IN (SELECT id FROM dose_verification_sessions WHERE user_id = $1)', [userId]);
  await query('DELETE FROM dose_verification_sessions WHERE user_id = $1', [userId]);
});

afterAll(async () => {
  await query('DELETE FROM dose_verification_feedback_events WHERE session_id IN (SELECT id FROM dose_verification_sessions WHERE user_id = $1)', [userId]);
  await query('DELETE FROM dose_verification_detections WHERE session_id IN (SELECT id FROM dose_verification_sessions WHERE user_id = $1)', [userId]);
  await query('DELETE FROM dose_verification_sessions WHERE user_id = $1', [userId]);
  await query('DELETE FROM pill_reference_images WHERE reference_set_id IN (SELECT id FROM pill_reference_sets WHERE user_id = $1)', [userId]);
  await query('DELETE FROM pill_reference_sets WHERE user_id = $1', [userId]);
  await query('DELETE FROM medication_plans WHERE user_id = $1', [userId]);
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('dose verification flow', () => {
  test('start -> upload -> assign -> confirm', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        mode: 'dose_verification',
        detections: [
          {
            detectionIdx: 0,
            bbox: [1, 2, 10, 12],
            score: 0.94,
            status: 'assigned',
            assignedPlanId: planA,
            assignedDrugName: 'Paracetamol',
            confidence: 0.91,
            suggestions: [
              { planId: planA, drugName: 'Paracetamol', score: 0.91 },
              { planId: planB, drugName: 'Vitamin C', score: 0.68 },
            ],
          },
          {
            detectionIdx: 1,
            bbox: [12, 15, 24, 28],
            score: 0.82,
            status: 'uncertain',
            assignedPlanId: null,
            assignedDrugName: null,
            confidence: 0.66,
            suggestions: [
              { planId: planB, drugName: 'Vitamin C', score: 0.66 },
            ],
          },
        ],
        summary: {
          totalDetections: 2,
          assigned: 1,
          uncertain: 1,
          unknown: 0,
          extra: 0,
          missingExpected: 2,
          perMedication: [],
        },
        referenceCoverage: {
          totalExpected: 2,
          withReference: 2,
          withoutReference: 0,
          missingPlanIds: [],
          missingDrugNames: [],
        },
        expectedMedications: [],
        missingReferences: [],
      }),
    });

    const started = await request(app)
      .post('/api/pill-verifications/start')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        occurrenceId: `${planA}:2026-03-20:08:00`,
        scheduledTime: '2026-03-20T08:00:00.000Z',
        expectedMedications: [
          { planId: planA, drugName: 'Paracetamol', pillsPerDose: 2 },
          { planId: planB, drugName: 'Vitamin C', pillsPerDose: 1 },
        ],
      });

    expect(started.status).toBe(201);
    const sessionId = started.body.data.sessionId;

    const uploaded = await request(app)
      .post(`/api/pill-verifications/${sessionId}/image`)
      .set('Authorization', `Bearer ${accessToken}`)
      .attach('file', tinyPng, {
        filename: 'dose.png',
        contentType: 'image/png',
      });

    expect(uploaded.status).toBe(200);
    expect(uploaded.body.data.summary.uncertain).toBe(1);
    expect(uploaded.body.data.referenceCoverage.withReference).toBe(2);

    const fetchCall = global.fetch.mock.calls[0];
    expect(fetchCall[0]).toContain('/api/dose-verification');
    const formData = fetchCall[1].body;
    expect(formData.get('prescription_json')).toBeNull();
    expect(formData.get('occurrence_id')).toBe(`${planA}:2026-03-20:08:00`);

    const assigned = await request(app)
      .post(`/api/pill-verifications/${sessionId}/assign`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        detectionIdx: 1,
        assignedPlanId: planB,
        assignedDrugName: 'Vitamin C',
        status: 'assigned',
      });

    expect(assigned.status).toBe(200);
    expect(assigned.body.data.summary.assigned).toBe(2);

    const feedbackRowsAfterAssign = await query(
      `SELECT action, detection_idx, payload
       FROM dose_verification_feedback_events
       WHERE session_id = $1
       ORDER BY created_at ASC`,
      [sessionId]
    );
    expect(feedbackRowsAfterAssign.rows).toHaveLength(1);
    expect(feedbackRowsAfterAssign.rows[0].action).toBe('manual_assignment');
    expect(feedbackRowsAfterAssign.rows[0].detection_idx).toBe(1);

    const invalidAssign = await request(app)
      .post(`/api/pill-verifications/${sessionId}/assign`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        detectionIdx: 0,
        status: 'assigned',
      });

    expect(invalidAssign.status).toBe(400);
    expect(invalidAssign.body.error.code).toBe('MISSING_ASSIGNED_DRUG');

    const confirmed = await request(app)
      .post(`/api/pill-verifications/${sessionId}/confirm`)
      .set('Authorization', `Bearer ${accessToken}`);

    expect(confirmed.status).toBe(200);
    expect(confirmed.body.data.status).toBe('confirmed');

    const feedbackRowsFinal = await query(
      `SELECT action
       FROM dose_verification_feedback_events
       WHERE session_id = $1
       ORDER BY created_at ASC`,
      [sessionId]
    );
    expect(feedbackRowsFinal.rows.map((row) => row.action)).toEqual([
      'manual_assignment',
      'confirm_session',
    ]);
  });
});
