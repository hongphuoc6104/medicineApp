import { query } from '../config/database.js';
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import logger from '../middleware/logger.js';
import { getReferenceProfilesForPlans } from './pillReference.service.js';

const MANUAL_STATUSES = new Set(['assigned', 'uncertain', 'unknown', 'extra']);

function parseJsonb(value, fallback) {
  if (!value) return fallback;
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch (_) {
      return fallback;
    }
  }
  return value;
}

function normalizeExpectedMedications(expected = []) {
  return expected.map((med, index) => {
    const planId = String(med.planId || med.plan_id || '').trim();
    const drugName = String(med.drugName || med.name || `Thuốc ${index + 1}`).trim();
    const pillsPerDoseRaw = med.pillsPerDose ?? med.expectedCount ?? 1;
    const pillsPerDose = Number.isFinite(Number(pillsPerDoseRaw))
      ? Math.max(1, Number.parseInt(pillsPerDoseRaw, 10))
      : 1;

    return {
      planId,
      drugName,
      dosage: med.dosage || null,
      pillsPerDose,
    };
  });
}

function normalizeDetection(det = {}, index = 0) {
  return {
    detectionIdx: Number.isFinite(Number(det.detectionIdx))
      ? Number.parseInt(det.detectionIdx, 10)
      : index,
    bbox: Array.isArray(det.bbox) ? det.bbox : [],
    score: Number(det.score || 0),
    label: Number(det.label || 1),
    status: String(det.status || 'unknown'),
    assignedPlanId: det.assignedPlanId || null,
    assignedDrugName: det.assignedDrugName || null,
    confidence: Number(det.confidence || 0),
    note: det.note || null,
    suggestions: Array.isArray(det.suggestions) ? det.suggestions : [],
  };
}

function mapSuggestionDrugNames(suggestions = []) {
  return suggestions
    .map((item) => item?.drugName)
    .filter((name) => typeof name === 'string' && name.trim().length > 0);
}

function buildPerMedicationSummary(expectedMedications = [], detections = []) {
  return expectedMedications.map((med) => {
    const assignedCount = detections.filter(
      (det) => det.assignmentStatus === 'assigned' && det.assignedPlanId === med.planId
    ).length;
    const extraCount = detections.filter(
      (det) => det.assignmentStatus === 'extra' && det.assignedPlanId === med.planId
    ).length;

    const missingCount = Math.max(med.pillsPerDose - assignedCount, 0);
    return {
      planId: med.planId,
      drugName: med.drugName,
      expectedCount: med.pillsPerDose,
      assignedCount,
      missingCount,
      extraCount,
    };
  });
}

function computeSummary(expectedMedications = [], detections = [], baseSummary = {}) {
  const perMedication = buildPerMedicationSummary(expectedMedications, detections);
  const missingExpected = perMedication.reduce((acc, item) => acc + item.missingCount, 0);

  return {
    ...baseSummary,
    totalDetections: detections.length,
    assigned: detections.filter((det) => det.assignmentStatus === 'assigned').length,
    uncertain: detections.filter((det) => det.assignmentStatus === 'uncertain').length,
    unknown: detections.filter((det) => det.assignmentStatus === 'unknown').length,
    extra: detections.filter((det) => det.assignmentStatus === 'extra').length,
    unassigned: detections.filter((det) => det.assignmentStatus === 'unassigned').length,
    missingExpected,
    perMedication,
  };
}

async function getSessionRow(sessionId, userId) {
  const result = await query(
    `SELECT *
     FROM dose_verification_sessions
     WHERE id = $1 AND user_id = $2
     LIMIT 1`,
    [sessionId, userId]
  );
  const row = result.rows[0];
  if (!row) {
    throw new AppError('Không tìm thấy phiên xác minh liều', 404, 'DOSE_VERIFICATION_NOT_FOUND');
  }
  return row;
}

async function upsertDetections(sessionId, detections = []) {
  await query(
    `DELETE FROM dose_verification_detections
     WHERE session_id = $1`,
    [sessionId]
  );

  for (const det of detections) {
    await query(
      `INSERT INTO dose_verification_detections
         (session_id, detection_idx, bbox, score, assigned_plan_id,
          assigned_drug_name, confidence, status, note, suggestions, source, updated_at)
       VALUES
         ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, NOW())`,
      [
        sessionId,
        det.detectionIdx,
        JSON.stringify(det.bbox || []),
        Number(det.score || 0),
        det.assignedPlanId || null,
        det.assignedDrugName || null,
        Number(det.confidence || 0),
        det.status || 'unknown',
        det.note || null,
        JSON.stringify(Array.isArray(det.suggestions) ? det.suggestions : []),
        det.source || 'auto',
      ]
    );
  }
}

