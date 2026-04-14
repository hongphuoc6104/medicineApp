import { query } from '../config/database.js';
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import * as planService from './plan.service.js';
import * as scanService from './scan.service.js';

const LOW_CONFIDENCE_THRESHOLD = 0.75;
const STRENGTH_REGEX = /(\d+(?:[.,]\d+)?)\s*(mg|ml|mcg|g|iu|%)/gi;
const metadataCache = new Map();

export function clearReconciliationCachesForTests() {
  metadataCache.clear();
}

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9%]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function uniqueStrings(values = []) {
  return Array.from(
    new Set(
      values
        .map((value) => String(value || '').trim())
        .filter(Boolean)
    )
  );
}

function extractStrengths(...texts) {
  const hits = [];
  for (const text of texts) {
    if (!text) continue;
    let match;
    while ((match = STRENGTH_REGEX.exec(String(text))) !== null) {
      hits.push(`${match[1].replace(',', '.')} ${match[2].toLowerCase()}`);
    }
    STRENGTH_REGEX.lastIndex = 0;
  }
  return uniqueStrings(hits);
}

function normalizeIngredientEntries(entries = []) {
  const normalized = [];
  for (const entry of entries) {
    const name = String(entry?.name || entry?.ingredientName || '').trim();
    if (!name) continue;
    normalized.push({
      name,
      normalizedName: normalizeText(name),
      strength: String(entry?.strength || '').trim(),
      source: String(entry?.source || '').trim() || null,
    });
  }
  return normalized;
}

function ingredientKey(snapshot) {
  const keys = uniqueStrings(
    (snapshot.activeIngredients || [])
      .map((item) => item.normalizedName)
      .filter(Boolean)
      .sort()
  );
  return keys.join('|');
}

function exactKey(snapshot) {
  return normalizeText(snapshot.matchedDrugName || snapshot.rawName);
}

function dosageFormKey(snapshot) {
  return normalizeText(snapshot.dosageForm);
}

function strengthsKey(snapshot) {
  return uniqueStrings(snapshot.strengths || []).sort().join('|');
}

function hasManualReviewRisk(snapshot) {
  return (
    snapshot.mappingStatus !== 'confirmed'
    || Number(snapshot.confidence || 0) < LOW_CONFIDENCE_THRESHOLD
    || (!exactKey(snapshot) && !ingredientKey(snapshot))
  );
}

function buildManualReviewReason(snapshot) {
  if (snapshot.mappingStatus !== 'confirmed') {
    return 'Cần xác nhận tên thuốc từ OCR';
  }
  if (Number(snapshot.confidence || 0) < LOW_CONFIDENCE_THRESHOLD) {
    return 'Độ tin cậy OCR còn thấp';
  }
  return 'Thiếu dữ liệu chuẩn hóa để kết luận';
}

async function fetchDrugMetadata(name) {
  const normalized = normalizeText(name);
  if (!normalized) {
    return {};
  }
  if (metadataCache.has(normalized)) {
    return metadataCache.get(normalized);
  }

  const url = `${env.PYTHON_API_URL}/api/drug-metadata/${encodeURIComponent(name)}`;
  try {
    const resp = await fetch(url, {
      headers: { Accept: 'application/json' },
    });
    if (!resp.ok) {
      metadataCache.set(normalized, {});
      return {};
    }
    const data = await resp.json();
    metadataCache.set(normalized, data || {});
    return data || {};
  } catch {
    metadataCache.set(normalized, {});
    return {};
  }
}

async function toMedicationSnapshot({
  rawName,
  matchedDrugName = null,
  dosage = '',
  mappingStatus = 'confirmed',
  confidence = 1,
  sourceType,
  sourceRef,
  evidence = {},
}) {
  const queryName = matchedDrugName || rawName;
  const metadata = await fetchDrugMetadata(queryName);
  const activeIngredients = normalizeIngredientEntries(metadata.activeIngredients || []);
  const strengths = uniqueStrings([
    ...extractStrengths(rawName, dosage, evidence.ocrText),
    ...activeIngredients.map((item) => item.strength),
  ]);

  return {
    rawName: String(rawName || '').trim(),
    normalizedName: normalizeText(rawName),
    matchedDrugName: String(matchedDrugName || '').trim() || null,
    activeIngredients,
    strengths,
    dosageForm: String(metadata.dosageForm || '').trim(),
    manufacturer: String(metadata.manufacturer || '').trim(),
    packaging: String(metadata.packaging || '').trim(),
    mappingStatus,
    confidence: Number(confidence || 0),
    sourceType,
    sourceRef,
    evidence: {
      ...evidence,
      dosage: String(dosage || '').trim(),
      metadataSources: Array.isArray(metadata.sources) ? metadata.sources : [],
      identifiers: metadata.identifiers || {},
    },
  };
}

