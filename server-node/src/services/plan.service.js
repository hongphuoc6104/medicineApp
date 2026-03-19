/**
 * Plan service — medication plan CRUD + medication logs.
 */
import { query } from '../config/database.js';
import { AppError } from '../utils/errors.js';

function toUtcDateAndTimeKey(input) {
  const dt = new Date(input);
  if (Number.isNaN(dt.getTime())) {
    return null;
  }

  const iso = dt.toISOString();
  return {
    date: iso.slice(0, 10),
    time: iso.slice(11, 16),
  };
}

function normalizeDateKey(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') {
    return null;
  }
  const trimmed = dateStr.trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? trimmed : null;
}

function buildOccurrenceId(planId, scheduledTime, providedOccurrenceId) {
  if (providedOccurrenceId && typeof providedOccurrenceId === 'string') {
    const cleaned = providedOccurrenceId.trim();
    if (cleaned.length > 0) {
      return cleaned.slice(0, 120);
    }
  }

  const dateAndTime = toUtcDateAndTimeKey(scheduledTime);
  if (!dateAndTime) {
    return null;
  }
  return `${planId}:${dateAndTime.date}:${dateAndTime.time}`;
}

/**
 * Create a new medication plan.
 */
export async function createPlan(userId, data) {
  const result = await query(
    `INSERT INTO medication_plans
       (user_id, drug_name, dosage, frequency, times, pills_per_dose,
        total_days, start_date, end_date, notes)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
     RETURNING *`,
    [
      userId, data.drugName, data.dosage || null, data.frequency,
      JSON.stringify(data.times), data.pillsPerDose || 1,
      data.totalDays || null, data.startDate,
      data.endDate || null, data.notes || null,
    ]
  );
  return result.rows[0];
}

/**
 * Get all active plans for a user.
 */
export async function getUserPlans(userId, { page = 1, limit = 20, activeOnly = true } = {}) {
  const offset = (page - 1) * limit;

  // Use parameterized query — no string interpolation to avoid SQL injection risk
  const result = await query(
    `SELECT * FROM medication_plans
     WHERE user_id = $1 AND ($2::boolean IS FALSE OR is_active = true)
     ORDER BY created_at DESC
     LIMIT $3 OFFSET $4`,
    [userId, activeOnly, limit, offset]
  );

  const countResult = await query(
    `SELECT COUNT(*) FROM medication_plans
     WHERE user_id = $1 AND ($2::boolean IS FALSE OR is_active = true)`,
    [userId, activeOnly]
  );

  return {
    plans: result.rows,
    total: parseInt(countResult.rows[0].count),
  };
}

/**
 * Get a single plan by ID (must belong to user).
 */
export async function getPlanById(userId, planId) {
  const result = await query(
    'SELECT * FROM medication_plans WHERE id = $1 AND user_id = $2',
    [planId, userId]
  );
  if (result.rows.length === 0) {
    throw new AppError('Plan not found', 404, 'PLAN_NOT_FOUND');
  }
  return result.rows[0];
}

/**
 * Update a plan.
 */
export async function updatePlan(userId, planId, data) {
  // Verify ownership
  await getPlanById(userId, planId);

  const fields = [];
  const values = [];
  let idx = 1;

  const mapping = {
    drugName: 'drug_name', dosage: 'dosage', frequency: 'frequency',
    times: 'times', pillsPerDose: 'pills_per_dose',
    totalDays: 'total_days', startDate: 'start_date',
    endDate: 'end_date', isActive: 'is_active', notes: 'notes',
  };

  for (const [jsKey, dbKey] of Object.entries(mapping)) {
    if (data[jsKey] !== undefined) {
      const val = jsKey === 'times' ? JSON.stringify(data[jsKey]) : data[jsKey];
      fields.push(`${dbKey} = $${idx}`);
      values.push(val);
      idx++;
    }
  }

  if (fields.length === 0) {
    throw new AppError('No fields to update', 400, 'NO_UPDATES');
  }

  values.push(planId, userId);
  const result = await query(
    `UPDATE medication_plans SET ${fields.join(', ')}
     WHERE id = $${idx} AND user_id = $${idx + 1}
     RETURNING *`,
    values
  );

  return result.rows[0];
}

