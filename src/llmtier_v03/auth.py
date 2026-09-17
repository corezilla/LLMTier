from __future__ import annotations

import hmac
import ipaddress
import os
from dataclasses import dataclass

from .errors import ApiError


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    role: str


_TRUSTED_LAN_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
)


def unauthenticated_principal(client_address: str, headers, role: str) -> Principal | None:
    """Return the explicitly enabled no-login principal for local test deployments."""
    if headers.get("Authorization"):
        return None
    try:
        address = ipaddress.ip_address(client_address.split("%", 1)[0])
    except ValueError:
        return None
    if os.environ.get("LLMTIER_DEV_MODE") == "1" and address.is_loopback:
        return Principal("loopback-operator" if role == "admin" else "loopback-consumer", role)
    if os.environ.get("LLMTIER_TRUSTED_LAN_MODE") == "1" and (
        address.is_loopback or any(address in network for network in _TRUSTED_LAN_NETWORKS)
    ):
        return Principal("trusted-lan-operator" if role == "admin" else "trusted-lan-consumer", role)
    return None


def _configured_token(role: str) -> str | None:
    name = "LLMTIER_ADMIN_TOKEN" if role == "admin" else "LLMTIER_DATA_TOKEN"
    value = os.environ.get(name)
    if value:
        return value
    if os.environ.get("LLMTIER_DEV_MODE") == "1":
        return "dev-admin" if role == "admin" else "dev-data"
    return None


def authenticate(headers, role: str) -> Principal:
    configured = _configured_token(role)
    if configured is None:
        raise ApiError(503, "auth_not_configured", "Authentication is not configured")
    raw = headers.get("Authorization", "")
    if not raw.startswith("Bearer "):
        raise ApiError(401, "authentication_required", "Bearer authentication is required")
    supplied = raw[7:]
    if not hmac.compare_digest(supplied, configured):
        raise ApiError(403, "permission_denied", "The credential is not authorized")
    principal = headers.get("X-Principal-ID") or ("operator" if role == "admin" else "consumer")
    return Principal(principal_id=principal[:128], role=role)
