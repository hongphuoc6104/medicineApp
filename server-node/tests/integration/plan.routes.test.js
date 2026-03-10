/**
 * Integration tests — Plan routes (CRUD /api/plans)
 */
import request from 'supertest';
import app from '../../src/app.js';
import { cleanTestUsers, pool } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';

const PREFIX = 'test_ci_route_plan_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;
let planId;

beforeAll(async () => {
  await cleanTestUsers(PREFIX);
  await authService.register({ email: EMAIL, password: 'Test1234!', name: 'Plan Route Test' });
  const tokens = await authService.login({ email: EMAIL, password: 'Test1234!' });
  accessToken = tokens.accessToken;
});

afterAll(async () => {
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('POST /api/plans', () => {
  test('201: create valid plan', async () => {
    const res = await request(app)
      .post('/api/plans')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        drugName: 'Paracetamol 500mg',
        frequency: 'twice_daily',
        times: ['08:00', '20:00'],
        startDate: '2026-03-10',
        totalDays: 7,
        notes: 'Uống sau ăn',
      });
    expect(res.status).toBe(201);
    expect(res.body.data.drug_name).toBe('Paracetamol 500mg');
    expect(res.body.data.is_active).toBe(true);
    planId = res.body.data.id;
  });

  test('400: invalid frequency', async () => {
    const res = await request(app)
      .post('/api/plans')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        drugName: 'Test Drug',
        frequency: 'every_hour', // invalid
        times: ['08:00'],
        startDate: '2026-03-10',
      });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });

  test('400: invalid time format', async () => {
    const res = await request(app)
      .post('/api/plans')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        drugName: 'Test Drug',
        frequency: 'daily',
        times: ['8am'], // invalid format
        startDate: '2026-03-10',
      });
    expect(res.status).toBe(400);
  });

  test('401: no auth', async () => {
    const res = await request(app).post('/api/plans').send({
      drugName: 'Test',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    expect(res.status).toBe(401);
  });
});

describe('GET /api/plans', () => {
  test('200: returns paginated active plans', async () => {
    const res = await request(app)
      .get('/api/plans')
      .set('Authorization', `Bearer ${accessToken}`);
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.pagination).toBeDefined();
    expect(Array.isArray(res.body.data)).toBe(true);
  });

  test('200: active=false returns all plans', async () => {
    const res = await request(app)
      .get('/api/plans?active=false')
      .set('Authorization', `Bearer ${accessToken}`);
    expect(res.status).toBe(200);
  });
});

describe('PUT /api/plans/:id', () => {
  test('200: update plan notes', async () => {
    const res = await request(app)
      .put(`/api/plans/${planId}`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ notes: 'Updated note' });
    expect(res.status).toBe(200);
    expect(res.body.data.notes).toBe('Updated note');
  });

  test('404: plan not found for update', async () => {
    const res = await request(app)
      .put('/api/plans/00000000-0000-0000-0000-000000000000')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ notes: 'hack' });
    expect(res.status).toBe(404);
  });
});

describe('POST /api/plans/:id/log', () => {
  test('201: log medication as taken', async () => {
    const res = await request(app)
      .post(`/api/plans/${planId}/log`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        scheduledTime: '2026-03-10T08:00:00.000Z',
        status: 'taken',
      });
    expect(res.status).toBe(201);
    expect(res.body.data.status).toBe('taken');
    expect(res.body.data.taken_at).not.toBeNull();
  });

  test('400: invalid status', async () => {
    const res = await request(app)
      .post(`/api/plans/${planId}/log`)
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        scheduledTime: '2026-03-10T08:00:00.000Z',
        status: 'forgot', // invalid
      });
    expect(res.status).toBe(400);
  });
});

describe('DELETE /api/plans/:id', () => {
  test('200: soft delete plan', async () => {
    const res = await request(app)
      .delete(`/api/plans/${planId}`)
      .set('Authorization', `Bearer ${accessToken}`);
    expect(res.status).toBe(200);

    // Deleted plan should not appear in active list
    const listRes = await request(app)
      .get('/api/plans')
      .set('Authorization', `Bearer ${accessToken}`);
    const ids = listRes.body.data.map(p => p.id);
    expect(ids).not.toContain(planId);
  });
});
