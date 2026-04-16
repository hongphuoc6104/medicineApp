/**
 * Unit tests — drugInteraction.service.js
 */
import { jest } from '@jest/globals';
import * as drugInteractionService from '../../src/services/drugInteraction.service.js';

function mockJsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data),
  };
}

describe('drugInteraction.service', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test('searchActiveIngredients() normalizes suggestions', async () => {
    global.fetch.mockResolvedValue(
      mockJsonResponse([
        { activeIngredient: 'Paracetamol' },
        { activeIngredient: 'Ibuprofen' },
        { activeIngredient: 'Paracetamol' },
      ])
    );

    const result = await drugInteractionService.searchActiveIngredients('para');

    expect(result.keyword).toBe('para');
    expect(result.suggestions).toEqual([
      { name: 'Paracetamol' },
      { name: 'Ibuprofen' },
    ]);
  });

  test('checkByDrugNames() maps severity and summary', async () => {
    global.fetch.mockResolvedValue(
      mockJsonResponse([
        {
          TenThuoc_1: 'Warfarin',
          TenThuoc_2: 'Aspirin',
          HoatChat_1: 'Warfarin',
          HoatChat_2: 'Aspirin',
          MucDoNghiemTrong: 'Nghiêm trọng',
          CanhBaoTuongTacThuoc: 'Tăng nguy cơ chảy máu',
        },
        {
          TenThuoc_1: 'Paracetamol',
          TenThuoc_2: 'Caffeine',
          HoatChat_1: 'Paracetamol',
          HoatChat_2: 'Caffeine',
          MucDoNghiemTrong: 'Nhẹ',
          CanhBaoTuongTacThuoc: 'Theo dõi liều dùng',
        },
      ])
    );

    const result = await drugInteractionService.checkByDrugNames([
      'Warfarin',
      'Aspirin',
      'Paracetamol',
      'Caffeine',
    ]);

    expect(result.hasInteractions).toBe(true);
    expect(result.totalInteractions).toBe(2);
    expect(result.highestSeverity).toBe('major');
    expect(result.requestedDrugNames).toEqual([
      'Warfarin',
      'Aspirin',
      'Paracetamol',
      'Caffeine',
    ]);
    expect(result.severitySummary.major).toBe(1);
    expect(result.severitySummary.minor).toBe(1);
    expect(result.interactions[0].severity).toBe('major');
    expect(result.interactions[0].warning).toContain('chảy máu');
  });

  test('checkByDrugNames() accepts wrapped data payload', async () => {
    global.fetch.mockResolvedValue(
      mockJsonResponse({
        data: {
          interactions: [
            {
              TenThuoc_1: 'Warfarin',
              TenThuoc_2: 'Aspirin',
              MucDoNghiemTrong: 'Nghiêm trọng',
            },
          ],
        },
      })
    );

    const result = await drugInteractionService.checkByDrugNames([
      'Warfarin',
      'Aspirin',
    ]);

    expect(result.totalInteractions).toBe(1);
    expect(result.highestSeverity).toBe('major');
  });

  test('checkByDrugNames() de-duplicates input names', async () => {
    global.fetch.mockResolvedValue(mockJsonResponse([]));

    const result = await drugInteractionService.checkByDrugNames([
      'Warfarin',
      'warfarin',
      'Aspirin',
      'Aspirin',
    ]);

    expect(result.requestedDrugNames).toEqual(['Warfarin', 'Aspirin']);
    expect(result.totalInteractions).toBe(0);
    expect(result.message).toContain('Không phát hiện tương tác');
  });

  test('checkByDrugNames() rejects when unique drug count is below 2', async () => {
    await expect(
      drugInteractionService.checkByDrugNames(['Warfarin', 'warfarin'])
    ).rejects.toMatchObject({ statusCode: 400, code: 'VALIDATION_ERROR' });
  });

  test('checkByActiveIngredients() supports grouped payload', async () => {
    global.fetch.mockResolvedValue(
      mockJsonResponse({
        message: 'Tìm thấy tương tác',
        interactions: {
          'Chống chỉ định': [
            {
              hoatChat1: 'MAOI',
              hoatChat2: 'Linezolid',
              canhBao: 'Không dùng chung',
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

    const result = await drugInteractionService.checkByActiveIngredients([
      'MAOI',
      'Linezolid',
      'Paracetamol',
      'Warfarin',
    ]);

    expect(result.totalInteractions).toBe(2);
    expect(result.highestSeverity).toBe('contraindicated');
    expect(result.requestedActiveIngredients).toEqual([
      'MAOI',
      'Linezolid',
      'Paracetamol',
      'Warfarin',
    ]);
    expect(result.groups[0].severity).toBe('contraindicated');
    expect(result.groups[0].count).toBe(1);
    expect(result.groups[1].severity).toBe('moderate');
  });

  test('checkByActiveIngredients() rejects when unique ingredient count is below 2', async () => {
    await expect(
      drugInteractionService.checkByActiveIngredients(['Paracetamol', 'paracetamol'])
    ).rejects.toMatchObject({ statusCode: 400, code: 'VALIDATION_ERROR' });
  });

  test('throws timeout error when upstream aborts', async () => {
    const abortError = new Error('aborted');
    abortError.name = 'AbortError';
    global.fetch.mockRejectedValue(abortError);

    await expect(
      drugInteractionService.checkByDrugNames(['Aspirin', 'Warfarin'])
    ).rejects.toMatchObject({ statusCode: 504, code: 'INTERACTION_TIMEOUT' });
  });

  test('throws service unavailable on upstream 500', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'upstream failed',
    });

    await expect(
      drugInteractionService.getInteractionsByActiveIngredient('paracetamol')
    ).rejects.toMatchObject({
      statusCode: 503,
      code: 'INTERACTION_SERVICE_ERROR',
    });
  });
});
