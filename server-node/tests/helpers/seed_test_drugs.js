import { query } from './db.js';

export async function seedTestDrugs() {
  await query(`
    INSERT INTO drug_cache (drug_name, source, data, expires_at)
    VALUES 
      ('paracetamol 500mg', 'ddi', '{"name":"paracetamol 500mg"}', NOW() + INTERVAL '7 days'),
      ('Hapacol 650', 'ddi', '{"name":"Hapacol 650"}', NOW() + INTERVAL '7 days'),
      ('Hapacol', 'ddi', '{"name":"Hapacol"}', NOW() + INTERVAL '7 days'),
      ('thuoc 1', 'ddi', '{"name":"thuoc 1"}', NOW() + INTERVAL '7 days'),
      ('thuoc 2', 'ddi', '{"name":"thuoc 2"}', NOW() + INTERVAL '7 days'),
      ('thuoc 3', 'ddi', '{"name":"thuoc 3"}', NOW() + INTERVAL '7 days'),
      ('thuoc 4', 'ddi', '{"name":"thuoc 4"}', NOW() + INTERVAL '7 days'),
      ('thuoc 5', 'ddi', '{"name":"thuoc 5"}', NOW() + INTERVAL '7 days'),
      ('thuoc 6', 'ddi', '{"name":"thuoc 6"}', NOW() + INTERVAL '7 days')
    ON CONFLICT (drug_name, source) DO NOTHING;
  `);
}

export async function cleanupTestDrugs() {
  await query(`
    DELETE FROM drug_cache 
    WHERE drug_name IN (
      'paracetamol 500mg', 'Hapacol 650', 'Hapacol', 
      'thuoc 1', 'thuoc 2', 'thuoc 3', 'thuoc 4', 'thuoc 5', 'thuoc 6'
    ) AND source = 'ddi';
  `);
}
