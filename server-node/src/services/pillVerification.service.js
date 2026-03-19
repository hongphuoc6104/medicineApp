import { query } from '../config/database.js';
import { env } from '../config/env.js';
import { AppError } from '../utils/errors.js';
import logger from '../middleware/logger.js';

function buildPrescriptionBlocks(expectedMedications = []) {
  return expectedMedications.map((med, index) => ({
    text: med.drugName || med.name || `Drug ${index + 1}`,
    label: 'drugname',
    bbox: [20, 20 + index * 24, 320, 36 + index * 24],
  }));
}

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

async function getSessionRow(sessionId, userId) {
  const result = await query(
    `SELECT *
     FROM pill_verification_sessions
     WHERE id = $1 AND user_id = $2
     LIMIT 1`,
    [sessionId, userId]
  );
  const row = result.rows[0];
  if (!row) {
    throw new AppError('Pill verification session not found', 404, 'PILL_VERIFICATION_NOT_FOUND');
  }
  return row;
}

async function listAssignments(sessionId) {
  const result = await query(
    `SELECT detection_idx, assigned_drug_name, status, note
     FROM pill_verification_assignments
     WHERE session_id = $1
     ORDER BY detection_idx ASC`,
    [sessionId]
  );
  return result.rows;
}

async function buildSessionState(sessionId, userId) {
  const row = await getSessionRow(sessionId, userId);
  const dosePayload = parseJsonb(row.dose_payload, {});
  const result = parseJsonb(row.result, {});
  const assignments = await listAssignments(sessionId);
  const assignmentMap = new Map(assignments.map((item) => [item.detection_idx, item]));

  const expectedMedications = Array.isArray(dosePayload.expectedMedications)
    ? dosePayload.expectedMedications
    : [];

  const detections = (Array.isArray(result.detections) ? result.detections : []).map((det, index) => {
    const assigned = assignmentMap.get(index);
    return {
      ...det,
      detectionIdx: index,
      assignedDrugName: assigned?.assigned_drug_name || null,
      assignmentStatus: assigned?.status || 'unassigned',
      note: assigned?.note || null,
    };
  });

  const matchedNames = new Set(
    detections
      .filter((det) => det.assignmentStatus === 'assigned' && det.assignedDrugName)
      .map((det) => String(det.assignedDrugName).toLowerCase().trim())
  );
  const missingExpected = expectedMedications.filter((med) => {
    const name = String(med.drugName || med.name || '').toLowerCase().trim();
    return name && !matchedNames.has(name);
  });

  return {
    sessionId: row.id,
    occurrenceId: row.occurrence_id,
    status: row.status,
    expectedMedications,
    detections,
    note: result.note || null,
    modelDrugBlocks: Array.isArray(result.drugBlocks) ? result.drugBlocks : [],
    summary: {
      totalDetections: detections.length,
      assigned: detections.filter((det) => det.assignmentStatus === 'assigned').length,
      unknown: detections.filter((det) => det.assignmentStatus === 'unknown').length,
      extra: detections.filter((det) => det.assignmentStatus === 'extra').length,
      unassigned: detections.filter((det) => det.assignmentStatus === 'unassigned').length,
      missingExpected: missingExpected.length,
    },
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    confirmedAt: row.confirmed_at,
  };
}

export async function startSession(userId, payload) {
  const result = await query(
    `INSERT INTO pill_verification_sessions (user_id, occurrence_id, dose_payload)
     VALUES ($1, $2, $3::jsonb)
     RETURNING id`,
    [userId, payload.occurrenceId, JSON.stringify(payload)]
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
    throw new AppError('Session already confirmed', 400, 'PILL_VERIFICATION_CONFIRMED');
  }

  const payload = parseJsonb(row.dose_payload, {});
  const prescriptionBlocks = buildPrescriptionBlocks(payload.expectedMedications || []);

  let result;
  try {
    const formData = new FormData();
    const blob = new Blob([imageBuffer], { type: detectedMime });
    formData.append('file', blob, originalName || 'pills.jpg');
    formData.append('prescription_json', JSON.stringify(prescriptionBlocks));

    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 30_000);

    const resp = await fetch(`${env.PYTHON_API_URL}/api/scan-pills`, {
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
    logger.error(`Phase B proxy error: ${err.message}`);
    throw new AppError(
      'Pill verification pipeline unavailable. Please try again later.',
      503,
      'PILL_PIPELINE_UNAVAILABLE'
    );
  }

  const expectedMedications = Array.isArray(payload.expectedMedications)
    ? payload.expectedMedications
    : [];
  const detections = (Array.isArray(result?.detections) ? result.detections : []).map((det, index) => ({
    detectionIdx: index,
    bbox: det.bbox || [],
    score: Number(det.score || 0),
    label: det.label || 1,
    suggestedDrugNames: expectedMedications.map((med) => med.drugName || med.name).filter(Boolean).slice(0, 3),
  }));

  await query(
    `UPDATE pill_verification_sessions
     SET result = $1::jsonb,
         status = 'scanned',
         updated_at = NOW()
     WHERE id = $2 AND user_id = $3`,
    [
      JSON.stringify({
        detections,
        drugBlocks: result?.drug_blocks || [],
        note: result?.note || null,
      }),
      sessionId,
      userId,
    ]
  );

  return buildSessionState(sessionId, userId);
}

export async function assignDetection(sessionId, userId, payload) {
  await getSessionRow(sessionId, userId);

  await query(
    `INSERT INTO pill_verification_assignments
       (session_id, detection_idx, assigned_drug_name, status, note, updated_at)
     VALUES ($1, $2, $3, $4, $5, NOW())
     ON CONFLICT (session_id, detection_idx)
     DO UPDATE SET
       assigned_drug_name = EXCLUDED.assigned_drug_name,
       status = EXCLUDED.status,
       note = EXCLUDED.note,
       updated_at = NOW()`,
    [
      sessionId,
      payload.detectionIdx,
      payload.assignedDrugName || null,
      payload.status,
      payload.note || null,
    ]
  );

  return buildSessionState(sessionId, userId);
}

export async function confirmSession(sessionId, userId) {
  await getSessionRow(sessionId, userId);
  await query(
    `UPDATE pill_verification_sessions
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
