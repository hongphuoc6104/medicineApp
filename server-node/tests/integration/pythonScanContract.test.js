import { jest } from '@jest/globals';

const queryMock = jest.fn();

jest.unstable_mockModule('../../src/config/database.js', () => ({
  query: queryMock,
}));
jest.unstable_mockModule('../../src/config/env.js', () => ({
  env: { PYTHON_API_URL: 'http://python.test' },
}));

const { scanPrescription } = await import('../../src/services/scan.service.js');

function upstreamResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(body),
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
  };
}

async function expectFailure(response, status, code) {
  global.fetch = jest.fn().mockResolvedValue(response);

  await expect(scanPrescription(
    Buffer.from('image'),
    'user-id',
    'prescription.jpg'
  )).rejects.toMatchObject({ statusCode: status, code });
  expect(queryMock).not.toHaveBeenCalled();
}

beforeEach(() => {
  queryMock.mockReset();
  global.fetch = jest.fn();
});

describe('Python scan failure contract', () => {
  test.each([
    [503, 'PIPELINE_UNAVAILABLE'],
    [500, 'PIPELINE_EXECUTION_FAILED'],
    [422, 'SCAN_PROCESSING_FAILED'],
  ])('preserves upstream HTTP %i and machine code %s', async (status, code) => {
    await expectFailure(upstreamResponse(status, {
      detail: { code, message: `upstream ${code}` },
    }), status, code);
  });

  test('retains timeout status and code without persistence', async () => {
    global.fetch.mockRejectedValue(Object.assign(new Error('aborted'), { name: 'AbortError' }));

    await expect(scanPrescription(
      Buffer.from('image'),
      'user-id',
      'prescription.jpg'
    )).rejects.toMatchObject({ statusCode: 504, code: 'SCAN_TIMEOUT' });
    expect(queryMock).not.toHaveBeenCalled();
  });

  test('rejects a legacy HTTP-200 mock payload before normalization or persistence', async () => {
    await expectFailure(upstreamResponse(200, {
      mock: true,
      medications: [{ drug_name: 'Mock-Paracetamol-500mg' }],
    }), 503, 'PIPELINE_UNAVAILABLE');
  });

  test('rejects a legacy HTTP-200 terminal error before normalization or persistence', async () => {
    await expectFailure(upstreamResponse(200, {
      error: 'No prescription region could be processed',
    }), 422, 'SCAN_PROCESSING_FAILED');
  });

  test('keeps the existing successful payload normalization and persists once', async () => {
    global.fetch.mockResolvedValue(upstreamResponse(200, {
      medications: [{
        drug_name: 'Paracetamol',
        ocr_text: 'Paracetamol 500mg',
        mapped_drug_name: 'Paracetamol',
        mapping_status: 'confirmed',
        confidence: 0.95,
        match_score: 0.91,
      }],
      quality_state: 'GOOD',
      quality_metrics: { blur_score: 100 },
      rejected: false,
    }));
    queryMock.mockResolvedValue({ rows: [] });

    const result = await scanPrescription(
      Buffer.from('image'),
      'user-id',
      'prescription.jpg'
    );

    expect(result.qualityState).toBe('GOOD');
    expect(result.drugs).toHaveLength(1);
    expect(result.drugs[0]).toMatchObject({
      name: 'Paracetamol',
      ocrText: 'Paracetamol 500mg',
      mappedDrugName: 'Paracetamol',
      mappingStatus: 'confirmed',
    });
    expect(queryMock).toHaveBeenCalledTimes(1);
  });
});
