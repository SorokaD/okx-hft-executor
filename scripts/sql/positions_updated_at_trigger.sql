-- Apply via psql (do NOT paste this whole file into PowerShell as commands).
-- Recommended (Windows):
--   powershell -File scripts/sql/apply_positions_updated_at_trigger.ps1
-- Or manually:
--   psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/sql/positions_updated_at_trigger.sql

create schema if not exists okx_exec;

create or replace function okx_exec.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists trg_positions_set_updated_at on okx_exec.positions;

create trigger trg_positions_set_updated_at
before update on okx_exec.positions
for each row
execute procedure okx_exec.set_updated_at();

