from __future__ import annotations

from typing import Any

from llm_tier.client import TierClient
from llm_tier.tier_model import TierCallRequest, TierCallResult, TierStatsQuery, TierStatsRow


_TIER_INSTANCE: TierCore | None = None


# Purpose: Return the process-local facade that delegates every operation to the independent Tier HTTP process.
# Inputs: None.
# Outputs: A reusable TierCore facade.
def get_tier() -> TierCore:
    global _TIER_INSTANCE
    if _TIER_INSTANCE is None:
        _TIER_INSTANCE = TierCore()
    return _TIER_INSTANCE


# Purpose: Preserve the public Tier facade while enforcing TierClient as the only execution path.
# Inputs: Optional injected TierClient for composition and tests.
# Outputs: Delegated call, job, configuration, and statistics operations.
class TierCore:
    # Purpose: Construct a client-only Tier facade without probing or creating local backends.
    # Inputs: Optional TierClient; defaults to the configured HTTP client.
    # Outputs: Initialized TierCore.
    def __init__(self, client: TierClient | None = None) -> None:
        self._client = client or TierClient()

    @property
    # Purpose: Report the facade's single supported transport mode.
    # Inputs: None.
    # Outputs: Always True because embedded mode no longer exists.
    def is_client_mode(self) -> bool:
        return True

    # Purpose: Execute one synchronous Tier request through the independent service.
    # Inputs: Normalized TierCallRequest.
    # Outputs: TierCallResult returned by TierClient.
    def call(self, req: TierCallRequest) -> TierCallResult:
        return self._client.call(req)

    # Purpose: Submit one asynchronous Tier request through the independent service.
    # Inputs: Normalized TierCallRequest.
    # Outputs: Server-owned job ID.
    def call_async(self, req: TierCallRequest) -> str:
        return self._client.call_async(req)

    # Purpose: Read one server-owned job result.
    # Inputs: Non-empty job ID.
    # Outputs: Terminal result or None while pending.
    def get_result(self, job_id: str) -> TierCallResult | None:
        return self._client.get_result(job_id)

    # Purpose: Reload Tier configuration in the independent process.
    # Inputs: None.
    # Outputs: True when the server accepted and completed the reload.
    def reload_config(self) -> bool:
        response = self._client.reload_config()
        return bool(response.get("ok", False))

    # Purpose: Return server statistics for one Tier label.
    # Inputs: Tier name used as a display/filter context.
    # Outputs: Dictionary containing the requested Tier and authoritative stats payload.
    def get_tier_info(self, tier_name: str) -> dict[str, Any]:
        return {"tier": tier_name, "stats": self._client.get_stats(tier=tier_name)}

    # Purpose: Clear exhausted state in the independent Tier process.
    # Inputs: Optional Tier name; empty means all tiers.
    # Outputs: None after the server operation returns.
    def reset_exhausted(self, tier_name: str = "") -> None:
        self._client.reset_exhausted(tier_name)

    # Purpose: Convert authoritative server stats rows into TierStatsRow values.
    # Inputs: Optional scope and backend filters.
    # Outputs: Matching TierStatsRow list.
    def get_stats(self, query: TierStatsQuery | None = None) -> list[TierStatsRow]:
        resolved = query or TierStatsQuery()
        raw = self._client.get_stats(
            project=resolved.project_name,
            stage=resolved.stage_name,
            phase=resolved.phase_name,
            task_id=resolved.task_id,
            task_key=resolved.task_key,
            tier=resolved.tier,
            backend=resolved.backend,
            role=resolved.role_name,
        )
        stats = raw.get("stats", {}) if isinstance(raw, dict) else {}
        rows = stats.get("rows", []) if isinstance(stats, dict) else []
        return [TierStatsRow(**row) for row in rows if isinstance(row, dict)]

    # Purpose: Return the authoritative aggregate statistics summary.
    # Inputs: None.
    # Outputs: Server summary dictionary.
    def get_summary(self) -> dict[str, Any]:
        raw = self._client.get_stats()
        stats = raw.get("stats", {}) if isinstance(raw, dict) else {}
        summary = stats.get("summary", {}) if isinstance(stats, dict) else {}
        return dict(summary) if isinstance(summary, dict) else {}

    # Purpose: Report whether the configured Tier HTTP service is enabled.
    # Inputs: None.
    # Outputs: False when unavailable; otherwise the server tier_enabled flag.
    def is_enabled(self) -> bool:
        try:
            health = self._client.get_health()
        except Exception:
            return False
        return bool(health.get("tier_enabled", False))
