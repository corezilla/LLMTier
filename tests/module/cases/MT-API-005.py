"""MT-API-005 — `_run` 三错误出口（M001，层②，negative，P0）。

出口：ApiError→既定码；sqlite3.Error→503 `usage_store_unavailable`（落日志）；
未知异常→500 `internal_error`（落日志）。故障注入＝存储面（文件权限）与
数据面（超深 JSON 触发 RecursionError），均经公开入口/真实文件触发，不打桩。
"""
from __future__ import annotations

import json
import os
import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class RunExitTests(LoopbackEnv):
    def _log_events(self, event):
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        return [row for row in page["data"] if row["event"] == event]

    def test_api_error_exit_maps_declared_code(self):
        status, payload, _ = self.request("GET", "/v1/usage?from=bad-timestamp&to=2100-01-01T00:00:00Z")
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_store_failure_exit_is_503_usage_store_unavailable(self):
        # 存储面注入（文件权限）。`_run` 的 sqlite3.Error 出口 message 为
        # "Store is unavailable"（区别于服务层包装的 "Usage store is unavailable"）；
        # 库整体不可用时日志写入本身被 OperationalLog fail-open 吞掉（同样正确）。
        db_path = self.fx.app.store.path
        self.fx.app.store.close()
        os.chmod(db_path, 0o000)
        try:
            status, payload, _ = self.request("GET", "/v1/providers")
            self.assertEqual(503, status)
            self.assertEqual("usage_store_unavailable", payload["error"]["code"])
            self.assertEqual("Store is unavailable", payload["error"]["message"])
        finally:
            os.chmod(db_path, 0o644)
        # 存储恢复后日志路径恢复可用
        status, _, _ = self.request("GET", "/healthz")
        self.assertEqual(200, status)
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertTrue(any(row["event"] == "request" for row in page["data"]))

    def test_unknown_exception_exit_is_500_internal_error_and_logged(self):
        # 存储面注入：毒化 service_levels.capabilities_json（非 JSON 字符串）→
        # /v1/models 组装路径 json.loads 抛 JSONDecodeError（非 ApiError /
        # 非 sqlite3.Error）→ _run 未知异常出口 500。
        conn = self.fx.app.store.connection()
        original = conn.execute("SELECT capabilities_json FROM service_levels WHERE id='Worker'").fetchone()[0]
        try:
            conn.execute("UPDATE service_levels SET capabilities_json='{oops' WHERE id='Worker'")
            status, payload, _ = self.request("GET", "/v1/models")
            self.assertEqual(500, status)
            self.assertEqual("internal_error", payload["error"]["code"])
            self.assertEqual("server_error", payload["error"]["type"])
        finally:
            conn.execute("UPDATE service_levels SET capabilities_json=? WHERE id='Worker'", (original,))
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertTrue(any(row["event"] == "unhandled_error" for row in page["data"]))

    def test_server_survives_after_error_exits(self):
        status, payload, _ = self.request("GET", "/healthz")
        self.assertEqual(200, status)


if __name__ == "__main__":
    unittest.main()