async function listDetections(sessionId) {
  const result = await query(
    `SELECT detection_idx,
            bbox,
            score,
            assigned_plan_id,
            assigned_drug_name,
            confidence,
            status,
            note,
            suggestions,
            source,
            updated_at
     FROM dose_verification_detections
     WHERE session_id = $1
     ORDER BY detection_idx ASC`,
    [sessionId]
  );

  return result.rows.map((row) => ({
    detectionIdx: row.detection_idx,
    bbox: parseJsonb(row.bbox, []),
    score: Number(row.score || 0),
    assignedPlanId: row.assigned_plan_id || null,
    assignedDrugName: row.assigned_drug_name || null,
    confidence: Number(row.confidence || 0),
    assignmentStatus: row.status || 'unassigned',
    status: row.status || 'unassigned',
    note: row.note || null,
    suggestions: parseJsonb(row.suggestions, []),
    suggestedDrugNames: mapSuggestionDrugNames(parseJsonb(row.suggestions, [])),
    source: row.source || 'auto',
    updatedAt: row.updated_at,
  }));
}

async function appendFeedbackEvent(sessionId, detectionIdx, action, payload = {}) {
  const normalizedIdx = Number(detectionIdx);
  await query(
    `INSERT INTO dose_verification_feedback_events
       (session_id, detection_idx, action, payload, created_at)
     VALUES ($1, $2, $3, $4::jsonb, NOW())`,
    [
      sessionId,
      Number.isFinite(normalizedIdx) ? Math.trunc(normalizedIdx) : null,
      action,
      JSON.stringify(payload || {}),
    ]
  );
}

async function buildSessionState(sessionId, userId) {
  const row = await getSessionRow(sessionId, userId);
  const expectedMedications = normalizeExpectedMedications(
    parseJsonb(row.expected_medications, [])
  );
  const result = parseJsonb(row.result, {});
  const detections = await listDetections(sessionId);

  const summary = computeSummary(
    expectedMedications,
    detections,
    parseJsonb(result.summary, {})
  );

  const referenceCoverage = parseJsonb(result.referenceCoverage, {
    totalExpected: expectedMedications.length,
    withReference: 0,
    withoutReference: expectedMedications.length,
    missingPlanIds: expectedMedications
      .map((med) => med.planId)
      .filter((planId) => planId.length > 0),
    missingDrugNames: expectedMedications.map((med) => med.drugName),
  });

  return {
    sessionId: row.id,
    occurrenceId: row.occurrence_id,
    scheduledTime: row.scheduled_time,
    status: row.status,
    expectedMedications,
    detections,
    summary,
    referenceCoverage,
    missingReferences: Array.isArray(result.missingReferences)
      ? result.missingReferences
      : referenceCoverage.missingDrugNames || [],
    note: result.note || null,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    confirmedAt: row.confirmed_at,
  };
}

function normalizeStartPayload(payload) {
  const expectedMedications = normalizeExpectedMedications(
    Array.isArray(payload.expectedMedications) ? payload.expectedMedications : []
  );
  if (expectedMedications.length === 0) {
    throw new AppError('Thiếu danh sách thuốc cần xác minh', 400, 'INVALID_EXPECTED_MEDICATIONS');
  }

  return {
    occurrenceId: String(payload.occurrenceId || '').trim(),
    scheduledTime: payload.scheduledTime,
    expectedMedications,
  };
}

export async function startSession(userId, payload) {
  const normalized = normalizeStartPayload(payload);
  if (!normalized.occurrenceId) {
    throw new AppError('Thiếu occurrenceId', 400, 'INVALID_OCCURRENCE_ID');
  }

  const result = await query(
    `INSERT INTO dose_verification_sessions
       (user_id, occurrence_id, scheduled_time, expected_medications, status, result, updated_at)
     VALUES ($1, $2, $3, $4::jsonb, 'draft', '{}'::jsonb, NOW())
     RETURNING id`,
    [
      userId,
      normalized.occurrenceId,
      normalized.scheduledTime || null,
      JSON.stringify(normalized.expectedMedications),
    ]
  );

  return buildSessionState(result.rows[0].id, userId);
}

