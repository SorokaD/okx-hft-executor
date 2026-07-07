-- =============================================================================
-- OPTIONAL: полный сброс схемы okx_exec (только dev / пустая БД).
-- ВНИМАНИЕ: удаляет все данные в okx_exec.*
--
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/postgres/000_reset_okx_exec.sql
-- =============================================================================

DROP SCHEMA IF EXISTS okx_exec CASCADE;
