/**
 * Test database helpers.
 * Uses same PostgreSQL instance but cleans up data between tests.
 */
import { pool, query } from '../../src/config/database.js';

/**
 * Clean test data by email prefix to avoid touching real data.
 */
export async function cleanTestUsers(emailPrefix = 'test_ci_') {
  await query(`DELETE FROM users WHERE email LIKE $1`, [`${emailPrefix}%`]);
}

/**
 * Create a test user and return token data.
 */
export async function createTestUser(suffix = '1') {
  const email = `test_ci_${suffix}@example.com`;
  const password = 'Test1234!';
  const name = `Test User ${suffix}`;

  // Clean existing
  await query('DELETE FROM users WHERE email = $1', [email]);

  const { register, login } = await import('../../src/services/auth.service.js');
  await register({ email, password, name });
  const tokens = await login({ email, password });
  return { email, password, name, ...tokens };
}

export { pool, query };