export async function uploadImage(
  sessionId,
  userId,
  imageBuffer,
  originalName,
  detectedMime = 'image/jpeg'
) {
  const row = await getSessionRow(sessionId, userId);
  if (row.status === 'confirmed') {
    throw new AppError('Phiên đã được xác nhận', 400, 'DOSE_VERIFICATION_CONFIRMED');
  }

  const expectedMedications = normalizeExpectedMedications(
    parseJsonb(row.expected_medications, [])
  );
  const planIds = expectedMedications
    .map((med) => med.planId)
    .filter((planId) => planId.length > 0);
  const referenceProfiles = await getReferenceProfilesForPlans(userId, planIds);

  let result;
  try {
    const formData = new FormData();
    const blob = new Blob([imageBuffer], { type: detectedMime });
    formData.append('file', blob, originalName || 'dose.jpg');
    formData.append('occurrence_id', row.occurrence_id);
    if (row.scheduled_time) {
      formData.append('scheduled_time', new Date(row.scheduled_time).toISOString());
    }
    formData.append('expected_medications', JSON.stringify(expectedMedications));
    formData.append('reference_profiles', JSON.stringify(referenceProfiles));

    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 30_000);

    const resp = await fetch(`${env.PYTHON_API_URL}/api/dose-verification`, {
      method: 'POST',
      body: formData,
      signal: ctrl.signal,
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Python API returned ${resp.status}: ${text}`);
    }

    result = await resp.json();
  } catch (err) {
    logger.error(`Dose verification proxy error: ${err.message}`);
    throw new AppError(
      'Pipeline xác minh liều đang tạm thời không khả dụng.',
      503,
      'DOSE_PIPELINE_UNAVAILABLE'
    );
  }

  const detections = (Array.isArray(result?.detections) ? result.detections : []).map((det, index) =>
    normalizeDetection(det, index)
  );

  await upsertDetections(
    row.id,
    detections.map((det) => ({
      ...det,
      source: 'auto',
    }))
  );

  await query(
    `UPDATE dose_verification_sessions
     SET status = 'scanned',
         result = $1::jsonb,
         updated_at = NOW()
     WHERE id = $2 AND user_id = $3`,
    [
      JSON.stringify({
        summary: result?.summary || null,
        referenceCoverage: result?.referenceCoverage || null,
        missingReferences: result?.missingReferences || [],
        expectedMedications,
        mode: result?.mode || 'dose_verification',
      }),
      row.id,
      userId,
    ]
  );

  return buildSessionState(sessionId, userId);
}

export async function assignDetection(sessionId, userId, payload) {
  await getSessionRow(sessionId, userId);

  if (!MANUAL_STATUSES.has(payload.status)) {
    throw new AppError('Trạng thái gán không hợp lệ', 400, 'INVALID_ASSIGNMENT_STATUS');
  }

  if (payload.status === 'assigned' && !payload.assignedDrugName) {
    throw new AppError('Thiếu tên thuốc khi gán detection', 400, 'MISSING_ASSIGNED_DRUG');
  }

  await query(
    `INSERT INTO dose_verification_detections
       (session_id, detection_idx, assigned_plan_id, assigned_drug_name,
        status, note, source, updated_at)
     VALUES ($1, $2, $3, $4, $5, $6, 'manual', NOW())
     ON CONFLICT (session_id, detection_idx)
     DO UPDATE SET
       assigned_plan_id = EXCLUDED.assigned_plan_id,
       assigned_drug_name = EXCLUDED.assigned_drug_name,
       status = EXCLUDED.status,
       note = EXCLUDED.note,
       source = 'manual',
       updated_at = NOW()`,
    [
      sessionId,
      payload.detectionIdx,
      payload.assignedPlanId || null,
      payload.assignedDrugName || null,
      payload.status,
      payload.note || null,
    ]
  );

  await appendFeedbackEvent(sessionId, payload.detectionIdx, 'manual_assignment', {
    assignedPlanId: payload.assignedPlanId || null,
    assignedDrugName: payload.assignedDrugName || null,
    status: payload.status,
    note: payload.note || null,
  });

  return buildSessionState(sessionId, userId);
}

export async function confirmSession(sessionId, userId) {
  const state = await buildSessionState(sessionId, userId);
  await appendFeedbackEvent(sessionId, null, 'confirm_session', {
    summary: state.summary,
    referenceCoverage: state.referenceCoverage,
  });
  await query(
    `UPDATE dose_verification_sessions
     SET status = 'confirmed',
         confirmed_at = NOW(),
         updated_at = NOW()
     WHERE id = $1 AND user_id = $2`,
    [sessionId, userId]
  );
  return buildSessionState(sessionId, userId);
}

export async function getSession(sessionId, userId) {
  return buildSessionState(sessionId, userId);
}
