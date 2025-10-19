-- Initialize pgvector extension for RCA Engine
-- This script runs automatically when the PostgreSQL container is first created

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant necessary permissions to rca_user
-- GRANT ALL PRIVILEGES ON SCHEMA public TO rca_user;

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'pgvector extension successfully installed!';
END $$;
