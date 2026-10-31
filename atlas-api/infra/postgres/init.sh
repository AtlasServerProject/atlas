#!/bin/sh
set -eu
: "${ATLAS_MIGRATION_PASSWORD:?Set the dedicated migration password}"
: "${ATLAS_DB_PASSWORD:?Set the dedicated runtime password}"
psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /atlas-provision.sql
