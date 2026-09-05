-- staff's key was staff_id live while call_attempts.va_id and status_log.va_id
-- both referenced it. Renamed to va_id, and name made unique because the
-- importer identifies a VA by name. Applied live 2026-09-05.
ALTER TABLE staff RENAME COLUMN staff_id TO va_id;
ALTER TABLE staff DROP CONSTRAINT IF EXISTS staff_name_key;
ALTER TABLE staff ADD CONSTRAINT staff_name_key UNIQUE (name);
