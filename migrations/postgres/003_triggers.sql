-- =============================================================================
-- Триггеры и вспомогательные функции
-- =============================================================================

CREATE OR REPLACE FUNCTION okx_exec.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_positions_set_updated_at ON okx_exec.positions;

CREATE TRIGGER trg_positions_set_updated_at
    BEFORE UPDATE ON okx_exec.positions
    FOR EACH ROW
    EXECUTE PROCEDURE okx_exec.set_updated_at();