async function buildScanSnapshots(scanDetail) {
  const items = await Promise.all(
    (scanDetail.drugs || []).map((drug, index) => toMedicationSnapshot({
      rawName: drug.ocrText || drug.name,
      matchedDrugName: (drug.mappingStatus || 'unmapped_candidate') === 'confirmed'
        ? (drug.mappedDrugName || drug.name)
        : null,
      mappingStatus: drug.mappingStatus || 'unmapped_candidate',
      confidence: Number(drug.confidence || 0),
      sourceType: 'scan',
      sourceRef: {
        scanId: scanDetail.id,
        itemIndex: index,
      },
      evidence: {
        ocrText: drug.ocrText || null,
        qualityState: scanDetail.qualityState || null,
        guidance: scanDetail.guidance || null,
        bbox: drug.bbox || null,
      },
    }))
  );

  return {
    sourceType: 'scan',
    sourceRef: { scanId: scanDetail.id },
    items,
    meta: {
      qualityState: scanDetail.qualityState,
      guidance: scanDetail.guidance,
      unresolvedCount: scanDetail.unresolvedCount,
      scannedAt: scanDetail.scannedAt,
    },
  };
}

async function buildActivePlanSnapshots(userId) {
  const { plans } = await planService.getUserPlans(userId, {
    page: 1,
    limit: 100,
    activeOnly: true,
  });

  const items = [];
  for (const plan of plans) {
    for (const drug of plan.drugs || []) {
      items.push(await toMedicationSnapshot({
        rawName: drug.drugName,
        matchedDrugName: drug.drugName,
        dosage: drug.dosage || '',
        sourceType: 'active_plan',
        sourceRef: {
          planId: plan.id,
          drugId: drug.id,
        },
        evidence: {
          planTitle: plan.title,
          notes: drug.notes || null,
        },
      }));
    }
  }

  return {
    sourceType: 'active_plan',
    sourceRef: { planIds: plans.map((plan) => plan.id) },
    items,
    meta: {
      totalPlans: plans.length,
    },
  };
}

async function resolvePreviousScanId(userId, scanId) {
  const current = await query(
    `SELECT scanned_at
     FROM scans
     WHERE user_id = $1 AND id = $2
     LIMIT 1`,
    [userId, scanId]
  );
  const currentRow = current.rows[0];
  if (!currentRow) {
    throw new AppError('Scan history item not found', 404, 'SCAN_NOT_FOUND');
  }

  const previous = await query(
    `SELECT id
     FROM scans
     WHERE user_id = $1
       AND scanned_at < $2
     ORDER BY scanned_at DESC
     LIMIT 1`,
    [userId, currentRow.scanned_at]
  );

  if (!previous.rows[0]?.id) {
    throw new AppError('Không có lần quét trước đó để so sánh', 404, 'PREVIOUS_SCAN_NOT_FOUND');
  }

  return previous.rows[0].id;
}

function pushUniquePair(target, entry, keyBuilder) {
  const key = keyBuilder(entry);
  if (!target.some((item) => keyBuilder(item) === key)) {
    target.push(entry);
  }
}

function collectDuplicateActiveIngredients(items) {
  const bucket = new Map();
  for (const item of items) {
    for (const ingredient of item.activeIngredients || []) {
      if (!ingredient.normalizedName) continue;
      const list = bucket.get(ingredient.normalizedName) || [];
      list.push(item);
      bucket.set(ingredient.normalizedName, list);
    }
  }

  return Array.from(bucket.entries())
    .filter(([, snapshots]) => snapshots.length > 1)
    .map(([normalizedIngredient, snapshots]) => ({
      ingredient: snapshots[0].activeIngredients.find(
        (item) => item.normalizedName === normalizedIngredient
      )?.name || normalizedIngredient,
      snapshots,
    }));
}

