-- MetricLens AI — Canonical PostgreSQL schema (time-series load-forecasting domain)
-- Idempotent: safe to run repeatedly. Mirrors ./docs/04_database_design.md.
-- ---------------------------------------------------------------------------

-- ENUM domains (guarded for idempotency; CREATE TYPE has no IF NOT EXISTS).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'host_env') THEN
        CREATE TYPE host_env AS ENUM ('PROD', 'STAGING', 'DEV');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'forecast_metric') THEN
        CREATE TYPE forecast_metric AS ENUM ('CPU', 'MEM', 'NET_IN', 'NET_OUT');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS hosts (
    id          VARCHAR(36)  PRIMARY KEY,
    hostname    VARCHAR(255) NOT NULL UNIQUE,
    environment host_env     NOT NULL DEFAULT 'PROD',
    vcpu_count  INTEGER      NOT NULL CHECK (vcpu_count BETWEEN 1 AND 256),
    memory_mb   INTEGER      NOT NULL CHECK (memory_mb BETWEEN 256 AND 4194304),
    created_at  TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS metrics (
    id           BIGINT        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host_id      VARCHAR(36)   NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    ts           TIMESTAMP     NOT NULL,
    cpu_pct      NUMERIC(5,2)  NOT NULL CHECK (cpu_pct  BETWEEN 0 AND 100),
    mem_pct      NUMERIC(5,2)  NOT NULL CHECK (mem_pct  BETWEEN 0 AND 100),
    net_in_kbps  NUMERIC(12,2) NOT NULL CHECK (net_in_kbps  >= 0),
    net_out_kbps NUMERIC(12,2) NOT NULL CHECK (net_out_kbps >= 0),
    CONSTRAINT uq_metrics_host_ts UNIQUE (host_id, ts)
);
CREATE INDEX IF NOT EXISTS ix_metrics_host_ts ON metrics (host_id, ts);

CREATE TABLE IF NOT EXISTS forecasts (
    id              VARCHAR(36)     PRIMARY KEY,
    host_id         VARCHAR(36)     NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    metric          forecast_metric NOT NULL,
    generated_at    TIMESTAMP       NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    horizon_minutes INTEGER         NOT NULL CHECK (horizon_minutes BETWEEN 1 AND 10080),
    model           VARCHAR(50)     NOT NULL DEFAULT 'STL_HOLTWINTERS',
    predicted_value NUMERIC(12,2)   NOT NULL,
    lower_bound     NUMERIC(12,2)   NOT NULL,
    upper_bound     NUMERIC(12,2)   NOT NULL,
    mape            NUMERIC(5,2)    CHECK (mape >= 0)
);
CREATE INDEX IF NOT EXISTS ix_forecasts_host ON forecasts (host_id, generated_at);

CREATE TABLE IF NOT EXISTS recommendations (
    id                    VARCHAR(36)   PRIMARY KEY,
    host_id               VARCHAR(36)   NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    generated_at          TIMESTAMP     NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    current_vcpu          INTEGER       NOT NULL CHECK (current_vcpu >= 1),
    recommended_vcpu      INTEGER       NOT NULL CHECK (recommended_vcpu >= 1),
    current_memory_mb     INTEGER       NOT NULL CHECK (current_memory_mb >= 256),
    recommended_memory_mb INTEGER       NOT NULL CHECK (recommended_memory_mb >= 256),
    est_cost_saving_pct   NUMERIC(5,2)  NOT NULL DEFAULT 0 CHECK (est_cost_saving_pct BETWEEN -100 AND 100),
    slo_confidence        NUMERIC(5,2)  NOT NULL CHECK (slo_confidence BETWEEN 0 AND 100)
);
CREATE INDEX IF NOT EXISTS ix_recommendations_host ON recommendations (host_id, generated_at);
