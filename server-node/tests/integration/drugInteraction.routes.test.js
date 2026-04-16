/**
 * Integration tests — drug interaction routes (/api/drug-interactions/*)
 */
import { jest } from '@jest/globals';
import request from 'supertest';
import app from '../../src/app.js';
import { cleanTestUsers, pool } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';

const PREFIX = 'test_ci_route_drug_interaction_';
const EMAIL = `${PREFIX}user@example.com`;

let accessToken;

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data),
  };
}

beforeAll(async () => {
  await cleanTestUsers(PREFIX);
  await authService.register({
    email: EMAIL,
    password: 'Test1234!',
    name: 'Drug Interaction Route Test',
  });
  const tokens = await authService.login({
    email: EMAIL,
    password: 'Test1234!',
  });
  accessToken = tokens.accessToken;
});

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.resetAllMocks();
});

afterAll(async () => {
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('POST /api/drug-interactions/check-by-drugs', () => {
  test('200: returns normalized interactions', async () => {
    global.fetch.mockResolvedValue(
      jsonResponse([
        {
          TenThuoc_1: 'Warfarin',
          TenThuoc_2: 'Aspirin',
          HoatChat_1: 'Warfarin',
          HoatChat_2: 'Aspirin',
          MucDoNghiemTrong: 'Nghiêm trọng',
          CanhBaoTuongTacThuoc: 'Tăng nguy cơ chảy máu',
        },
      ])
    );

    const res = await request(app)
      .post('/api/drug-interactions/check-by-drugs')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ drugNames: ['Warfarin', 'Aspirin'] });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.hasInteractions).toBe(true);
    expect(res.body.data.interactions[0].severity).toBe('major');
    expect(res.body.data.totalInteractions).toBe(1);
    expect(res.body.data.requestedDrugNames).toEqual(['Warfarin', 'Aspirin']);
  });

  test('200: de-duplicates same drug names', async () => {
    global.fetch.mockResolvedValue(jsonResponse([]));

    const res = await request(app)
      .post('/api/drug-interactions/check-by-drugs')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ drugNames: ['Warfarin', 'warfarin', 'Aspirin'] });

    expect(res.status).toBe(200);
    expect(res.body.data.requestedDrugNames).toEqual(['Warfarin', 'Aspirin']);
  });

  test('400: validation rejects only one drug', async () => {
    const res = await request(app)
      .post('/api/drug-interactions/check-by-drugs')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ drugNames: ['Warfarin'] });

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });

  test('401: no auth token', async () => {
    const res = await request(app)
      .post('/api/drug-interactions/check-by-drugs')
      .send({ drugNames: ['Warfarin', 'Aspirin'] });

    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe('AUTH_REQUIRED');
  });
});

describe('GET /api/drug-interactions/search-active-ingredients', () => {
  test('200: returns suggestions', async () => {
    global.fetch.mockResolvedValue(
      jsonResponse([
        { activeIngredient: 'Paracetamol' },
        { activeIngredient: 'Ibuprofen' },
      ])
    );

    const res = await request(app)
      .get('/api/drug-interactions/search-active-ingredients?keyword=para')
      .set('Authorization', `Bearer ${accessToken}`);

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.suggestions[0].name).toBe('Paracetamol');
  });
});

describe('POST /api/drug-interactions/check-by-active-ingredients', () => {
  test('200: supports grouped response', async () => {
    global.fetch.mockResolvedValue(
      jsonResponse({
        message: 'Tìm thấy 2 tương tác',
        interactions: {
          'Chống chỉ định': [
            {
              hoatChat1: 'MAOI',
              hoatChat2: 'Linezolid',
              canhBao: 'Không phối hợp',
            },
          ],
          'Trung bình': [
            {
              hoatChat1: 'Paracetamol',
              hoatChat2: 'Warfarin',
              canhBao: 'Theo dõi INR',
            },
          ],
        },
      })
    );

    const res = await request(app)
      .post('/api/drug-interactions/check-by-active-ingredients')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ activeIngredients: ['MAOI', 'Linezolid', 'Paracetamol', 'Warfarin'] });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.highestSeverity).toBe('contraindicated');
    expect(res.body.data.groups.length).toBe(2);
    expect(res.body.data.requestedActiveIngredients.length).toBe(4);
  });

  test('400: rejects payload with < 2 unique active ingredients', async () => {
    const res = await request(app)
      .post('/api/drug-interactions/check-by-active-ingredients')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({ activeIngredients: ['Paracetamol', 'paracetamol'] });

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });
});

describe('GET /api/drug-interactions/by-active-ingredient', () => {
  test('200: returns interaction list for one ingredient', async () => {
    global.fetch.mockResolvedValue(
      jsonResponse({
        message: 'Tìm thấy 1 tương tác',
        interactions: {
          'Không xác định': [
            {
              hoatChat1: 'Levocetirizine',
              hoatChat2: 'Theophylline',
              canhBao: 'Giảm nhẹ độ thanh thải',
            },
          ],
        },
      })
    );

    const res = await request(app)
      .get('/api/drug-interactions/by-active-ingredient?ingredientName=Levocetirizine')
      .set('Authorization', `Bearer ${accessToken}`);

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.totalInteractions).toBe(1);
    expect(res.body.data.interactions[0].ingredientA).toBe('Levocetirizine');
  });
});

describe('upstream errors', () => {
  test('503: upstream 500 returns service error', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'upstream failed',
    });

    const res = await request(app)
      .get('/api/drug-interactions/by-active-ingredient?ingredientName=Paracetamol')
      .set('Authorization', `Bearer ${accessToken}`);

    expect(res.status).toBe(503);
    expect(res.body.error.code).toBe('INTERACTION_SERVICE_ERROR');
  });
});
