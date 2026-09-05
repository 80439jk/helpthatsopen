-- NC county DSS offices and several FL county human-services departments are
-- government agencies; org_type had no value for that. Recording what a
-- PROVIDER is does not imply affiliation -- it is what lets the site carry the
-- right disclaimer and keep GovernmentService out of our own schema.org entity.
ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_org_type_check;
ALTER TABLE organizations ADD CONSTRAINT organizations_org_type_check
  CHECK (org_type = ANY (ARRAY[
    'caa','pha','food_bank','food_pantry','faith','municipal_utility','co_op',
    'nonprofit','aaa','clinic','school_district','aic_211','government','other']));
