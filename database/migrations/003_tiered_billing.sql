-- LogicHive Migration: Tiered Subscription Infrastructure (Phase 5)
-- Goal: Add quota and plan information to organizations.

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_type TEXT DEFAULT 'free';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'; -- active, frozen
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS request_limit INTEGER DEFAULT 100;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS current_usage_count INTEGER DEFAULT 0;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_start_date TIMESTAMPTZ DEFAULT NOW();

-- Function to reset usage (to be called by a cron job or on month change logic)
CREATE OR REPLACE FUNCTION reset_organization_usage(target_org_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE organizations 
  SET current_usage_count = 0 
  WHERE id = target_org_id;
END;
$$ LANGUAGE plpgsql;
