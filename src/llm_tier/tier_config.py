from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from llm_tier.tier_model import TierAccount, TierModel


# Purpose: Validate the single settings authority before it can replace live Tier configuration.
# Inputs: Parsed settings JSON candidate.
# Outputs: True only for object-shaped tiers with unique tier/account/model Backend identities.
def _valid_tier_config(candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    if not isinstance(candidate.get("llm_tier", {}), dict):
        return False
    tiers = candidate.get("llm_tiers")
    if not isinstance(tiers, dict) or not tiers:
        return False
    identities: set[str] = set()
    for tier_name, models in tiers.items():
        if not str(tier_name or "").strip() or not isinstance(models, list):
            return False
        for model in models:
            if not isinstance(model, dict):
                return False
            backend = str(model.get("backend") or "").strip()
            account = str(model.get("account") or "").strip()
            model_name = str(model.get("model_name") or "").strip()
            if not backend or not account or not model_name:
                return False
            try:
                max_context_tokens = int(model.get("max_context_tokens") or 0)
                reserved_completion_tokens = int(model.get("reserved_completion_tokens") or 0)
            except (TypeError, ValueError):
                return False
            if reserved_completion_tokens < 0:
                return False
            if max_context_tokens > 0 and reserved_completion_tokens >= max_context_tokens:
                return False
            identity = f"{tier_name}:{account}:{model_name}"
            if identity in identities:
                return False
            identities.add(identity)
    return True


# 用途：
# - 加载并查询 llm_tier 配置，account 是凭证/额度/并发主体，backend 是路由入口
# 输入：
# - settings_path 或环境变量中的配置路径
# 输出：
# - Router、server 和执行阶段可消费的配置查询接口
class TierConfig:
    # 用途：
    # - 定位并加载 llm_tier settings.json
    # 输入：
    # - settings_path: 可选显式配置路径；为空时按环境变量和默认路径查找
    # 输出：
    # - 初始化后的 TierConfig 实例
    def __init__(self, settings_path: str | Path | None = None) -> None:
        self._settings_path: Path | None = None
        self._config: dict[str, Any] = {}
        self._last_persist_error = ""

        if settings_path:
            self._settings_path = Path(settings_path).resolve()
        else:
            env_path = os.environ.get("SLINKY_TIER_CONFIG", "").strip()
            if env_path:
                self._settings_path = Path(env_path).resolve()

            if not self._settings_path or not self._settings_path.is_file():
                cwd = Path.cwd()
                repo_root = Path(__file__).resolve().parent.parent.parent
                candidates = [
                    Path(os.environ.get("SLINKY_WORKSPACES_SETTINGS", "")).expanduser(),
                    cwd / "workspaces" / "settings.json",
                    cwd.parent / "workspaces" / "settings.json",
                    repo_root / "workspaces" / "settings.json",
                ]
                default_path = Path(__file__).resolve().parent.parent.parent / "settings.default.json"
                if default_path.is_file():
                    candidates.append(default_path)
                for candidate in candidates:
                    if str(candidate) and candidate.is_file():
                        self._settings_path = candidate
                        break

        if self._settings_path and self._settings_path.is_file():
            try:
                candidate = json.loads(self._settings_path.read_text(encoding="utf-8"))
                self._config = candidate if _valid_tier_config(candidate) else {}
            except (json.JSONDecodeError, OSError):
                self._config = {}

    # 用途：
    # - 读取指定 Tier 下的 backend 列表并解析成完整 TierModel
    # 输入：
    # - tier_name: llm_tiers 中的 Tier 名称
    # 输出：
    # - 按配置文件顺序返回的 TierModel 列表；配置位置即路由顺序
    def get_tier_models(self, tier_name: str) -> list[TierModel]:
        tiers = self._config.get("llm_tiers", {})
        raw_models = tiers.get(tier_name, [])
        models: list[TierModel] = []
        for m in raw_models:
            try:
                resolved_weight = int(round(float(m.get("weight", 1) or 1)))
            except (TypeError, ValueError):
                resolved_weight = 1
            backend_name = str(m.get("backend", "") or "").strip()
            identity_account, identity_model = _backend_identity_account_model(backend_name)
            account_id = str(m.get("account") or identity_account or "").strip()
            account = self.get_account(account_id) if account_id else None
            provider_name = str(m.get("provider", m.get("backend", "")) or "").strip()
            backend_type = str(m.get("backend_type", "API") or "API").strip()
            agent_name = backend_name.split(":", 1)[0].strip()
            is_mlexp_backend = agent_name == "mlexp" or backend_type.upper() == "MLP"
            credentials = {} if is_mlexp_backend else (dict(account.credentials) if account is not None else {})
            backend_credentials = dict(m.get("credentials", {}) or {}) if isinstance(m.get("credentials", {}), dict) else {}
            credentials.update(backend_credentials)
            if m.get("api_key"):
                credentials["api_key"] = m.get("api_key")
            if m.get("api_key_file"):
                credentials["api_key_file"] = m.get("api_key_file")
            if m.get("base_url"):
                credentials["base_url"] = m.get("base_url")
            for credential_key in (
                "access_key_id",
                "secret_access_key",
                "usage_access_key_id",
                "usage_secret_access_key",
                "usage_access_key_id_file",
                "usage_secret_access_key_file",
                "usage_cookie",
                "usage_cookie_file",
                "console_cookie_file",
                "usage_url",
                "usage_web_id",
                "usage_csrf_token",
                "x_web_id",
                "usage_group_id",
                "group_id",
                "usage_account_id",
                "account_id",
                "usage_workspace_url",
                "usage_workspace_id",
            ):
                if m.get(credential_key):
                    credentials[credential_key] = m.get(credential_key)
            if m.get("cli_path"):
                credentials["cli_path"] = m.get("cli_path")
            if m.get("sandbox"):
                credentials["sandbox"] = m.get("sandbox")
            if m.get("remote_workspace_root"):
                credentials["remote_workspace_root"] = m.get("remote_workspace_root")
            for config_key in ("workdir", "ssh"):
                if m.get(config_key):
                    credentials[config_key] = m.get(config_key)
            if m.get("timeout_seconds"):
                credentials["timeout_seconds"] = m.get("timeout_seconds")
            if m.get("max_tokens"):
                credentials["max_tokens"] = m.get("max_tokens")
            quota = dict(account.quota) if account is not None else {}
            usage_account_id = str(
                m.get("usage_account")
                or m.get("usage_account_id")
                or _usage_account_from_model_selector(m)
                or ""
            ).strip()
            usage_account = self.get_account(usage_account_id) if usage_account_id else None
            if usage_account is not None:
                usage_credentials = {
                    key: value
                    for key, value in usage_account.credentials.items()
                    if key.startswith("usage_") or key in {
                        "console_cookie_file",
                        "usage_cookie_file",
                        "usage_workspace_url",
                        "usage_url",
                        "usage_web_id",
                        "x_web_id",
                        "usage_group_id",
                        "group_id",
                    }
                }
                credentials.update(usage_credentials)
                credentials["usage_account_id"] = usage_account.account_id
                usage_quota = dict(usage_account.quota)
                usage_quota["usage_provider"] = usage_account.provider
                quota.update(usage_quota)
            backend_quota = dict(m.get("quota", {}) or {}) if isinstance(m.get("quota", {}), dict) else {}
            quota.update(backend_quota)
            if m.get("quota_type"):
                quota["quota_type"] = m.get("quota_type")
            if m.get("reset_day"):
                quota["reset_day"] = m.get("reset_day")
            for quota_key in ("quota_provider", "quota_scope", "usage_provider", "reset_strategy"):
                if m.get(quota_key):
                    quota[quota_key] = m.get(quota_key)
            models.append(
                TierModel(
                    backend=m.get("backend", ""),
                    provider=provider_name,
                    model_name=m.get("model_name") or identity_model,
                    account=account_id,
                    usage_account=usage_account_id or account_id,
                    model_key=m.get("model_key") or m.get("model_name") or identity_model,
                    backend_type=backend_type,
                    weight=max(1, resolved_weight),
                    priority=int(m.get("priority") or 0),
                    enabled=bool(m.get("enabled", True)),
                    timeout_seconds=int(m.get("timeout_seconds") or credentials.get("timeout_seconds") or 600),
                    max_context_tokens=int(m.get("max_context_tokens") or 0),
                    reserved_completion_tokens=int(m.get("reserved_completion_tokens") or 0),
                    max_output_tokens=int(m.get("max_output_tokens") or 0),
                    quota=quota,
                    credentials=credentials,
                )
            )
        return models

    # 用途：
    # - 读取指定 account 配置并解析成 TierAccount
    # 输入：
    # - account_id: llm_accounts 中的账号标识
    # 输出：
    # - TierAccount；不存在或配置非法时返回 None
    def get_account(self, account_id: str) -> TierAccount | None:
        normalized_account = str(account_id or "").strip()
        if not normalized_account:
            return None
        raw_accounts = self._config.get("llm_accounts", {})
        if not isinstance(raw_accounts, dict):
            return None
        raw = raw_accounts.get(normalized_account)
        if not isinstance(raw, dict):
            return None
        credentials = dict(raw.get("credentials", {}) or {}) if isinstance(raw.get("credentials", {}), dict) else {}
        for credential_key in (
            "api_key",
            "api_key_file",
            "base_url",
            "access_key_id",
            "secret_access_key",
            "usage_access_key_id",
            "usage_secret_access_key",
            "usage_access_key_id_file",
            "usage_secret_access_key_file",
            "usage_cookie",
            "usage_cookie_file",
            "console_cookie_file",
            "usage_url",
            "usage_web_id",
            "usage_csrf_token",
            "x_web_id",
            "usage_group_id",
            "group_id",
            "usage_account_id",
            "account_id",
            "usage_workspace_url",
            "usage_workspace_id",
        ):
            if raw.get(credential_key):
                credentials[credential_key] = raw.get(credential_key)
        quota = dict(raw.get("quota", {}) or {}) if isinstance(raw.get("quota", {}), dict) else {}
        if raw.get("quota_type"):
            quota["quota_type"] = raw.get("quota_type")
        if raw.get("reset_day"):
            quota["reset_day"] = raw.get("reset_day")
        for quota_key in ("quota_provider", "quota_scope", "usage_provider", "reset_strategy"):
            if raw.get(quota_key):
                quota[quota_key] = raw.get(quota_key)
        return TierAccount(
            account_id=normalized_account,
            provider=str(raw.get("provider") or "").strip(),
            max_concurrent_requests=max(1, int(raw.get("max_concurrent_requests") or 1)),
            min_request_interval_ms=max(0, int(raw.get("min_request_interval_ms") or 0)),
            requests_per_minute=max(0, int(raw.get("requests_per_minute") or 0)),
            quota=quota,
            credentials=credentials,
        )

    # 用途：
    # - 返回全部 account 配置，供 runtime dashboard 和 router 并发池使用
    # 输入：
    # - 无
    # 输出：
    # - 按 settings.json 顺序解析出的 TierAccount 列表
    def get_accounts(self) -> list[TierAccount]:
        raw_accounts = self._config.get("llm_accounts", {})
        if not isinstance(raw_accounts, dict):
            return []
        return [
            account
            for account_id in raw_accounts
            if (account := self.get_account(str(account_id))) is not None
        ]

    # 用途：
    # - 在 llm_tiers 内定位一个 backend 配置对象，backend 自身是唯一配置来源
    # 输入：
    # - backend/model_name/model_key/provider/account: backend 标识和可选模型/account 限定
    # 输出：
    # - TierModel；找不到时返回 None
    def find_backend_model(
        self,
        backend: str,
        model_name: str = "",
        model_key: str = "",
        provider: str = "",
        account: str = "",
    ) -> TierModel | None:
        backend_name = str(backend or "").strip()
        target_model_name = str(model_name or "").strip()
        target_model_key = str(model_key or "").strip()
        target_provider = str(provider or "").strip()
        target_account = str(account or "").strip()
        if not backend_name and not target_provider:
            return None
        fallback: TierModel | None = None
        tiers = self._config.get("llm_tiers", {})
        for tier_name in tiers:
            for model in self.get_tier_models(tier_name):
                if backend_name and model.backend != backend_name:
                    continue
                if target_provider and model.provider != target_provider:
                    continue
                if target_account and str(model.account or "").strip() != target_account:
                    continue
                if target_model_key and model.model_key == target_model_key:
                    return model
                if target_model_name and model.model_name == target_model_name:
                    return model
                if fallback is None:
                    fallback = model
        return fallback

    # 用途：
    # - 查询 role 应路由到哪个 Tier
    # 输入：
    # - role_name: runtime role 名称
    # 输出：
    # - Tier 名称；未配置时返回空字符串
    def get_tier_for_role(self, role_name: str) -> str:
        role_map = self._config.get("role_tier_map", {})
        return str(role_map.get(role_name, ""))

    # 用途：
    # - 读取 provider profile 中声明的可选模型能力列表
    # 输入：
    # - provider: backend provider 名称，例如 xfyun
    # 输出：
    # - model_name/model_key/max_context_tokens 等模型 profile 列表
    def get_provider_profile_models(self, provider: str) -> list[dict[str, Any]]:
        provider_name = str(provider or "").strip()
        profiles = self._config.get("provider_profiles", {})
        profile = profiles.get(provider_name, {}) if isinstance(profiles, dict) else {}
        raw_models = profile.get("models", []) if isinstance(profile, dict) else []
        if not isinstance(raw_models, list):
            return []
        models: list[dict[str, Any]] = []
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            model_name = str(raw_model.get("model_name") or raw_model.get("name") or "").strip()
            model_key = str(raw_model.get("model_key") or raw_model.get("modelId") or raw_model.get("model_id") or "").strip()
            if not model_name or not model_key:
                continue
            try:
                max_context_tokens = int(raw_model.get("max_context_tokens") or 0)
            except (TypeError, ValueError):
                max_context_tokens = 0
            models.append({
                "model_name": model_name,
                "model_key": model_key,
                "max_context_tokens": max_context_tokens,
            })
        return models

    # 用途：
    # - 返回 backend unhealthy breaker 的阈值和冷却时长配置
    # 输入：
    # - 无；读取 llm_tier.breaker 或顶层缺省值
    # 输出：
    # - `failure_threshold` 与 `cooldown_seconds`
    def get_breaker_config(self) -> dict[str, int]:
        tier_cfg = self._config.get("llm_tier", {})
        breaker = tier_cfg.get("breaker", {}) if isinstance(tier_cfg.get("breaker", {}), dict) else {}
        failure_threshold = int(breaker.get("failure_threshold") or 3)
        cooldown_seconds = int(breaker.get("cooldown_seconds") or 300)
        return {
            "failure_threshold": max(1, failure_threshold),
            "cooldown_seconds": max(1, cooldown_seconds),
        }

    # 用途：
    # - 从 account 配置读取账号级并发和调用间隔参数
    # 输入：
    # - account_id: llm_accounts 中的账号标识
    # 输出：
    # - max_concurrent_requests、min_request_interval_ms、requests_per_minute 配置
    def get_account_concurrency(self, account_id: str) -> dict[str, Any]:
        account = self.get_account(account_id)
        if account is None:
            return {"max_concurrent_requests": 1, "min_request_interval_ms": 0, "requests_per_minute": 0}
        return {
            "max_concurrent_requests": account.max_concurrent_requests,
            "min_request_interval_ms": account.min_request_interval_ms,
            "requests_per_minute": account.requests_per_minute,
        }

    # 用途：
    # - 从 backend 自身配置读取 context/output 能力参数
    # 输入：
    # - backend/account: settings.json 中的 backend 标识和账号限定
    # - model_name/model_key: 可选模型展示名和真实 API model id
    # 输出：
    # - capability 配置副本；未配置时返回空字典
    def get_backend_capabilities(
        self,
        backend: str,
        model_name: str = "",
        model_key: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        model = self.find_backend_model(
            backend,
            model_name=model_name,
            model_key=model_key,
            account=account,
        )
        if model is None:
            return {}
        return {
            "max_context_tokens": model.max_context_tokens,
            "reserved_completion_tokens": model.reserved_completion_tokens,
            "max_output_tokens": model.max_output_tokens,
        }

    # 用途：
    # - 从 backend 自身配置读取 quota reset 策略
    # 输入：
    # - backend: backend 标识
    # 输出：
    # - quota 配置副本；未配置时返回 None
    def get_quota_config(self, backend: str) -> dict[str, Any] | None:
        model = self.find_backend_model(backend)
        return dict(model.quota) if model and model.quota else None

    # 用途：
    # - 读取 backend 自身携带的 credentials 配置
    # 输入：
    # - backend/provider/model_name/model_key/account: backend 标识和可选模型/account 限定
    # 输出：
    # - 可传给 backend client 的 credentials 副本
    def get_backend_credentials(
        self,
        backend: str,
        provider: str = "",
        model_name: str = "",
        model_key: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        model = self.find_backend_model(
            backend,
            model_name=model_name,
            model_key=model_key,
            provider=provider,
            account=account,
        )
        return dict(model.credentials) if model else {}

    # 用途：
    # - 将当前 config 内存态持久化回 settings.json
    # 输入：
    # - 无；读取当前 `_config`
    # 输出：
    # - True 表示写回成功
    def persist(self) -> bool:
        if not self._settings_path:
            self._last_persist_error = "settings_path_missing"
            return False
        temporary_path: Path | None = None
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._config, ensure_ascii=False, indent=2) + "\n"
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._settings_path.parent,
                prefix=f".{self._settings_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self._settings_path)
            temporary_path = None
            self._last_persist_error = ""
            return True
        except Exception as exc:
            self._last_persist_error = str(exc)
            return False
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    # 用途：
    # - 从原 settings path 重新加载配置
    # 输入：
    # - 无；读取初始化时确定的 settings 路径
    # 输出：
    # - True 表示 reload 成功
    def reload(self) -> bool:
        if not self._settings_path or not self._settings_path.is_file():
            return False
        try:
            candidate = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        if not _valid_tier_config(candidate):
            return False
        self._config = candidate
        return True

    # 用途：
    # - 判断 llm_tier 是否启用
    # 输入：
    # - 无；读取 llm_tier.enabled
    # 输出：
    # - True 表示启用
    def is_enabled(self) -> bool:
        tier_cfg = self._config.get("llm_tier", {})
        return bool(tier_cfg.get("enabled", False))


# 用途：
# - 从 MLP backend 的模型选择器推导 usage account
# 输入：
# - raw_model: llm_tiers 中的单个 backend 配置对象
# 输出：
# - 例如 `go/DeepSeek-V4-Flash` -> `go`，`ollama/gemma4` -> `ollama`
def _usage_account_from_model_selector(raw_model: dict[str, Any]) -> str:
    backend = str(raw_model.get("backend") or "").strip().lower()
    identity_account, _identity_model = _backend_identity_account_model(backend)
    if identity_account:
        return identity_account
    backend_type = str(raw_model.get("backend_type") or "").strip().upper()
    if backend != "mlexp" and backend_type != "MLP":
        return ""
    selector = str(raw_model.get("model_key") or raw_model.get("model_name") or "").strip()
    if "/" not in selector:
        return ""
    account, _model = selector.split("/", 1)
    return account.strip()


# 用途：
# - 从 backend identity 解析 account 和 model
# 输入：
# - backend: `agent:account/model` 或 API `account/model`
# 输出：
# - `(account, model)`；不是 identity 时返回空字符串
def _backend_identity_account_model(backend: str) -> tuple[str, str]:
    normalized = str(backend or "").strip()
    if ":" in normalized:
        _agent, normalized = normalized.split(":", 1)
    if "/" not in normalized:
        return "", ""
    account, model = normalized.split("/", 1)
    return account.strip(), model.strip()
