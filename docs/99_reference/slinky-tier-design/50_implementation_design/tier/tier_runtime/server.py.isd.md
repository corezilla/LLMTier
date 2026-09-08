# `src/llm_tier/server.py` ISD

Version: v1.7
Last Updated: 2026-09-08 12:18:44
Status: Draft / HTTP Authority Retained

target_file: `src/llm_tier/server.py`
target_state: `retain`

上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 职责

`TierServer`是独立Tier进程的唯一业务authority和HTTP owner，持有Config、Router、Quota、Concurrency、Provider Usage、Jobs、Stats、probe与management状态。它只允许监听loopback，不提供Browser页面；Dashboard通过`TierClient`代理其API。调用方进程不得构造Router、Backend或Stats writer。

## 2. Public Interface

```python
class TierServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, settings_path: str | None = None) -> None: ...
    def start(self, blocking: bool = False) -> None: ...
    def stop(self) -> None: ...
    def call(self, req: TierCallRequest) -> TierCallResult: ...
    def get_stats(self, query: TierStatsQuery | None = None) -> list[dict[str, Any]]: ...
    def get_summary(self) -> dict[str, Any]: ...
    def reset_exhausted(self, tier_name: str = "") -> None: ...
    def reload_config(self) -> bool: ...
```

`host`只接受`127.0.0.1`、`localhost`或`::1`；`port`必须为1..65535，测试可传0取得临时端口。生产配置不得监听`0.0.0.0`或LAN地址。`settings_path`沿用`TierConfig`现有路径语义，不建立第二份server配置。

HTTP API保留现有`/health`、`/runtime`、`/stats`、`/recent-errors`、`/call`、`/escalate`、`/result/<job_id>`、`/reset`、`/reload`、`/backend/probe`及config/model/weight/concurrency/enable/disable/usage/debug management routes。Tier页面从本Server删除，`/`、`/tier`和`/tier.html`返回404；Browser页面只由Dashboard提供。

JSON body只接受object并限制body size。`POST /config/save`只接受空object；非空object在持久化前返回HTTP 400，并包含`error/message/request_id`。`POST /backend/weight`的validation 400也必须包含非空`request_id`，且不得回显输入credential或非法字段值。参数错误在创建job或修改状态前返回4xx；Backend/business失败保持typed payload。HTTP response不得包含credential、Cookie、token或traceback。

## 3. Job、Timeout与并发

submit返回唯一`job_id`，`get_result`只按`job_id`查询。Client生成的`client_request_id`只用于日志/stats correlation，不作为job查询alias，也不触发自动去重。POST响应未知时Client不得自动重提；同步call提交成功后只轮询同一`job_id`。

Client总等待预算到期必须返回明确poll timeout，不能只记录warning后无限等待。GET transport失败与pending必须区分。busy retry仅处理Server明确返回的`all_backends_busy`，受总timeout约束。

call/probe/reload/enable/disable并发沿用Router、Concurrency和Server lock的唯一状态；不得新增Dashboard侧coordination。shutdown停止接收新请求，取消probe timer并关闭listener；已进入Backend的非幂等调用不得由HTTP断连自动重提。

Backend首次进入exhausted时，以`exhausted_ts`为基准注册600秒周期probe；Server重启或monitor补扫时计算严格晚于当前时间的下一个600秒边界，避免立即probe风暴。到期后只在Backend仍admin-enabled且exhausted时调用现有`_probe_single_backend`。失败结果通过现有status路径重新注册下一周期；成功结果通过现有quota reset路径清除exhausted并取消timer。`reset_at`只进入runtime/usage展示，不参与timer due计算。

`/runtime`的Backend主状态与`failure_count/last_error/last_error_type/last_error_at`必须直接来自Router当前authority；最近probe记录只提供`checked_at`和Provider Usage等补充信息，不得用旧probe状态覆盖调用失败后的`unreachable`。

## 4. Tests

真实process测试覆盖loopback bind、拒绝非loopback host、Dashboard代理、Browser无8765请求、body boundary、malformed JSON、disconnect、timeout、busy、concurrent call/probe/reload、job poll、shutdown及credential redaction。exhausted timer测试必须覆盖首次delay为600秒、远期`reset_at`不延后probe、失败后继续下一周期、成功后取消以及Server重启补扫不产生立即probe风暴。源码测试确认不存在Tier HTML serving和`_TierEmbedded` fallback。

## Exact Signature Authority

- `class TierServer`
- `TierServer.__init__(self, host: str=DEFAULT_HOST, port: int=DEFAULT_PORT, settings_path: str | None=None) -> None`
- `TierServer.start(self, blocking: bool=False) -> None`
- `TierServer.stop(self) -> None`
- `TierServer.call(self, req: TierCallRequest) -> TierCallResult`
- `TierServer.get_stats(self, query: TierStatsQuery | None=None) -> list[dict[str, Any]]`
- `TierServer.get_summary(self) -> dict[str, Any]`
- `TierServer.reset_exhausted(self, tier_name: str='') -> None`
- `TierServer.reload_config(self) -> bool`
