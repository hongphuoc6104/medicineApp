import { jest } from '@jest/globals';
import request from 'supertest';

import app from '../../src/app.js';
import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';

const PREFIX = 'test_ci_route_pill_verify_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;
let userId;

const tinyPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7YtF4AAAAASUVORK5CYII=',
  'base64'
);

async function ensureSchema() {
  await query(`CREATE TABLE IF NOT EXISTS pill_verification_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    occurrence_id VARCHAR(120) NOT NULL,
    dose_payload JSONB NOT NULL,
    result JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
  )`);
  await query(`CREATE TABLE IF NOT EXISTS pill_verification_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES pill_verification_sessions(id) ON DELETE CASCADE,
    detection_idx INTEGER NOT NULL,
    assigned_drug_name VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'assigned',
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, detection_idx)
  )`);
}

beforeAll(async () => {
  await ensureSchema();
  await cleanTestUsers(PREFIX);

  const user = await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Pill Verify Test',
  });
  userId = user.id;

  const tokens = await authService.login({
    email: EMAIL,
    password: 'Test1234!',
  });
  accessToken = tokens.accessToken;
});

beforeEach(async () => {
  global.fetch = jest.fn();
  await query(
    `DELETE FROM pill_verification_assignments
     WHERE session_id IN (SELECT id FROM pill_verification_sessions WHERE user_id = $1)`,
    [userId]
  );
  await query('DELETE FROM pill_verification_sessions WHERE user_id = $1', [userId]);
});

afterAll(async () => {
  await query(
    `DELETE FROM pill_verification_assignments
     WHERE session_id IN (SELECT id FROM pill_verification_sessions WHERE user_id = $1)`,
    [userId]
  );
  await query('DELETE FROM pill_verification_sessions WHERE user_id = $1', [userId]);
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('pill verification flow', () => {
  test('start -> upload -> assign -> confirm', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        detections: [{ bbox: [1, 2, 10, 12], score: 0.94, label: 1 }],
        drug_blocks: [{ idx: 0, text: 'Paracetamol' }],
        note: 'Detection only',
      }),
    });

    const started = await request(app)
      .post('/api/pill-verifications/start')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        occurrenceId: 'plan-1:2026-03-20:07:00',
        planId: 'plan-1',
        scheduledTime: '2026-03-20T07:00:00.000Z',
        expectedMedications: [{ drugName: 'Paracetamol', pillsPerDose: 1 }],
      });

    expect(started.status).toBe(201);
    const sessionId = started.body.data.sessionId;

    const uploaded = await request(app)
      .post(`/api/pill-verifications/${sessionId}/image`)
      .set('Authorization', `Bearer ${accessToken}`)
      .attach('file', tinyPng, {
        filename: 'pills.png',
        contentType: 'image/png',
      });
    expect(uploaded.status).toBe(200);
    expect(uploaded.body.data.detections.length).toBe(1);

    const assigned = await request(app)
      .post(`/api/pill-verifications/${sessionId}/assign`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        detectionIdx: 0,
        assignedDrugName: 'Paracetamol',
        status: 'assigned',
      });
    expect(assigned.status).toBe(200);
    expect(assigned.body.data.summary.assigned).toBe(1);

    const confirmed = await request(app)
      .post(`/api/pill-verifications/${sessionId}/confirm`)
      .set('Authorization', `Bearer ${accessToken}`);
    expect(confirmed.status).toBe(200);
    expect(confirmed.body.data.status).toBe('confirmed');
  });
});
