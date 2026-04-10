import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { query } from '../config/database.js';
import { AppError } from '../utils/errors.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const STORAGE_ROOT = path.resolve(__dirname, '../../storage/pill-references');

function safeNumber(value, fallback = null) {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeSide(side) {
  const value = String(side || 'front').trim().toLowerCase();
  return ['front', 'back', 'other'].includes(value) ? value : 'front';
}

function extByMime(mime) {
  if (mime === 'image/png') return '.png';
  if (mime === 'image/webp') return '.webp';
  return '.jpg';
}

function toStoragePath(userId, setId, filename) {
  return path.join('storage', 'pill-references', userId, setId, filename);
}

function toAbsoluteImagePath(imagePath) {
  const value = String(imagePath || '').trim();
  if (!value) return value;
  if (path.isAbsolute(value)) {
    return value;
  }
  return path.resolve(__dirname, '../..', value);
}

function parseUuidArray(planIds = []) {
  return Array.from(
    new Set(
      planIds
        .map((planId) => String(planId || '').trim())
        .filter((planId) => planId.length > 0)
    )
  );
}

function groupRowsToSets(rows = []) {
  const bySet = new Map();

  for (const row of rows) {
    if (!bySet.has(row.id)) {
      bySet.set(row.id, {
        id: row.id,
        userId: row.user_id,
        planId: row.plan_id,
        drugNameSnapshot: row.drug_name_snapshot,
        status: row.status,
        imageCount: 0,
        images: [],
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      });
    }

    const item = bySet.get(row.id);
    if (row.image_id) {
      item.images.push({
        id: row.image_id,
        imagePath: row.image_path,
        side: row.side || 'front',
        qualityScore: safeNumber(row.quality_score, null),
        confirmedByUser: Boolean(row.confirmed_by_user),
        createdAt: row.image_created_at,
      });
      item.imageCount += 1;
    }
  }

  return Array.from(bySet.values()).sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );
}

async function ensurePlanOwnership(userId, planId) {
  const result = await query(
    `SELECT id, drug_name
     FROM medication_plans
     WHERE id = $1 AND user_id = $2
     LIMIT 1`,
    [planId, userId]
  );
  const row = result.rows[0];
  if (!row) {
    throw new AppError('Kế hoạch thuốc không tồn tại', 404, 'PLAN_NOT_FOUND');
  }
  return row;
}

async function getSetRow(referenceSetId, userId) {
  const result = await query(
    `SELECT *
     FROM pill_reference_sets
     WHERE id = $1 AND user_id = $2
     LIMIT 1`,
    [referenceSetId, userId]
  );
  const row = result.rows[0];
  if (!row) {
    throw new AppError('Không tìm thấy hồ sơ mẫu viên thuốc', 404, 'PILL_REFERENCE_NOT_FOUND');
  }
  return row;
}

async function fetchSetWithImages(userId, { referenceSetId = null, planId = null } = {}) {
  const params = [userId];
  const clauses = ['prs.user_id = $1'];

  if (referenceSetId) {
    params.push(referenceSetId);
    clauses.push(`prs.id = $${params.length}`);
  }
  if (planId) {
    params.push(planId);
    clauses.push(`prs.plan_id = $${params.length}`);
  }

  const result = await query(
    `SELECT prs.id,
            prs.user_id,
            prs.plan_id,
            prs.drug_name_snapshot,
            prs.status,
            prs.created_at,
            prs.updated_at,
            pri.id AS image_id,
            pri.image_path,
            pri.side,
            pri.quality_score,
            pri.confirmed_by_user,
            pri.created_at AS image_created_at
     FROM pill_reference_sets prs
     LEFT JOIN pill_reference_images pri
       ON pri.reference_set_id = prs.id
     WHERE ${clauses.join(' AND ')}
     ORDER BY prs.updated_at DESC, pri.created_at DESC`,
    params
  );

  return groupRowsToSets(result.rows);
}

export async function startEnrollment(userId, payload) {
  const plan = await ensurePlanOwnership(userId, payload.planId);
  const drugNameSnapshot = String(payload.drugNameSnapshot || plan.drug_name || '').trim();
  if (!drugNameSnapshot) {
    throw new AppError('Thiếu tên thuốc để tạo hồ sơ mẫu', 400, 'INVALID_REFERENCE_PAYLOAD');
  }

  const result = await query(
    `INSERT INTO pill_reference_sets (user_id, plan_id, drug_name_snapshot, status, updated_at)
     VALUES ($1, $2, $3, 'enrolling', NOW())
     ON CONFLICT (user_id, plan_id)
     DO UPDATE SET
       drug_name_snapshot = EXCLUDED.drug_name_snapshot,
       status = 'enrolling',
       updated_at = NOW()
     RETURNING id`,
    [userId, payload.planId, drugNameSnapshot]
  );

  const sets = await fetchSetWithImages(userId, {
    referenceSetId: result.rows[0].id,
  });
  return sets[0];
}

