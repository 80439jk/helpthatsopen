-- organizations had only a primary key, so the loader's ON CONFLICT DO NOTHING
-- never fired and every program created a fresh organization. 100 NC county
-- offices became 300 rows. Same defect that turned 44 Texas organizations into
-- 119; fixed in 001_schema.sql, never applied live.
WITH canon AS (
  SELECT org_id, min(org_id::text) OVER (PARTITION BY name, org_type) AS keep_txt
  FROM organizations)
UPDATE programs p SET org_id = c.keep_txt::uuid
FROM canon c WHERE p.org_id = c.org_id AND c.keep_txt <> c.org_id::text;
DELETE FROM organizations o
WHERE NOT EXISTS (SELECT 1 FROM programs p WHERE p.org_id = o.org_id);
ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_name_org_type_key;
ALTER TABLE organizations ADD CONSTRAINT organizations_name_org_type_key UNIQUE (name, org_type);
