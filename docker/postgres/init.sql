-- PostgreSQL initialization script for Tarot project
-- This script runs when the database container starts for the first time

-- Create database if it doesn't exist
-- Note: The main database is created by the POSTGRES_DB environment variable

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON DATABASE tarot_db TO tarot_user;