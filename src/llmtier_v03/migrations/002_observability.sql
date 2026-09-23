-- 002_observability.sql — LT-OBS 可观测性与调试能力（需求 llmtier-observability-debug-requirements-v0.1）
CREATE TABLE IF NOT EXISTS diagnostic_settings (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  snapshots_enabled INTEGER NOT NULL DEFAULT 0,
  stats_enabled INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO diagnostic_settings VALUES(1,0,0);

CREATE TABLE IF NOT EXISTS diagnostic_snapshots (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  upstream_url TEXT NOT NULL,
  backend_model TEXT,
  http_status INTEGER,
  latency_ms REAL,
  error_summary TEXT,
  model TEXT,
  deployment_id TEXT,
  snapshot_type TEXT NOT NULL DEFAULT 'upstream'
);
CREATE INDEX IF NOT EXISTS idx_diag_snapshots_request ON diagnostic_snapshots(request_id);
CREATE INDEX IF NOT EXISTS idx_diag_snapshots_captured ON diagnostic_snapshots(captured_at);

CREATE TABLE IF NOT EXISTS diagnostic_injections (
  id TEXT PRIMARY KEY,
  deployment_id TEXT NOT NULL,
  injection_type TEXT NOT NULL,
  fault_status INTEGER,
  fault_body TEXT,
  delay_ms INTEGER,
  retry_after_sec INTEGER,
  stream_terminate_after_events INTEGER,
  malformed_after_events INTEGER,
  malformed_event_type TEXT,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  UNIQUE(deployment_id, injection_type)
);

CREATE TABLE IF NOT EXISTS data_plane_stats (
  stat_hour TEXT NOT NULL,
  deployment_id TEXT,
  model TEXT,
  status TEXT NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(stat_hour, deployment_id, model, status)
);

CREATE TABLE IF NOT EXISTS data_plane_latency_samples (
  stat_hour TEXT NOT NULL,
  deployment_id TEXT,
  model TEXT,
  latency_ms REAL NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_samples_lookup ON data_plane_latency_samples(stat_hour, deployment_id, model);

CREATE TABLE IF NOT EXISTS trace_events (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  stage_timestamp TEXT NOT NULL,
  detail TEXT,
  correlation_id TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trace_request ON trace_events(request_id);
CREATE INDEX IF NOT EXISTS idx_trace_correlation ON trace_events(correlation_id);
