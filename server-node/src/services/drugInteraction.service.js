/**
 * Drug interaction service — proxy + normalize DDI interaction APIs.
 */
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import logger from '../middleware/logger.js';

const SEVERITY_ORDER = {
  contraindicated: 0,
  major: 1,
  moderate: 2,
  minor: 3,
  caution: 4,
  unknown: 5,
};

const EMPTY_SUMMARY = {
  contraindicated: 0,
  major: 0,
  moderate: 0,
  minor: 0,
  caution: 0,
  unknown: 0,
};

const DEFAULT_NO_INTERACTIONS_MESSAGE =
  'Không phát hiện tương tác trong dữ liệu hiện tại.';
const DEFAULT_HAS_INTERACTIONS_MESSAGE = 'Đã tìm thấy tương tác thuốc.';

function normalizeSeverity(rawValue) {
  const value = (rawValue || '').toString().trim().toLowerCase();
  if (!value) return 'unknown';

  if (
    value.includes('chống chỉ định')
    || value.includes('chong chi dinh')
    || value.includes('contraindicated')
  ) {
    return 'contraindicated';
  }

  if (
    value.includes('nghiêm trọng')
    || value.includes('nghiem trong')
    || value.includes('major')
  ) {
    return 'major';
  }

  if (
    value.includes('trung bình')
    || value.includes('trung binh')
    || value.includes('moderate')
  ) {
    return 'moderate';
  }

  if (value.includes('nhẹ') || value.includes('nhe') || value.includes('minor')) {
    return 'minor';
  }

  if (
    value.includes('thận trọng')
    || value.includes('than trong')
    || value.includes('không nên phối hợp')
    || value.includes('khong nen phoi hop')
    || value.includes('không khuyến cáo')
    || value.includes('khong khuyen cao')
    || value.includes('cần phải chú ý')
    || value.includes('can phai chu y')
    || value.includes('caution')
  ) {
    return 'caution';
  }

  return 'unknown';
}

function severityRank(value) {
  return SEVERITY_ORDER[value] ?? SEVERITY_ORDER.unknown;
}

function parseJson(text) {
  if (!text || !text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function requestDdi(path, { method = 'GET', body, timeoutMs = 7000 } = {}) {
  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const response = await fetch(`${env.DDI_API_BASE}${path}`, {
      method,
      signal: ctrl.signal,
      headers: {
        'Accept': 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });

    const text = await response.text();
    const data = parseJson(text);

    return {
      ok: response.ok,
      status: response.status,
      data,
      text,
    };
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new AppError('Drug interaction service timed out', 504, 'INTERACTION_TIMEOUT');
    }

    logger.warn(`DDI interaction API network error: ${err.message}`);
    throw new AppError(
      'Drug interaction service unavailable',
      503,
      'INTERACTION_SERVICE_ERROR'
    );
  } finally {
    clearTimeout(timeout);
  }
}

function pickFirst(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null) {
      const trimmed = String(value).trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }

  return '';
}

function toInteractionItem(rawItem = {}, severityHint = '') {
  const severityOriginal = pickFirst(
    rawItem.mucDoNghiemTrong,
    rawItem.MucDoNghiemTrong,
    rawItem.severity,
    rawItem.Severity,
    severityHint
  );

  return {
    drugA: pickFirst(
      rawItem.drugA,
      rawItem.drug_a,
      rawItem.tenThuoc1,
      rawItem.TenThuoc_1,
      rawItem.TenThuoc,
      rawItem.drug_name_a
    ),
    drugB: pickFirst(
      rawItem.drugB,
      rawItem.drug_b,
      rawItem.tenThuoc2,
      rawItem.TenThuoc_2,
      rawItem.drug_name_b
    ),
    ingredientA: pickFirst(
      rawItem.ingredientA,
      rawItem.hoatChat1,
      rawItem.HoatChat_1,
      rawItem.activeIngredient1,
      rawItem.active_ingredient_1
    ),
    ingredientB: pickFirst(
      rawItem.ingredientB,
      rawItem.hoatChat2,
      rawItem.HoatChat_2,
      rawItem.activeIngredient2,
      rawItem.active_ingredient_2
    ),
    severity: normalizeSeverity(severityOriginal),
    severityOriginal,
    warning: pickFirst(
      rawItem.warning,
      rawItem.canhBao,
      rawItem.CanhBaoTuongTacThuoc,
      rawItem.effect,
      rawItem.recommendations
    ),
  };
}

function summarizeInteractions(items) {
  const severitySummary = { ...EMPTY_SUMMARY };
  for (const item of items) {
    severitySummary[item.severity] = (severitySummary[item.severity] || 0) + 1;
  }

  const highest = items.length
    ? [...items].sort((a, b) => severityRank(a.severity) - severityRank(b.severity))[0].severity
    : 'unknown';

  return {
    severitySummary,
    highestSeverity: highest,
  };
}

function sortInteractions(items) {
  return [...items].sort((a, b) => {
    const bySeverity = severityRank(a.severity) - severityRank(b.severity);
    if (bySeverity !== 0) {
      return bySeverity;
    }

    const aDrugA = a.drugA || '';
    const bDrugA = b.drugA || '';
    const byDrugA = aDrugA.localeCompare(bDrugA, 'vi');
    if (byDrugA !== 0) {
      return byDrugA;
    }

    const aDrugB = a.drugB || '';
    const bDrugB = b.drugB || '';
    return aDrugB.localeCompare(bDrugB, 'vi');
  });
}

