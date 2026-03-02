-- LogicHive Migration: Org-Hive (Phase 5)
-- Goal: Introduce multi-tenancy and organization-level isolation.

-- 1. Create Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    api_key_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Add organization_id to functions table
ALTER TABLE logichive_functions ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- 3. Update match_functions RPC to include organizational filtering
-- (First, drop the old one to change signature)
DROP FUNCTION IF EXISTS match_functions(vector(768), float, int);

CREATE OR REPLACE FUNCTION match_functions (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  target_org_id uuid
)
RETURNS TABLE (
  name text,
  code text,
  description text,
  tags text[],
  call_count int,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    f.name,
    f.code,
    f.description,
    f.tags,
    f.call_count,
    1 - (f.embedding <=> query_embedding) AS similarity
  FROM logichive_functions f
  WHERE (1 - (f.embedding <=> query_embedding) > match_threshold)
    AND f.organization_id = target_org_id
  ORDER BY f.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. Set a 'Public' organization for existing data (Optional/Cleanup)
-- INSERT INTO organizations (name, api_key_hash) VALUES ('Public Hive', 'public_hash');
-- UPDATE logichive_functions SET organization_id = (SELECT id FROM organizations WHERE name = 'Public Hive') WHERE organization_id IS NULL;