function buildTransitionSafety(diff) {
  const riskCards = [];
  const checklist = [];
  const ask = [];

  if (diff.duplicate_active_ingredients.length > 0) {
    riskCards.push({
      level: 'warning',
      label: 'Có thể trùng thuốc',
      detail: 'Phát hiện ít nhất một hoạt chất xuất hiện ở nhiều thuốc trong đơn mới.',
    });
    checklist.push('Kiểm tra xem có thuốc nào bị trùng hoạt chất hoặc trùng mục đích dùng.');
    ask.push('Hỏi lại bác sĩ hoặc dược sĩ nếu thấy hai thuốc có vẻ cùng hoạt chất.');
  }

  if (diff.possible_substitutions.length > 0) {
    riskCards.push({
      level: 'info',
      label: 'Có thể đổi thuốc',
      detail: 'Có thuốc mới dùng cùng hoạt chất với thuốc cũ nhưng khác tên hoặc khác nhãn.',
    });
    checklist.push('Đối chiếu tên thuốc mới với thuốc cũ để xác nhận có phải đổi brand/generic hay không.');
    ask.push('Hỏi lại nhà thuốc nếu thuốc giao khác tên trên toa nhưng có vẻ cùng hoạt chất.');
  }

  if (diff.strength_changed.length > 0 || diff.dosage_form_changed.length > 0) {
    riskCards.push({
      level: 'warning',
      label: 'Cần hỏi lại',
      detail: 'Phát hiện thay đổi strength hoặc dạng bào chế giữa hai danh sách thuốc.',
    });
    checklist.push('Xác nhận lại strength và dạng bào chế trước khi lưu lịch hoặc mua thuốc.');
  }

  if (diff.needs_manual_review.length > 0) {
    riskCards.push({
      level: 'warning',
      label: 'Cần xác nhận nhà thuốc',
      detail: 'Có mục OCR hoặc so khớp còn yếu, chưa nên kết luận tự động.',
    });
    checklist.push('Mở lại ảnh quét và kiểm tra thủ công các mục được gắn cần xem lại.');
  }

  return {
    know: checklist,
    check: checklist,
    ask,
    riskCards,
  };
}

function reconcileSnapshots(candidateItems, baselineItems) {
  const added = [];
  const removed = [];
  const substitutions = [];
  const strengthChanged = [];
  const dosageFormChanged = [];
  const needsManualReview = [];
  const baselineUsed = new Set();
  const exactMatchedCandidates = new Set();

  for (const item of candidateItems) {
    if (hasManualReviewRisk(item)) {
      needsManualReview.push({
        side: 'candidate',
        reason: buildManualReviewReason(item),
        snapshot: item,
      });
    }
  }

  for (const item of baselineItems) {
    if (hasManualReviewRisk(item)) {
      needsManualReview.push({
        side: 'baseline',
        reason: buildManualReviewReason(item),
        snapshot: item,
      });
    }
  }

  for (const candidate of candidateItems) {
    const candidateExact = exactKey(candidate);
    if (!candidateExact) continue;

    const baselineIndex = baselineItems.findIndex((baseline, index) => {
      if (baselineUsed.has(index)) return false;
      return exactKey(baseline) === candidateExact;
    });

    if (baselineIndex === -1) continue;
    baselineUsed.add(baselineIndex);
    exactMatchedCandidates.add(candidate);
    const baseline = baselineItems[baselineIndex];

    if (strengthsKey(candidate) && strengthsKey(baseline) && strengthsKey(candidate) !== strengthsKey(baseline)) {
      pushUniquePair(strengthChanged, { candidate, baseline }, ({ candidate: c, baseline: b }) => `${exactKey(c)}:${exactKey(b)}`);
    }
    if (dosageFormKey(candidate) && dosageFormKey(baseline) && dosageFormKey(candidate) !== dosageFormKey(baseline)) {
      pushUniquePair(dosageFormChanged, { candidate, baseline }, ({ candidate: c, baseline: b }) => `${exactKey(c)}:${exactKey(b)}`);
    }
  }

  for (const candidate of candidateItems) {
    if (exactMatchedCandidates.has(candidate)) {
      continue;
    }

    const candidateIngredients = ingredientKey(candidate);
    if (!candidateIngredients) {
      if (!hasManualReviewRisk(candidate)) {
        added.push(candidate);
      }
      continue;
    }

    const substitutionIndex = baselineItems.findIndex((baseline, index) => {
      if (baselineUsed.has(index)) return false;
      const baselineIngredients = ingredientKey(baseline);
      return baselineIngredients && baselineIngredients === candidateIngredients;
    });

    if (substitutionIndex !== -1) {
      baselineUsed.add(substitutionIndex);
      const baseline = baselineItems[substitutionIndex];
      substitutions.push({
        candidate,
        baseline,
        reason: 'same_active_ingredients',
      });
      if (strengthsKey(candidate) && strengthsKey(baseline) && strengthsKey(candidate) !== strengthsKey(baseline)) {
        pushUniquePair(strengthChanged, { candidate, baseline }, ({ candidate: c, baseline: b }) => `${ingredientKey(c)}:${strengthsKey(c)}:${strengthsKey(b)}`);
      }
      if (dosageFormKey(candidate) && dosageFormKey(baseline) && dosageFormKey(candidate) !== dosageFormKey(baseline)) {
        pushUniquePair(dosageFormChanged, { candidate, baseline }, ({ candidate: c, baseline: b }) => `${ingredientKey(c)}:${dosageFormKey(c)}:${dosageFormKey(b)}`);
      }
      continue;
    }

    if (!hasManualReviewRisk(candidate)) {
      added.push(candidate);
    }
  }

  baselineItems.forEach((baseline, index) => {
    if (!baselineUsed.has(index)) {
      removed.push(baseline);
    }
  });

  const duplicateActiveIngredients = collectDuplicateActiveIngredients(candidateItems);
  const diff = {
    added_medications: added,
    removed_medications: removed,
    possible_substitutions: substitutions,
    duplicate_active_ingredients: duplicateActiveIngredients,
    strength_changed: strengthChanged,
    dosage_form_changed: dosageFormChanged,
    needs_manual_review: needsManualReview,
  };

  return {
    diff,
    summary: {
      added: added.length,
      removed: removed.length,
      substitutions: substitutions.length,
      duplicates: duplicateActiveIngredients.length,
      strengthChanged: strengthChanged.length,
      dosageFormChanged: dosageFormChanged.length,
      manualReview: needsManualReview.length,
      hasChanges: Boolean(
        added.length
        || removed.length
        || substitutions.length
        || duplicateActiveIngredients.length
        || strengthChanged.length
        || dosageFormChanged.length
      ),
      requiresManualReview: needsManualReview.length > 0,
    },
    transitionOfCare: buildTransitionSafety(diff),
  };
}

