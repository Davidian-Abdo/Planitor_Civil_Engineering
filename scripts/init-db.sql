-- Initialize PostgreSQL database with extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_tasks_discipline ON base_tasks(discipline);
CREATE INDEX IF NOT EXISTS idx_tasks_resource_type ON base_tasks(resource_type);

-- Create read-only user for backups (optional)
CREATE USER readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE construction_db TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;