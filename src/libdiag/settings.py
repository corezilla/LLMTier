"""Feature: diagnostic global switches (diagnostic_settings)."""
from __future__ import annotations

from http_api.errors import ApiError
from util.store import Store, txn


class SettingsDiagnostics:
    def __init__(self, store: Store):
        self.store = store

    def switches(self) -> dict[str, bool]:
        row = self.store.one("SELECT snapshots_enabled,stats_enabled FROM diagnostic_settings WHERE singleton=1")
        return {"snapshots_enabled": bool(row["snapshots_enabled"]), "stats_enabled": bool(row["stats_enabled"])}

    def set_switches(self, snapshots_enabled: bool | None = None, stats_enabled: bool | None = None, conn=None) -> dict[str, bool]:
        for name, value in (("snapshots_enabled", snapshots_enabled), ("stats_enabled", stats_enabled)):
            if value is not None and not isinstance(value, bool):
                raise ApiError(400, "invalid_request", f"{name} must be a boolean", param=name)
        current = self.switches()
        snapshots = current["snapshots_enabled"] if snapshots_enabled is None else snapshots_enabled
        stats = current["stats_enabled"] if stats_enabled is None else stats_enabled
        with txn(self.store, conn) as conn:
            conn.execute("UPDATE diagnostic_settings SET snapshots_enabled=?,stats_enabled=? WHERE singleton=1", (int(snapshots), int(stats)))
        return self.switches()
