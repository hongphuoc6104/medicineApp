/**
 * Plan service — medication plan CRUD + medication logs.
 */
import { query } from '../config/database.js';
import { AppError } from '../utils/errors.js';

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
  const activeFilter = activeOnly ? 'AND is_active = true' : '';

  const result = await query(
    `SELECT * FROM medication_plans
     WHERE user_id = $1 ${activeFilter}
     ORDER BY created_at DESC
     LIMIT $2 OFFSET $3`,
    [userId, limit, offset]
  );

  const countResult = await query(
    `SELECT COUNT(*) FROM medication_plans
     WHERE user_id = $1 ${activeFilter}`,
    [userId]
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

  const allowed = ['drug_name', 'dosage', 'frequency', 'times',
    'pills_per_dose', 'total_days', 'start_date', 'end_date',
    'is_active', 'notes'];
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

  const result = await query(
    `INSERT INTO medication_logs (plan_id, scheduled_time, taken_at, status, note)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING *`,
    [
      planId,
      data.scheduledTime,
      data.status === 'taken' ? new Date().toISOString() : null,
      data.status,
      data.note || null,
    ]
  );
  return result.rows[0];
}

/**
 * Get medication logs for a plan.
 */
export async function getPlanLogs(planId, userId, { page = 1, limit = 50 } = {}) {
  // Verify ownership
  await query(
    'SELECT id FROM medication_plans WHERE id = $1 AND user_id = $2',
    [planId, userId]
  ).then(r => {
    if (r.rows.length === 0) throw new AppError('Plan not found', 404, 'PLAN_NOT_FOUND');
  });

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