function ensureServiceAvailable(response) {
  if (response.ok) {
    return;
  }

  if (response.status === 404) {
    return;
  }

  logger.warn(`DDI interaction API error: ${response.status} ${response.text || ''}`);
  throw new AppError(
    'Drug interaction service unavailable',
    503,
    'INTERACTION_SERVICE_ERROR'
  );
}

function unwrapPayload(data) {
  if (!data || typeof data !== 'object') {
    return data;
  }

  if (Array.isArray(data)) {
    return data;
  }

  if (data.data !== undefined) {
    return data.data;
  }

  return data;
}

function normalizeInputList(values, fieldName) {
  const unique = [];
  const seen = new Set();

  for (const raw of values || []) {
    const value = String(raw || '').trim();
    if (!value) {
      continue;
    }

    const lower = value.toLowerCase();
    if (seen.has(lower)) {
      continue;
    }
    seen.add(lower);
    unique.push(value);
  }

  if (unique.length < 2) {
    throw new AppError(
      `At least 2 unique ${fieldName} are required`,
      400,
      'VALIDATION_ERROR'
    );
  }

  return unique;
}

export async function checkByDrugNames(drugNames) {
  const normalizedDrugNames = normalizeInputList(drugNames, 'drug names');

  const response = await requestDdi('/interactions', {
    method: 'POST',
    body: { drugNames: normalizedDrugNames },
  });

  ensureServiceAvailable(response);

  const payload = unwrapPayload(response.data);
  const rawItems = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.interactions)
      ? payload.interactions
      : [];

  const interactions = sortInteractions(rawItems.map((item) => toInteractionItem(item)));
  const { severitySummary, highestSeverity } = summarizeInteractions(interactions);

  return {
    requestedDrugNames: normalizedDrugNames,
    hasInteractions: interactions.length > 0,
    totalInteractions: interactions.length,
    highestSeverity,
    severitySummary,
    interactions,
    message:
      payload?.message
      || (interactions.length > 0
        ? DEFAULT_HAS_INTERACTIONS_MESSAGE
        : DEFAULT_NO_INTERACTIONS_MESSAGE),
  };
}

export async function searchActiveIngredients(keyword) {
  const response = await requestDdi(
    `/interactions/search-active-ingredients?keyword=${encodeURIComponent(keyword)}`
  );

  ensureServiceAvailable(response);

  const data = unwrapPayload(response.data);
  const list = Array.isArray(data)
    ? data
    : Array.isArray(data?.suggestions)
      ? data.suggestions
      : [];

  const names = list
    .map((item) => {
      if (typeof item === 'string') {
        return item.trim();
      }
      return pickFirst(item.activeIngredient, item.name, item.value);
    })
    .filter((name) => name.length > 0);

  return {
    keyword,
    suggestions: [...new Set(names)].map((name) => ({ name })),
  };
}

function normalizeGroupedInteractions(rawGroups) {
  const groups = [];
  const flat = [];

  for (const [severityOriginal, items] of Object.entries(rawGroups || {})) {
    const normalizedItems = (Array.isArray(items) ? items : [])
      .map((item) => toInteractionItem(item, severityOriginal));

    if (normalizedItems.length === 0) {
      continue;
    }

    flat.push(...normalizedItems);

    groups.push({
      severity: normalizeSeverity(severityOriginal),
      severityOriginal,
      count: normalizedItems.length,
      interactions: sortInteractions(normalizedItems),
    });
  }

  groups.sort((a, b) => {
    const bySeverity = severityRank(a.severity) - severityRank(b.severity);
    if (bySeverity !== 0) {
      return bySeverity;
    }

    return a.severityOriginal.localeCompare(b.severityOriginal, 'vi');
  });

  return {
    groups,
    flat: sortInteractions(flat),
  };
}

export async function checkByActiveIngredients(activeIngredients) {
  const normalizedIngredients = normalizeInputList(
    activeIngredients,
    'active ingredients'
  );

  const response = await requestDdi('/interactions/check-by-active-ingredients', {
    method: 'POST',
    body: { activeIngredients: normalizedIngredients },
  });

  ensureServiceAvailable(response);

  const payload = unwrapPayload(response.data) || {};
  const { groups, flat } = normalizeGroupedInteractions(payload.interactions || {});
  const { severitySummary, highestSeverity } = summarizeInteractions(flat);

  return {
    requestedActiveIngredients: normalizedIngredients,
    hasInteractions: flat.length > 0,
    totalInteractions: flat.length,
    highestSeverity,
    severitySummary,
    groups,
    interactions: flat,
    message:
      payload.message
      || (flat.length > 0
        ? DEFAULT_HAS_INTERACTIONS_MESSAGE
        : DEFAULT_NO_INTERACTIONS_MESSAGE),
  };
}

export async function getInteractionsByActiveIngredient(ingredientName) {
  const response = await requestDdi(
    `/interactions/by-active-ingredient?ingredientName=${encodeURIComponent(ingredientName)}`
  );

  ensureServiceAvailable(response);

  const payload = unwrapPayload(response.data) || {};
  const { groups, flat } = normalizeGroupedInteractions(payload.interactions || {});
  const { severitySummary, highestSeverity } = summarizeInteractions(flat);

  return {
    ingredientName,
    hasInteractions: flat.length > 0,
    totalInteractions: flat.length,
    highestSeverity,
    severitySummary,
    groups,
    interactions: flat,
    message:
      payload.message
      || (flat.length > 0
        ? DEFAULT_HAS_INTERACTIONS_MESSAGE
        : DEFAULT_NO_INTERACTIONS_MESSAGE),
  };
}
