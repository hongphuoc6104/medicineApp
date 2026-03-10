/**
 * Drug service — search local DB + ddi.lab.io.vn API + PostgreSQL cache.
 *
 * Flow:
 * 1. Search local drug_cache (crawled data, 9284 drugs) using pg_trgm fuzzy search
 * 2. If not found / user requests detailed info → call ddi.lab.io.vn API
 * 3. Cache API results in drug_cache (7 day TTL)
 */
import { query } from '../config/database.js';
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import logger from '../middleware/logger.js';

/**
 * Search drugs by name (fuzzy search using pg_trgm).
 * @param {string} q - Search query
 * @param {{ page?: number, limit?: number }} opts
 * @returns {Promise<{ drugs: any[], total: number }>}
 */
export async function searchDrugs(q, { page = 1, limit = 20 } = {}) {
  const offset = (page - 1) * limit;

  if (!q || q.trim().length < 2) {
    throw new AppError('Search query must be at least 2 characters', 400, 'INVALID_QUERY');
  }

  const searchTerm = q.trim();

  // Use pg_trgm for fuzzy search + ILIKE for exact prefix match
  const result = await query(
    `SELECT drug_name, source, data,
            similarity(drug_name, $1) AS sim_score
     FROM drug_cache
     WHERE drug_name % $1 OR drug_name ILIKE $2
     ORDER BY sim_score DESC, drug_name ASC
     LIMIT $3 OFFSET $4`,
    [searchTerm, `%${searchTerm}%`, limit, offset]
  );

  // Count total
  const countResult = await query(
    `SELECT COUNT(*) FROM drug_cache
     WHERE drug_name % $1 OR drug_name ILIKE $2`,
    [searchTerm, `%${searchTerm}%`]
  );

  const total = parseInt(countResult.rows[0].count);

  return {
    drugs: result.rows.map((r) => ({
      name: r.drug_name,
      source: r.source,
      score: parseFloat(r.sim_score),
      ...r.data,
    })),
    total,
  };
}

/**
 * Get drug details by exact name.
 * First checks local cache, then calls ddi.lab.io.vn API.
 * @param {string} name - Drug name
 * @returns {Promise<object>}
 */
export async function getDrugDetails(name) {
  if (!name || name.trim().length < 1) {
    throw new AppError('Drug name required', 400, 'INVALID_NAME');
  }

  const trimmed = name.trim();

  // 1. Check local cache
  const cached = await query(
    `SELECT data, source, cached_at, expires_at FROM drug_cache
     WHERE drug_name ILIKE $1 LIMIT 1`,
    [trimmed]
  );

  if (cached.rows.length > 0) {
    const row = cached.rows[0];
    return {
      ...row.data,
      _source: row.source,
      _cached: true,
      _cached_at: row.cached_at,
    };
  }

  // 2. Not in cache → call ddi.lab.io.vn API
  return await fetchFromDdi(trimmed);
}

/**
 * Get drug interactions by active ingredient.
 * @param {string} ingredientName
 * @returns {Promise<object>}
 */
export async function getInteractions(ingredientName) {
  if (!ingredientName || ingredientName.length < 2) {
    throw new AppError('Ingredient name required', 400, 'INVALID_NAME');
  }

  try {
    const url = `${env.DDI_API_BASE}/interactions/by-active-ingredient?ingredientName=${encodeURIComponent(ingredientName)}`;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 5000);

    const resp = await fetch(url, {
      signal: ctrl.signal,
      headers: { 'Accept': 'application/json' },
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      throw new Error(`DDI API returned ${resp.status}`);
    }

    return await resp.json();
  } catch (err) {
    logger.warn(`DDI interactions API error: ${err.message}`);
    throw new AppError(
      'Drug interaction service unavailable',
      503,
      'INTERACTION_SERVICE_ERROR'
    );
  }
}

// ── Internal ──

async function fetchFromDdi(drugName) {
  try {
    const url = `${env.DDI_API_BASE}/drugs/search-detailed?q=${encodeURIComponent(drugName)}&page=1&limit=5`;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 5000);

    const resp = await fetch(url, {
      signal: ctrl.signal,
      headers: { 'Accept': 'application/json' },
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      throw new Error(`DDI API returned ${resp.status}`);
    }

    const data = await resp.json();
    const drugs = data.drugs || [];

    if (drugs.length === 0) {
      throw new AppError(`Drug not found: ${drugName}`, 404, 'DRUG_NOT_FOUND');
    }

    // Cache the first result
    const drug = drugs[0];
    try {
      await query(
        `INSERT INTO drug_cache (drug_name, source, data, expires_at)
         VALUES ($1, 'ddi', $2, NOW() + INTERVAL '7 days')
         ON CONFLICT (drug_name, source) DO UPDATE
         SET data = $2, cached_at = NOW(), expires_at = NOW() + INTERVAL '7 days'`,
        [drug.tenThuoc?.trim() || drugName, JSON.stringify(drug)]
      );
    } catch (cacheErr) {
      logger.warn(`Failed to cache drug: ${cacheErr.message}`);
    }

    return {
      ...drug,
      _source: 'ddi',
      _cached: false,
    };
  } catch (err) {
    if (err instanceof AppError) throw err;

    logger.warn(`DDI API error: ${err.message}`);
    throw new AppError(
      'Drug information service temporarily unavailable',
      503,
      'DDI_SERVICE_ERROR'
    );
  }
}
