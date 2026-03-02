-- LogicHive Migration: AI Evaluation Metrics (Phase 5)
-- Goal: Store quantitative test results and reliability scores.

ALTER TABLE logichive_functions ADD COLUMN IF NOT EXISTS test_metrics JSONB DEFAULT '{}';
ALTER TABLE logichive_functions ADD COLUMN IF NOT EXISTS reliability_score FLOAT DEFAULT 0.0;

-- Update the match_functions RPC to return reliability_score
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
  similarity float,
  reliability_score float
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
    1 - (f.embedding <=> query_embedding) AS similarity,
    f.reliability_score
  FROM logichive_functions f
  WHERE (1 - (f.embedding <=> query_embedding) > match_threshold)
    AND f.organization_id = target_org_id
  ORDER BY f.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