export async function uploadEnrollmentFrame(
  referenceSetId,
  userId,
  imageBuffer,
  originalName,
  detectedMime,
  payload = {}
) {
  const setRow = await getSetRow(referenceSetId, userId);

  const side = normalizeSide(payload.side);
  const qualityScore = safeNumber(payload.qualityScore, null);
  const ext = extByMime(detectedMime);
  const safeName = String(originalName || '').replace(/[^a-zA-Z0-9_.-]/g, '_');
  const baseName = safeName.length > 0 ? safeName.slice(0, 60) : 'ref';
  const filename = `${Date.now()}-${crypto.randomUUID().slice(0, 8)}-${baseName}${ext}`;

  const dir = path.resolve(STORAGE_ROOT, userId, setRow.id);
  await fs.mkdir(dir, { recursive: true });
  const absolutePath = path.resolve(dir, filename);
  const relativePath = toStoragePath(userId, setRow.id, filename);
  await fs.writeFile(absolutePath, imageBuffer);

  await query(
    `INSERT INTO pill_reference_images
       (reference_set_id, image_path, side, quality_score, confirmed_by_user)
     VALUES ($1, $2, $3, $4, false)`,
    [setRow.id, relativePath, side, qualityScore]
  );

  await query(
    `UPDATE pill_reference_sets
     SET status = 'enrolling',
         updated_at = NOW()
     WHERE id = $1`,
    [setRow.id]
  );

  const sets = await fetchSetWithImages(userId, { referenceSetId: setRow.id });
  return sets[0];
}

export async function finalizeEnrollment(referenceSetId, userId, payload = {}) {
  const setRow = await getSetRow(referenceSetId, userId);

  const images = await query(
    `SELECT id
     FROM pill_reference_images
     WHERE reference_set_id = $1
     ORDER BY created_at DESC`,
    [setRow.id]
  );
  if (images.rows.length === 0) {
    throw new AppError('Cần ít nhất 1 ảnh mẫu trước khi hoàn tất', 400, 'EMPTY_REFERENCE_IMAGES');
  }

  const providedIds = Array.isArray(payload.confirmedImageIds)
    ? payload.confirmedImageIds.map((id) => String(id || '').trim()).filter(Boolean)
    : [];
  const imageIds = providedIds.length > 0
    ? providedIds
    : images.rows.map((row) => row.id);

  await query(
    `UPDATE pill_reference_images
     SET confirmed_by_user = false
     WHERE reference_set_id = $1`,
    [setRow.id]
  );
  await query(
    `UPDATE pill_reference_images
     SET confirmed_by_user = true
     WHERE reference_set_id = $1
       AND id = ANY($2::uuid[])`,
    [setRow.id, imageIds]
  );
  await query(
    `UPDATE pill_reference_sets
     SET status = 'ready',
         updated_at = NOW()
     WHERE id = $1`,
    [setRow.id]
  );

  const sets = await fetchSetWithImages(userId, { referenceSetId: setRow.id });
  return sets[0];
}

export async function listReferenceSets(userId, { planId = null } = {}) {
  return fetchSetWithImages(userId, { planId });
}

export async function getReferenceProfilesForPlans(userId, planIds = []) {
  const ids = parseUuidArray(planIds);
  if (ids.length === 0) {
    return [];
  }

  const result = await query(
    `SELECT prs.id,
            prs.plan_id,
            prs.drug_name_snapshot,
            prs.status,
            pri.id AS image_id,
            pri.image_path,
            pri.side,
            pri.quality_score,
            pri.confirmed_by_user
     FROM pill_reference_sets prs
     LEFT JOIN pill_reference_images pri
       ON pri.reference_set_id = prs.id
     WHERE prs.user_id = $1
       AND prs.plan_id = ANY($2::uuid[])
     ORDER BY prs.updated_at DESC, pri.created_at DESC`,
    [userId, ids]
  );

  const bySet = new Map();
  for (const row of result.rows) {
    if (!bySet.has(row.id)) {
      bySet.set(row.id, {
        referenceProfileId: row.id,
        planId: row.plan_id,
        drugName: row.drug_name_snapshot,
        status: row.status,
        images: [],
      });
    }

    if (row.image_id) {
      bySet.get(row.id).images.push({
        id: row.image_id,
        imagePath: toAbsoluteImagePath(row.image_path),
        side: row.side || 'front',
        qualityScore: safeNumber(row.quality_score, null),
        confirmedByUser: Boolean(row.confirmed_by_user),
      });
    }
  }

  return Array.from(bySet.values()).map((profile) => ({
    ...profile,
    images: (() => {
      if (profile.images.length === 0) {
        return [];
      }
      const confirmed = profile.images.filter((image) => image.confirmedByUser);
      return confirmed.length > 0 ? confirmed : profile.images;
    })(),
  }));
}
