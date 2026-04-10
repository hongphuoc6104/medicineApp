import request from 'supertest';

import app from '../../src/app.js';
import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';

const PREFIX = 'test_ci_route_pill_ref_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;
let userId;
let planId;

const tinyPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7YtF4AAAAASUVORK5CYII=',
  'base64'
);

async function ensurePhaseBSchema() {
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
}

beforeAll(async () => {
  await ensurePhaseBSchema();
  await cleanTestUsers(PREFIX);

  const user = await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Pill Reference Test',
  });
  userId = user.id;

  const tokens = await authService.login({
    email: EMAIL,
    password: 'Test1234!',
  });
  accessToken = tokens.accessToken;

  const plan = await query(
    `INSERT INTO medication_plans
       (user_id, drug_name, dosage, frequency, times, pills_per_dose,
        total_days, start_date, notes)
     VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
     RETURNING id`,
    [
      userId,
      'Paracetamol 500mg',
      '500mg',
      'daily',
      JSON.stringify(['08:00']),
      1,
      10,
      '2026-03-20',
      null,
    ]
  );
  planId = plan.rows[0].id;
});

beforeEach(async () => {
  await query(
    `DELETE FROM pill_reference_images
     WHERE reference_set_id IN (
       SELECT id FROM pill_reference_sets WHERE user_id = $1
     )`,
    [userId]
  );
  await query('DELETE FROM pill_reference_sets WHERE user_id = $1', [userId]);
});

afterAll(async () => {
  await query(
    `DELETE FROM pill_reference_images
     WHERE reference_set_id IN (
       SELECT id FROM pill_reference_sets WHERE user_id = $1
     )`,
    [userId]
  );
  await query('DELETE FROM pill_reference_sets WHERE user_id = $1', [userId]);
  await query('DELETE FROM medication_plans WHERE user_id = $1', [userId]);
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('pill reference enrollment flow', () => {
  test('start -> upload frame -> finalize -> list', async () => {
    const started = await request(app)
      .post('/api/pill-references/enroll/start')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        planId,
        drugNameSnapshot: 'Paracetamol 500mg',
      });

    expect(started.status).toBe(201);
    expect(started.body.data.planId).toBe(planId);
    const referenceSetId = started.body.data.id;

    const uploaded = await request(app)
      .post(`/api/pill-references/${referenceSetId}/frame`)
      .set('Authorization', `Bearer ${accessToken}`)
      .field('side', 'front')
      .attach('file', tinyPng, {
        filename: 'pill.png',
        contentType: 'image/png',
      });

    expect(uploaded.status).toBe(200);
    expect(uploaded.body.data.imageCount).toBe(1);
    expect(uploaded.body.data.images[0].side).toBe('front');
    expect(uploaded.body.data.images[0].imagePath).toContain('storage/pill-references');

    const finalized = await request(app)
      .post(`/api/pill-references/${referenceSetId}/finalize`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({});

    expect(finalized.status).toBe(200);
    expect(finalized.body.data.status).toBe('ready');
    expect(finalized.body.data.images[0].confirmedByUser).toBe(true);

    const listed = await request(app)
      .get('/api/pill-references')
      .set('Authorization', `Bearer ${accessToken}`)
      .query({ planId });

    expect(listed.status).toBe(200);
    expect(Array.isArray(listed.body.data)).toBe(true);
    expect(listed.body.data).toHaveLength(1);
    expect(listed.body.data[0].status).toBe('ready');
    expect(listed.body.data[0].images[0].confirmedByUser).toBe(true);
  });
});
