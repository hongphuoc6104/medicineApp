/**
 * Scan service — proxy prescription image to Python FastAPI pipeline.
 */
import { query } from '../config/database.js';
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import logger from '../middleware/logger.js';

/**
 * Forward prescription image to Python FastAPI for OCR + NER.
 * @param {Buffer} imageBuffer - Image file buffer
 * @param {string} userId - Authenticated user ID
 * @param {string} originalName - Original filename
 * @returns {Promise<object>} Scan result
 */
export async function scanPrescription(imageBuffer, userId, originalName) {
  let result;

  try {
    // Build multipart form for Python API
    const formData = new FormData();
    const blob = new Blob([imageBuffer], { type: 'image/jpeg' });
    formData.append('file', blob, originalName || 'prescription.jpg');

    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 30_000); // 30s for OCR

    const resp = await fetch(`${env.PYTHON_API_URL}/api/scan-prescription`, {
      method: 'POST',
      body: formData,
      signal: ctrl.signal,
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      const errBody = await resp.text();
      throw new Error(`Python API returned ${resp.status}: ${errBody}`);
    }

    result = await resp.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new AppError('Scan timed out (30s)', 504, 'SCAN_TIMEOUT');
    }
    logger.error(`Python API error: ${err.message}`);
    throw new AppError(
      'AI pipeline unavailable. Please try again later.',
      503,
      'PIPELINE_UNAVAILABLE'
    );
  }

  // Save to scan history
  const drugCount = result.medications?.length || 0;
  try {
    await query(
      `INSERT INTO scans (user_id, result, drug_count)
       VALUES ($1, $2, $3)`,
      [userId, JSON.stringify(result), drugCount]
    );
  } catch (err) {
    logger.warn(`Failed to save scan history: ${err.message}`);
  }

  return result;
}

/**
 * Get scan history for a user.
 * @param {string} userId
 * @param {{ page?: number, limit?: number }} opts
 */
export async function getScanHistory(userId, { page = 1, limit = 20 } = {}) {
  const offset = (page - 1) * limit;

  const result = await query(
    `SELECT id, drug_count, scanned_at, result
     FROM scans
     WHERE user_id = $1
     ORDER BY scanned_at DESC
     LIMIT $2 OFFSET $3`,
    [userId, limit, offset]
  );

  const countResult = await query(
    'SELECT COUNT(*) FROM scans WHERE user_id = $1',
    [userId]
  );

  return {
    scans: result.rows,
    total: parseInt(countResult.rows[0].count),
  };
}
