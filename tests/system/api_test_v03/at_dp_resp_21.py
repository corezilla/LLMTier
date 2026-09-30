"""Case ID: DP-RESP-21

Endpoint: POST /v1/responses（流式）；GET /v1/trace/{request_id}
Upstream Provider: prov_b（LAN fake provider，backend_model="force-huge-stream"）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_diag），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）；force-huge-stream 输出远超 socket 缓冲的帧，
        使客户端断开后服务端写入必然失败，从而**确定性**触发 aborted 记录（非竞态）
  Auth: Bearer dev-data

目标：客户端 SSE 发送阶段断开 → 出口记 trace `aborted`（reason "client disconnected"），
无成功终态，许可释放。

实现：src/http_api/app.py:222-223
  except (BrokenPipeError, ConnectionResetError):
      diagnostics.record_trace(request_id, "aborted", {"reason": "client disconnected"})

断言（无 xfail 兜底——断开可确定性构造）：
- 首响 200 + text/event-stream
- 断开后 trace 含 aborted 阶段且 reason == "client disconnected"（硬断言）
- 后续请求可正常准入（许可释放）
"""
from __future__ import annotations

import time

import pytest

API_BODY = {
    "model": "Senior",
    "input": [{"role": "user", "content": "Count from 1 to 1000."}],
    "stream": True,
    "store": False,
    "max_output_tokens": 2000,
}


def _set_backend_model(admin, backend_model: str) -> None:
    view = admin.get("/v1/deployments/depl_b")
    assert view.status_code == 200, f"GET deployment 失败: {view.text}"
    etag = view.headers.get("ETag")
    assert etag, "GET deployment 缺少 ETag"
    resp = admin.patch(
        "/v1/deployments/depl_b",
        json={"backend_model": backend_model},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 200, f"PATCH backend_model 失败: {resp.status_code}: {resp.text}"


@pytest.mark.api_b
def test_dp_resp_21_client_disconnect_marks_aborted(llmtier_b_diag):
    admin = llmtier_b_diag.admin_client()
    _set_backend_model(admin, "force-huge-stream")
    request_id = None
    try:
        client = llmtier_b_diag.api_client()
        try:
            with client.stream("POST", "/v1/responses", json=API_BODY) as resp:
                assert resp.status_code == 200, f"首响应为 {resp.status_code}: {resp.text[:200]}"
                assert "text/event-stream" in resp.headers.get("content-type", ""), (
                    f"content-type={resp.headers.get('content-type')!r}"
                )
                request_id = resp.headers.get("X-Request-ID")
                assert request_id, "响应缺少 X-Request-ID"
                # 读一个事件即关闭：服务端随后写入巨量帧必然失败 → aborted。
                for _ in resp.iter_lines():
                    break
        finally:
            client.close()

        assert request_id, "未记录 request_id"

        # 硬断言：轮询 trace 直到出现 aborted；超时即 FAIL（不再 xfail 掩盖）。
        aborted = None
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            trace = admin.get(f"/v1/trace/{request_id}")
            if trace.status_code == 200:
                stages = trace.json().get("stages") or []
                aborted = next((s for s in stages if s.get("stage") == "aborted"), None)
                if aborted is not None:
                    break
            time.sleep(0.2)

        assert aborted is not None, (
            f"服务端未记录 aborted（client disconnect 未被观测）: {trace.json()}"
        )
        detail = aborted.get("detail") or {}
        assert detail.get("reason") == "client disconnected", (
            f"aborted reason 不符: {detail}"
        )

        # 许可释放：断开后新请求可正常准入并完成。
        probe = llmtier_b_diag.api_client()
        try:
            with probe.stream("POST", "/v1/responses", json={**API_BODY, "input": "hi"}) as follow:
                assert follow.status_code == 200, (
                    f"断开后许可未释放，后续请求 {follow.status_code}: {follow.text[:200]}"
                )
                saw_terminal = False
                for line in follow.iter_lines():
                    text = line.decode("utf-8", "replace") if isinstance(line, bytes) else line
                    if text.startswith("event: response.completed"):
                        saw_terminal = True
                assert saw_terminal, "后续请求未完成（缺 response.completed）"
        finally:
            probe.close()
    finally:
        _set_backend_model(admin, "test-model")
        admin.close()