/**
 * Delete a plan (soft delete: set is_active = false).
 */
export async function deletePlan(userId, planId) {
  await getPlanById(userId, planId);
  await query(
    'UPDATE medication_plans SET is_active = false WHERE id = $1 AND user_id = $2',
    [planId, userId]
  );
}

/**
 * Log medication as taken/missed/skipped.
 */
export async function logMedication(planId, userId, data) {
  // Verify plan ownership
  const plan = await query(
    'SELECT id FROM medication_plans WHERE id = $1 AND user_id = $2',
    [planId, userId]
  );
  if (plan.rows.length === 0) {
    throw new AppError('Plan not found', 404, 'PLAN_NOT_FOUND');
  }

  const occurrenceId = buildOccurrenceId(
    planId,
    data.scheduledTime,
    data.occurrenceId
  );

  const takenAt = data.status === 'taken' ? new Date().toISOString() : null;

  if (!occurrenceId) {
    const inserted = await query(
      `INSERT INTO medication_logs
         (plan_id, scheduled_time, taken_at, status, note, occurrence_id)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [
        planId,
        data.scheduledTime,
        takenAt,
        data.status,
        data.note || null,
        null,
      ]
    );
    return inserted.rows[0];
  }

  const result = await query(
    `INSERT INTO medication_logs
       (plan_id, scheduled_time, taken_at, status, note, occurrence_id)
     VALUES ($1, $2, $3, $4, $5, $6)
     ON CONFLICT (plan_id, occurrence_id)
     DO UPDATE SET
       scheduled_time = EXCLUDED.scheduled_time,
       taken_at = EXCLUDED.taken_at,
       status = EXCLUDED.status,
       note = COALESCE(EXCLUDED.note, medication_logs.note)
     RETURNING *`,
    [
      planId,
      data.scheduledTime,
      takenAt,
      data.status,
      data.note || null,
      occurrenceId,
    ]
  );
  return result.rows[0];
}

/**
 * Get medication logs for a plan.
 */
export async function getPlanLogs(planId, userId, { page = 1, limit = 50 } = {}) {
  // Verify ownership with proper await
  const planCheck = await query(
    'SELECT id FROM medication_plans WHERE id = $1 AND user_id = $2',
    [planId, userId]
  );
  if (planCheck.rows.length === 0) {
    throw new AppError('Plan not found', 404, 'PLAN_NOT_FOUND');
  }

  const offset = (page - 1) * limit;
  const result = await query(
    `SELECT * FROM medication_logs
     WHERE plan_id = $1
     ORDER BY scheduled_time DESC
     LIMIT $2 OFFSET $3`,
    [planId, limit, offset]
  );

  return result.rows;
}

/**
 * Get all medication logs for a user (across all plans).
 */
export async function getUserMedicationLogs(
  userId,
  { date = null, page = 1, limit = 100 } = {}
) {
  const offset = (page - 1) * limit;
  const dateKey = normalizeDateKey(date);

  const clauses = ['p.user_id = $1'];
  const params = [userId];

  if (dateKey) {
    params.push(dateKey);
    const idx = params.length;
    clauses.push(`(l.occurrence_id LIKE '%' || $${idx} || ':%' OR l.scheduled_time::date = $${idx}::date)`);
  }

  params.push(limit, offset);
  const limitIdx = params.length - 1;
  const offsetIdx = params.length;

  const result = await query(
    `SELECT l.*, p.drug_name, p.dosage, p.pills_per_dose
     FROM medication_logs l
     JOIN medication_plans p ON p.id = l.plan_id
     WHERE ${clauses.join(' AND ')}
     ORDER BY l.scheduled_time DESC
     LIMIT $${limitIdx} OFFSET $${offsetIdx}`,
    params
  );

  const countParams = params.slice(0, params.length - 2);
  const countResult = await query(
    `SELECT COUNT(*)
     FROM medication_logs l
     JOIN medication_plans p ON p.id = l.plan_id
     WHERE ${clauses.join(' AND ')}`,
    countParams
  );

  return {
    logs: result.rows,
    total: Number.parseInt(countResult.rows[0].count, 10),
  };
}

/**
 * Build today's medication schedule (expanded per dose time) and merge
 * with existing logs to expose pending/taken/skipped/missed status.
 */
export async function getTodaySchedule(userId, { date = null } = {}) {
  const dateKey = normalizeDateKey(date) || new Date().toISOString().slice(0, 10);

  const plansResult = await query(
    `SELECT id, drug_name, dosage, pills_per_dose, frequency, times, notes
     FROM medication_plans
     WHERE user_id = $1
       AND is_active = true
       AND start_date <= $2::date
       AND (end_date IS NULL OR end_date >= $2::date)
     ORDER BY created_at DESC`,
    [userId, dateKey]
  );

  const plans = plansResult.rows;
  if (plans.length === 0) {
    return {
      date: dateKey,
      doses: [],
      summary: {
        total: 0,
        taken: 0,
        pending: 0,
        skipped: 0,
        missed: 0,
      },
    };
  }

  const doses = [];
  const occurrenceIds = [];

  for (const plan of plans) {
    const times = Array.isArray(plan.times) ? plan.times : [];
    for (const time of times) {
      const hhmm = String(time || '').slice(0, 5);
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(hhmm)) {
        continue;
      }
      const scheduledTime = `${dateKey}T${hhmm}:00.000Z`;
      const occurrenceId = `${plan.id}:${dateKey}:${hhmm}`;
      occurrenceIds.push(occurrenceId);
      doses.push({
        occurrenceId,
        planId: plan.id,
        drugName: plan.drug_name,
        dosage: plan.dosage,
        pillsPerDose: plan.pills_per_dose,
        frequency: plan.frequency,
        notes: plan.notes,
        time: hhmm,
        scheduledTime,
        status: 'pending',
        takenAt: null,
        note: null,
      });
    }
  }

  const logsResult = await query(
    `SELECT l.*
     FROM medication_logs l
     JOIN medication_plans p ON p.id = l.plan_id
     WHERE p.user_id = $1
       AND (l.occurrence_id = ANY($2::text[]) OR l.scheduled_time::date = $3::date)
     ORDER BY l.scheduled_time DESC`,
    [userId, occurrenceIds, dateKey]
  );

  const logByOccurrence = new Map();
  for (const log of logsResult.rows) {
    if (log.occurrence_id) {
      logByOccurrence.set(log.occurrence_id, log);
      continue;
    }

    const dt = toUtcDateAndTimeKey(log.scheduled_time);
    if (!dt) {
      continue;
    }
    const fallbackOccurrence = `${log.plan_id}:${dt.date}:${dt.time}`;
    logByOccurrence.set(fallbackOccurrence, log);
  }

  for (const dose of doses) {
    const log = logByOccurrence.get(dose.occurrenceId);
    if (!log) {
      continue;
    }
    dose.status = log.status || 'pending';
    dose.takenAt = log.taken_at || null;
    dose.note = log.note || null;
  }

  doses.sort((a, b) => {
    if (a.time !== b.time) {
      return a.time.localeCompare(b.time);
    }
    return a.drugName.localeCompare(b.drugName);
  });

  const summary = doses.reduce(
    (acc, dose) => {
      acc.total += 1;
      acc[dose.status] = (acc[dose.status] || 0) + 1;
      return acc;
    },
    {
      total: 0,
      taken: 0,
      pending: 0,
      skipped: 0,
      missed: 0,
    }
  );

  return {
    date: dateKey,
    doses,
    summary,
  };
}
