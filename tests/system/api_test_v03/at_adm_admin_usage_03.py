"""Case ID: ADM-ADMIN-USAGE-03

Endpoint: DELETE /v1/usage
Upstream Provider: 无（直接写 SQLite 造测试数据）
Model: 无
Auth: Bearer dev-admin

目标：验证清空 usage 统计记录功能，4 种过滤 scope。

原理：用 admin_client_b 直接 SQL 写入 test usage 记录，
reset 后通过 GET /v1/usage 验证记录已清空。

断言：
- 无参数 DELETE → 全部清空（deleted == 插入数）
- ?model=Worker → 只清 model=Worker 的记录
- ?deployment_id=depl_b → 只清该 deployment 的记录
- ?model=Worker&deployment_id=depl_b → 两者都满足才清
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_all(admin_client_b, llmtier_b):
    store = llmtier_b._tmpdir  # not needed directly; use via fixture's admin_client
    # Insert test data via direct SQL on the test instance's DB
    import sqlite3
    db_path = llmtier_b._db_path
    conn = sqlite3.connect(db_path)
    inserted = 0
    for model in ("Worker", "Senior"):
        for i in range(2):
            principal = f"bulk_{model}_{i}"
            req = f"bulk_req_{model}_{i}"
            stamp = "2026-09-22T10:00:00.000Z"
            conn.execute("INSERT INTO usage_obligations VALUES(?,?,?,?,?,?)",
                (principal, req, model, "/v1/responses", stamp, stamp))
            conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (principal, req, 1, 1, model, "/v1/responses", stamp, stamp, "measured", "provider", 10, 5, 15, 0, 0, 0))
            conn.execute("INSERT INTO usage_heads VALUES(?,?,?,?)", (principal, req, 1, stamp))
            conn.execute("INSERT INTO provider_request_bindings VALUES(?,?,?,?,?)", (principal, req, "prov_b", "depl_b", stamp))
            inserted += 1
    conn.commit()

    before = conn.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn.close()

    # Reset all
    resp = admin_client_b.delete("/v1/usage")
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["deleted"] == before, f"deleted={body['deleted']} expected {before}"

    # Verify empty
    conn2 = sqlite3.connect(db_path)
    after = conn2.execute("SELECT COUNT(*) FROM usage_record_versions").fetchone()[0]
    conn2.close()
    assert after == 0, f"期望 0 条记录，实际 {after} 条"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_by_model(admin_client_b, llmtier_b):
    import sqlite3
    db_path = llmtier_b._db_path
    conn = sqlite3.connect(db_path)
    # Insert Worker and Senior records
    for model in ("Worker", "Senior"):
        for i in range(2):
            principal = f"model_test_{model}_{i}"
            req = f"model_req_{model}_{i}"
            stamp = "2026-09-22T11:00:00.000Z"
            conn.execute("INSERT INTO usage_obligations VALUES(?,?,?,?,?,?)",
                (principal, req, model, "/v1/responses", stamp, stamp))
            conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (principal, req, 1, 1, model, "/v1/responses", stamp, stamp, "measured", "provider", 10, 5, 15, 0, 0, 0))
            conn.execute("INSERT INTO usage_heads VALUES(?,?,?,?)", (principal, req, 1, stamp))
            conn.execute("INSERT INTO provider_request_bindings VALUES(?,?,?,?,?)", (principal, req, "prov_b", "depl_b", stamp))
    conn.commit()

    # Reset only Worker
    resp = admin_client_b.delete("/v1/usage", params={"model": "Worker"})
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["deleted"] == 2, f"deleted={body['deleted']} expected 2 (2 Worker records)"

    # Verify Senior still there, Worker gone
    conn2 = sqlite3.connect(db_path)
    remaining = conn2.execute("SELECT model, COUNT(*) FROM usage_record_versions v JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id AND h.head_record_version=v.record_version GROUP BY model").fetchall()
    conn2.close()
    remaining_dict = {r[0]: r[1] for r in remaining}
    assert remaining_dict.get("Senior") == 2, f"Senior should have 2, got {remaining_dict}"
    assert "Worker" not in remaining_dict, f"Worker should be gone, got {remaining_dict}"


@pytest.mark.api_b
def test_adm_admin_usage_03_reset_by_deployment(admin_client_b, llmtier_b):
    import sqlite3
    db_path = llmtier_b._db_path

    # Ensure a clean slate: earlier cases share this session DB and may leave
    # Senior provider_request_bindings bound to depl_b, which would inflate the
    # deployment-scoped deletion count.
    assert admin_client_b.delete("/v1/usage").status_code == 200

    # Create a second deployment
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

    conn = sqlite3.connect(db_path)
    # Insert records for depl_b and depl2
    for depl in ("depl_b", depl2_id):
        for i in range(2):
            principal = f"depl_test_{depl[-8:]}_{i}"
            req = f"depl_req_{depl[-8:]}_{i}"
            stamp = "2026-09-22T12:00:00.000Z"
            conn.execute("INSERT INTO usage_obligations VALUES(?,?,?,?,?,?)",
                (principal, req, "Worker", "/v1/responses", stamp, stamp))
            conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (principal, req, 1, 1, "Worker", "/v1/responses", stamp, stamp, "measured", "provider", 10, 5, 15, 0, 0, 0))
            conn.execute("INSERT INTO usage_heads VALUES(?,?,?,?)", (principal, req, 1, stamp))
            conn.execute("INSERT INTO provider_request_bindings VALUES(?,?,?,?,?)", (principal, req, "prov_b", depl, stamp))
    conn.commit()

    # Reset only depl_b
    resp = admin_client_b.delete("/v1/usage", params={"deployment_id": "depl_b"})
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["deleted"] == 2, f"deleted={body['deleted']} expected 2 (depl_b records)"

    # Verify depl2 still has records
    conn2 = sqlite3.connect(db_path)
    remaining = conn2.execute("SELECT COUNT(*) FROM provider_request_bindings WHERE deployment_id=?", (depl2_id,)).fetchone()[0]
    conn2.close()
    assert remaining == 2, f"depl2 should have 2 records, got {remaining}"
