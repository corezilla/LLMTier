PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1), schema_version INTEGER NOT NULL,
  initialized_at TEXT NOT NULL, bootstrap_sha256 TEXT
);
CREATE TABLE IF NOT EXISTS providers (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL CHECK(kind IN ('cloud','local')),
  endpoint TEXT NOT NULL, secret_ref TEXT, enabled INTEGER NOT NULL, version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS deployments (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, provider_id TEXT NOT NULL REFERENCES providers(id),
  backend_model TEXT NOT NULL, capabilities_json TEXT NOT NULL, enabled INTEGER NOT NULL,
  health TEXT NOT NULL DEFAULT 'unknown', version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS service_levels (
  id TEXT PRIMARY KEY, enabled INTEGER NOT NULL, capabilities_json TEXT NOT NULL, version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS service_level_deployments (
  level_id TEXT NOT NULL REFERENCES service_levels(id) ON DELETE CASCADE,
  deployment_id TEXT NOT NULL REFERENCES deployments(id), ordinal INTEGER NOT NULL,
  PRIMARY KEY(level_id,deployment_id), UNIQUE(level_id,ordinal)
);
CREATE TABLE IF NOT EXISTS deployment_runtime_profiles (
  deployment_id TEXT PRIMARY KEY REFERENCES deployments(id) ON DELETE CASCADE,
  max_in_flight INTEGER NOT NULL DEFAULT 1, connect_timeout_ms INTEGER NOT NULL DEFAULT 30000,
  stream_idle_timeout_ms INTEGER NOT NULL DEFAULT 60000, version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS provider_usage_profiles (
  provider_id TEXT PRIMARY KEY REFERENCES providers(id) ON DELETE CASCADE,
  usage_provider TEXT NOT NULL DEFAULT 'none', usage_api_key_ref TEXT,
  usage_access_key_ref TEXT, usage_secret_key_ref TEXT,
  max_concurrent_requests INTEGER NOT NULL DEFAULT 1,
  min_request_interval_ms INTEGER NOT NULL DEFAULT 0,
  requests_per_minute INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS provider_usage_snapshots (
  provider_id TEXT PRIMARY KEY REFERENCES providers(id) ON DELETE CASCADE,
  snapshot_json TEXT NOT NULL, checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provider_request_bindings (
  principal_id TEXT NOT NULL, request_id TEXT NOT NULL,
  provider_id TEXT NOT NULL REFERENCES providers(id),
  deployment_id TEXT NOT NULL REFERENCES deployments(id), bound_at TEXT NOT NULL,
  provider_request_id TEXT,
  PRIMARY KEY(principal_id,request_id)
);
CREATE TABLE IF NOT EXISTS usage_obligations (
  principal_id TEXT NOT NULL, request_id TEXT NOT NULL, model TEXT NOT NULL, endpoint TEXT NOT NULL,
  recorded_at TEXT NOT NULL, dispatch_authorized_at TEXT, PRIMARY KEY(principal_id,request_id)
);
CREATE TABLE IF NOT EXISTS usage_record_versions (
  principal_id TEXT NOT NULL, request_id TEXT NOT NULL, record_version INTEGER NOT NULL,
  is_final INTEGER NOT NULL, model TEXT NOT NULL, endpoint TEXT NOT NULL, recorded_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, measurement_status TEXT NOT NULL, source TEXT NOT NULL,
  input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER, cached_input_tokens INTEGER,
  cache_write_tokens INTEGER, reasoning_tokens INTEGER,
  PRIMARY KEY(principal_id,request_id,record_version),
  FOREIGN KEY(principal_id,request_id) REFERENCES usage_obligations(principal_id,request_id)
);
CREATE TABLE IF NOT EXISTS usage_heads (
  principal_id TEXT NOT NULL, request_id TEXT NOT NULL, head_record_version INTEGER NOT NULL,
  updated_at TEXT NOT NULL, PRIMARY KEY(principal_id,request_id),
  FOREIGN KEY(principal_id,request_id,head_record_version)
    REFERENCES usage_record_versions(principal_id,request_id,record_version)
);
CREATE TABLE IF NOT EXISTS query_snapshots (
  snapshot_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, snapshot_kind TEXT NOT NULL,
  filter_digest TEXT NOT NULL, authorization_digest TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS query_snapshot_items (
  snapshot_id TEXT NOT NULL REFERENCES query_snapshots(snapshot_id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL, request_id TEXT NOT NULL, record_version INTEGER,
  frozen_view_json TEXT, etag TEXT, PRIMARY KEY(snapshot_id,ordinal), UNIQUE(snapshot_id,request_id)
);
CREATE TABLE IF NOT EXISTS probe_results (
  deployment_id TEXT PRIMARY KEY REFERENCES deployments(id) ON DELETE CASCADE,
  status TEXT NOT NULL, checked_at TEXT NOT NULL, request_id TEXT NOT NULL, detail TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL,
  result TEXT NOT NULL, created_at TEXT NOT NULL, request_id TEXT
);
CREATE TABLE IF NOT EXISTS operational_logs (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, level TEXT NOT NULL, module TEXT NOT NULL,
  event TEXT NOT NULL, message TEXT NOT NULL CHECK(length(message)<=512), request_id TEXT
);
INSERT OR IGNORE INTO schema_meta(singleton,schema_version,initialized_at) VALUES(1,2,strftime('%Y-%m-%dT%H:%M:%fZ','now'));
INSERT OR IGNORE INTO provider_usage_profiles(provider_id,usage_provider)
  SELECT id, CASE WHEN kind='local' THEN 'local' ELSE 'none' END FROM providers;
