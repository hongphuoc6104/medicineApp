/**
 * Unit tests — plan.service.js
 */
import { cleanTestUsers, pool, query } from '../helpers/db.js';
import * as authService from '../../src/services/auth.service.js';
import * as planService from '../../src/services/plan.service.js';

const PREFIX = 'test_ci_plan_';
const EMAIL = `${PREFIX}user@example.com`;

let userId;

async function ensureMedicationLogOccurrenceSchema() {
  await query('ALTER TABLE medication_logs ADD COLUMN IF NOT EXISTS occurrence_id VARCHAR(120)');
  await query('DROP INDEX IF EXISTS uq_logs_plan_occurrence');
  await query('CREATE UNIQUE INDEX IF NOT EXISTS uq_logs_plan_occurrence_all ON medication_logs(plan_id, occurrence_id)');
}

beforeAll(async () => {
  await ensureMedicationLogOccurrenceSchema();
  await cleanTestUsers(PREFIX);
  // register() returns { id, email, name, created_at } directly (not { user: {...} })
  const user = await authService.register({ email: EMAIL, password: 'Test1234!', name: 'Plan Test' });
  userId = user.id;
});

afterAll(async () => {
  await cleanTestUsers(PREFIX);
  await pool.end();
});

describe('createPlan()', () => {
  test('should create a medication plan', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Paracetamol 500mg',
      frequency: 'twice_daily',
      times: ['08:00', '20:00'],
      startDate: '2026-03-10',
      totalDays: 7,
    });
    expect(plan.id).toBeDefined();
    expect(plan.drug_name).toBe('Paracetamol 500mg');
    expect(plan.user_id).toBe(userId);
    expect(plan.is_active).toBe(true);
  });
});

describe('getUserPlans()', () => {
  test('should return only active plans by default', async () => {
    // Create one more plan then delete it
    const activePlan = await planService.createPlan(userId, {
      drugName: 'Amoxicillin',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    // Deactivate it
    await planService.deletePlan(userId, activePlan.id);

    const { plans, total } = await planService.getUserPlans(userId, { activeOnly: true });
    expect(plans.every(p => p.is_active === true)).toBe(true);
    // Total should only count active
    const allRes = await planService.getUserPlans(userId, { activeOnly: false });
    expect(allRes.total).toBeGreaterThan(total);
  });

  test('should paginate correctly', async () => {
    const { plans } = await planService.getUserPlans(userId, { page: 1, limit: 1 });
    expect(plans.length).toBeLessThanOrEqual(1);
  });
});

describe('updatePlan()', () => {
  test('should update allowed fields', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Ibuprofen 400mg',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    const updated = await planService.updatePlan(userId, plan.id, {
      notes: 'Uống sau ăn',
      pillsPerDose: 2,
    });
    expect(updated.notes).toBe('Uống sau ăn');
    expect(updated.pills_per_dose).toBe(2);
  });

  test('should throw 400 if no fields to update', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Vitamin C',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    await expect(
      planService.updatePlan(userId, plan.id, {})
    ).rejects.toMatchObject({ statusCode: 400, code: 'NO_UPDATES' });
  });

  test('should throw 404 for wrong user (ownership check)', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Aspirin',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    const fakeUserId = '00000000-0000-0000-0000-000000000000';
    await expect(
      planService.updatePlan(fakeUserId, plan.id, { notes: 'hack' })
    ).rejects.toMatchObject({ statusCode: 404, code: 'PLAN_NOT_FOUND' });
  });
});

describe('deletePlan()', () => {
  test('should soft-delete plan (set is_active=false)', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Cetirizine',
      frequency: 'daily',
      times: ['22:00'],
      startDate: '2026-03-10',
    });
    await planService.deletePlan(userId, plan.id);

    const result = await query(
      'SELECT is_active FROM medication_plans WHERE id = $1',
      [plan.id]
    );
    expect(result.rows[0].is_active).toBe(false);
  });
});

describe('logMedication()', () => {
  test('should log a taken dose', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Omeprazole',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    const log = await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'taken',
    });
    expect(log.status).toBe('taken');
    expect(log.taken_at).not.toBeNull();
  });

  test('should set taken_at=null for missed dose', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Metformin',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    const log = await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'missed',
    });
    expect(log.status).toBe('missed');
    expect(log.taken_at).toBeNull();
  });

  test('should upsert log by occurrenceId (idempotent)', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Amlodipine',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });

    const occurrenceId = `${plan.id}:2026-03-10:08:00`;
    const first = await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'skipped',
      occurrenceId,
    });
    const second = await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'taken',
      occurrenceId,
    });

    expect(second.id).toBe(first.id);
    expect(second.status).toBe('taken');
  });
});

describe('getPlanLogs()', () => {
  test('should return logs for a plan', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Atorvastatin',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'taken',
    });
    const logs = await planService.getPlanLogs(plan.id, userId);
    expect(logs.length).toBeGreaterThan(0);
  });

  test('should throw 404 for unauthorized plan access', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Test Drug',
      frequency: 'daily',
      times: ['08:00'],
      startDate: '2026-03-10',
    });
    const fakeUserId = '00000000-0000-0000-0000-000000000000';
    await expect(
      planService.getPlanLogs(plan.id, fakeUserId)
    ).rejects.toMatchObject({ statusCode: 404 });
  });
});

describe('getTodaySchedule()', () => {
  test('should return expanded doses with status summary', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Rosuvastatin',
      frequency: 'twice_daily',
      times: ['08:00', '20:00'],
      startDate: '2026-03-10',
    });

    await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-10T08:00:00Z',
      status: 'taken',
      occurrenceId: `${plan.id}:2026-03-10:08:00`,
    });

    const schedule = await planService.getTodaySchedule(userId, {
      date: '2026-03-10',
    });

    expect(schedule.date).toBe('2026-03-10');
    expect(schedule.doses.length).toBeGreaterThan(0);
    expect(schedule.summary.total).toBe(schedule.doses.length);
    expect(schedule.summary.taken).toBeGreaterThanOrEqual(1);
  });
});

describe('getUserMedicationLogs()', () => {
  test('should return cross-plan logs for user', async () => {
    const plan = await planService.createPlan(userId, {
      drugName: 'Perindopril',
      frequency: 'daily',
      times: ['07:00'],
      startDate: '2026-03-11',
    });

    await planService.logMedication(plan.id, userId, {
      scheduledTime: '2026-03-11T07:00:00Z',
      status: 'taken',
      occurrenceId: `${plan.id}:2026-03-11:07:00`,
    });

    const result = await planService.getUserMedicationLogs(userId, {
      date: '2026-03-11',
      page: 1,
      limit: 20,
    });

    expect(result.total).toBeGreaterThan(0);
    expect(result.logs.length).toBeGreaterThan(0);
    expect(result.logs[0].drug_name).toBeDefined();
  });
});
