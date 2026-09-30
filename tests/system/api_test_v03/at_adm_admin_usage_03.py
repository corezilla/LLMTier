"""Case ID: ADM-ADMIN-USAGE-03

Endpoint: DELETE /v1/usage
Upstream Provider: 无（直接写 SQLite 造测试数据）
Model: 无
Auth: Bearer dev-admin

目标：验证清空 usage 统计记录功能，4 种过滤 scope + 审计 + data→403 负向。

原理：用 admin_client_b 直接 SQL 写入 test usage 记录，
reset 后通过直连 SQL / GET /v1/usage 验证记录已清空。

断言：
- 无参数 DELETE → 全部清空（deleted == 插入数）
- ?model=Worker → 只清 model=Worker 的记录
- ?deployment_id=depl_b → 只清该 deployment 的记录
- ?model=Worker&deployment_id=depl_b → 两者都满足才清
- 审计：DELETE 后 GET /v1/audit 出现 action=="usage.reset"、result=="success" 行
- 角色负向：api_client_b DELETE /v1/usage → 403 permission_denied 且零副作用
- 半开窗 [from,to)：recorded_at == to 的记录不计入，== from 的记录计入
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from tests.system.api_test_v03.conftest import error_envelope


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _seed(conn, principal: str, req: str, model: str, *, deployment_id: str = "depl_b",
          recorded_at: str | None = None) -> None:
    """Insert one obligation + head record + binding (head version 1)."""
    stamp = recorded_at or _stamp()
    conn.execute("INSERT INTO usage_obligations VALUES(?,?,?,?,?,?)",
                 (principal, req, model, "/v1/responses", stamp, stamp))
    conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (principal, req, 1, 1, model, "/v1/responses", stamp, stamp, "measured",
                  "provider", 10, 5, 15, 0, 0, 0))
    conn.execute("INSERT INTO usage_heads VALUES(?,?,?,?)", (principal, req, 1, stamp))
    conn.execute(
        "INSERT INTO provider_request_bindings(principal_id,request_id,provider_id,deployment_id,bound_at) "
        "VALUES(?,?,?,?,?)", (principal, req, "prov_b", deployment_id, stamp))


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_all(admin_client_b, llmtier_b):
    db_path = llmtier_b._db_path
    conn = sqlite3.connect(db_path)
    inserted = 0
    for model in ("Worker", "Senior"):
        for i in range(2):
            _seed(conn, f"bulk_{model}_{i}", f"bulk_req_{model}_{i}", model)
            inserted += 1
    conn.commit()
    before = conn.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn.close()
    assert before >= inserted, f"种子未落库: before={before} inserted={inserted}"

    resp = admin_client_b.delete("/v1/usage")
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == {"deleted"}, f"reset body 键集不符: {set(body)}"
    assert isinstance(body["deleted"], int), f"deleted 非 int: {body['deleted']!r}"
    assert body["deleted"] == before, f"deleted={body['deleted']} expected {before}"

    conn2 = sqlite3.connect(db_path)
    after = conn2.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn2.close()
    assert after == 0, f"期望 0 条记录，实际 {after} 条"

    # 审计：mutate(atomic=True) 同事务写 usage.reset success。
    audit = admin_client_b.get("/v1/audit?limit=20")
    assert audit.status_code == 200, f"GET /v1/audit 失败: {audit.text}"
    rows = audit.json().get("data", [])
    hits = [e for e in rows if e.get("action") == "usage.reset" and e.get("result") == "success"]
    assert hits, f"未找到 usage.reset/success 审计行: {[e.get('action') for e in rows]}"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_by_model(admin_client_b, llmtier_b):
    db_path = llmtier_b._db_path
    conn = sqlite3.connect(db_path)
    for model in ("Worker", "Senior"):
        for i in range(2):
            _seed(conn, f"model_test_{model}_{i}", f"model_req_{model}_{i}", model)
    conn.commit()

    resp = admin_client_b.delete("/v1/usage", params={"model": "Worker"})
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["deleted"] == 2, f"deleted={body['deleted']} expected 2 (2 Worker records)"

    conn2 = sqlite3.connect(db_path)
    remaining = conn2.execute(
        "SELECT model, COUNT(*) FROM usage_record_versions v "
        "JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id "
        "AND h.head_record_version=v.record_version GROUP BY model").fetchall()
    conn2.close()
    remaining_dict = {r[0]: r[1] for r in remaining}
    assert remaining_dict.get("Senior") == 2, f"Senior should have 2, got {remaining_dict}"
    assert "Worker" not in remaining_dict, f"Worker should be gone, got {remaining_dict}"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_by_deployment(admin_client_b, llmtier_b):
    db_path = llmtier_b._db_path

    # Ensure a clean slate: earlier cases share this session DB.
    assert admin_client_b.delete("/v1/usage").status_code == 200

    depl_resp = admin_client_b.post("/v1/deployments", json={
        "name": "Reset Test Depl 2",
        "provider_id": "prov_b",
        "backend_model": "test-model-2",
        "capabilities": {
            "responses": True, "embeddings": False, "tools": False, "structured_outputs": False,
            "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 4096,
            "max_output_tokens": 2048, "embedding_space_id": None, "embedding_dimensions": None,
            "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None,
        },
        "enabled": True,
    })
    assert depl_resp.status_code == 201
    depl2_id = depl_resp.json()["id"]

    try:
        conn = sqlite3.connect(db_path)
        for depl in ("depl_b", depl2_id):
            for i in range(2):
                _seed(conn, f"depl_test_{depl[-8:]}_{i}", f"depl_req_{depl[-8:]}_{i}", "Worker",
                      deployment_id=depl)
        conn.commit()

        resp = admin_client_b.delete("/v1/usage", params={"deployment_id": "depl_b"})
        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["deleted"] == 2, f"deleted={body['deleted']} expected 2 (depl_b records)"

        conn2 = sqlite3.connect(db_path)
        remaining = conn2.execute(
            "SELECT COUNT(*) FROM provider_request_bindings WHERE deployment_id=?",
            (depl2_id,)).fetchone()[0]
        conn2.close()
        assert remaining == 2, f"depl2 should have 2 records, got {remaining}"
    finally:
        # teardown: 先清除本 case 为 depl2 造的 usage 绑定（provider_request_bindings
        # 对 deployments(id) 有 FK），再删除本 case 新建的 deployment。
        admin_client_b.delete("/v1/usage", params={"deployment_id": depl2_id})
        current = admin_client_b.get(f"/v1/deployments/{depl2_id}")
        if current.status_code == 200:
            del_resp = admin_client_b.delete(
                f"/v1/deployments/{depl2_id}",
                headers={"If-Match": current.headers["ETag"]},
            )
            assert del_resp.status_code == 204, f"teardown 删除失败: {del_resp.status_code}: {del_resp.text}"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_double_scope(admin_client_b, llmtier_b):
    """?model=Worker&deployment_id=depl_b → 两者都满足才清。"""
    db_path = llmtier_b._db_path
    assert admin_client_b.delete("/v1/usage").status_code == 200

    conn = sqlite3.connect(db_path)
    # 2 条 Worker@depl_b（应删）；1 条 Senior@depl_b（model 不符，留）；1 条 Worker@depl_other（depl 不符，留）
    for i in range(2):
        _seed(conn, f"ds_a_{i}", f"ds_req_a_{i}", "Worker", deployment_id="depl_b")
    _seed(conn, "ds_b_0", "ds_req_b_0", "Senior", deployment_id="depl_b")
    _seed(conn, "ds_c_0", "ds_req_c_0", "Worker", deployment_id="depl_other")
    conn.commit()
    conn.close()

    resp = admin_client_b.delete(
        "/v1/usage", params={"model": "Worker", "deployment_id": "depl_b"})
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["deleted"] == 2, f"deleted={body['deleted']} expected 2 (Worker@depl_b only)"

    conn2 = sqlite3.connect(db_path)
    left = dict(conn2.execute(
        "SELECT request_id, model FROM usage_record_versions WHERE request_id IN "
        "('ds_req_a_0','ds_req_a_1','ds_req_b_0','ds_req_c_0')").fetchall())
    conn2.close()
    assert "ds_req_a_0" not in left and "ds_req_a_1" not in left, f"Worker@depl_b 未删除: {left}"
    assert left.get("ds_req_b_0") == "Senior", f"Senior@depl_b 被误删: {left}"
    assert left.get("ds_req_c_0") == "Worker", f"Worker@depl_other 被误删: {left}"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_role_negative(admin_client_b, api_client_b, llmtier_b):
    """data 凭据 DELETE /v1/usage → 403 permission_denied 且零副作用。"""
    db_path = llmtier_b._db_path
    assert admin_client_b.delete("/v1/usage").status_code == 200

    conn = sqlite3.connect(db_path)
    _seed(conn, "role_neg", "role_neg_req", "Worker")
    conn.commit()
    before = conn.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn.close()
    assert before == 1

    resp = api_client_b.delete("/v1/usage")
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    assert set(resp.json()) == {"error"}, f"顶层键集不符: {set(resp.json())}"
    err = error_envelope(resp)
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    conn2 = sqlite3.connect(db_path)
    after = conn2.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn2.close()
    assert after == before, f"被拒的 data 请求产生了副作用: {before} -> {after}"
    assert after == 1, f"记录被误删（应保留 1 条）: {after}"


@pytest.mark.api_b
def test_adm_admin_usage_03_half_open_window(admin_client_b, llmtier_b):
    """半开窗 [from,to)：recorded_at == to 排除，== from 计入（判别性边界）。"""
    assert admin_client_b.delete("/v1/usage").status_code == 200

    frm = "2026-01-01T00:00:00.000Z"
    mid = "2026-01-01T00:00:01.000Z"
    to = "2026-01-01T00:00:02.000Z"

    db_path = llmtier_b._db_path
    conn = sqlite3.connect(db_path)
    _seed(conn, "bnd_in", "bnd_req_at_from", "Worker", recorded_at=frm)   # == from → 计入
    _seed(conn, "bnd_mid", "bnd_req_inside", "Worker", recorded_at=mid)   # 窗内 → 计入
    _seed(conn, "bnd_out", "bnd_req_at_to", "Worker", recorded_at=to)     # == to → 排除
    conn.commit()
    conn.close()

    def _ids(req_ids: set[str]) -> set[str]:
        resp = admin_client_b.get("/v1/usage", params={"from": frm, "to": to})
        assert resp.status_code == 200, f"GET /v1/usage 失败: {resp.text}"
        got = {r["request_id"] for r in resp.json().get("data", [])}
        return got & req_ids

    ids = {"bnd_req_at_from", "bnd_req_inside", "bnd_req_at_to"}
    present = _ids(ids)
    assert "bnd_req_at_from" in present, f"recorded_at == from 应计入（半开左闭）: {present}"
    assert "bnd_req_inside" in present, f"窗内记录应计入: {present}"
    assert "bnd_req_at_to" not in present, (
        f"recorded_at == to 不应计入（半开右开 [from,to)）: {present}")