export async function compareScanToActivePlan(userId, scanId) {
  const candidateScan = await scanService.getScanHistoryItem(userId, scanId);
  const candidate = await buildScanSnapshots(candidateScan);
  const baseline = await buildActivePlanSnapshots(userId);
  const reconciliation = reconcileSnapshots(candidate.items, baseline.items);

  return {
    compareType: 'scan_vs_active_plan',
    candidate,
    baseline,
    ...reconciliation,
  };
}

export async function compareScanToPreviousScan(userId, scanId, previousScanId = null) {
  const candidateScan = await scanService.getScanHistoryItem(userId, scanId);
  const resolvedPreviousScanId = previousScanId || await resolvePreviousScanId(userId, scanId);
  const baselineScan = await scanService.getScanHistoryItem(userId, resolvedPreviousScanId);
  const candidate = await buildScanSnapshots(candidateScan);
  const baseline = await buildScanSnapshots(baselineScan);
  const reconciliation = reconcileSnapshots(candidate.items, baseline.items);

  return {
    compareType: 'scan_vs_previous_scan',
    candidate,
    baseline,
    ...reconciliation,
  };
}

export async function buildSnapshotsFromDispensedText(payload = {}) {
  const sourceRef = payload.sourceRef || null;
  const items = await Promise.all(
    (payload.items || []).map((item, index) => toMedicationSnapshot({
      rawName: item.rawName || item.ocrText || '',
      matchedDrugName: (item.mappingStatus || 'unmapped_candidate') === 'confirmed'
        ? (item.matchedDrugName || item.rawName || item.ocrText || null)
        : null,
      mappingStatus: item.mappingStatus || 'unmapped_candidate',
      confidence: Number(item.confidence || 0),
      sourceType: 'dispensed_text',
      sourceRef: {
        sourceRef,
        itemIndex: index,
      },
      evidence: {
        ocrText: item.ocrText || item.rawName || null,
        packagingType: item.packagingType || null,
      },
    }))
  );

  return {
    sourceType: 'dispensed_text',
    sourceRef: { sourceRef },
    items,
    meta: {
      packagingType: payload.packagingType || null,
    },
  };
}

export async function compareDispensedTextToActivePlan(userId, payload = {}) {
  const candidate = await buildSnapshotsFromDispensedText(payload);
  const baseline = await buildActivePlanSnapshots(userId);
  const reconciliation = reconcileSnapshots(candidate.items, baseline.items);

  return {
    compareType: 'dispensed_text_vs_active_plan',
    candidate,
    baseline,
    ...reconciliation,
  };
}
