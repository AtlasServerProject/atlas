\set ON_ERROR_STOP on
\getenv migration_password ATLAS_MIGRATION_PASSWORD
\getenv runtime_password ATLAS_DB_PASSWORD
-- Only run on a fresh, dedicated API database. Passwords arrive through the process environment.
SELECT format('CREATE ROLE atlas_api_migrator LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE', :'migration_password') \gexec
SELECT format('CREATE ROLE atlas_api_runtime LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE', :'runtime_password') \gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE :DBNAME FROM PUBLIC;
GRANT CONNECT ON DATABASE :DBNAME TO atlas_api_migrator, atlas_api_runtime;
CREATE SCHEMA atlas_web AUTHORIZATION atlas_api_migrator;
GRANT USAGE ON SCHEMA atlas_web TO atlas_api_runtime;
