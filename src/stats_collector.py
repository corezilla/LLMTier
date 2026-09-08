from __future__ import annotations

import calendar
import json
import math
import time
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Any

from tier_model import TierStatsQuery, TierStatsRow
from utils.sqlite import load_sqlite_module, sqlite_operation_lock


LLM_STATS_SQLITE_BUSY_TIMEOUT_MS = 5000
sqlite3 = load_sqlite_module()


# 用途：
# - 为 SQLite stats 行生成统计聚合 key
# 输入：
# - row/group_by: SQLite 行和分组层级
# 输出：
# - 稳定 tuple key
def _stats_group_key(*, row: sqlite3.Row, group_by: str) -> tuple[str, ...]:
    if group_by == "total":
        return ("total",)
    if group_by == "project":
        return (str(row["project"] or ""),)
    if group_by == "stage":
        return (str(row["stage_name"] or ""),)
    if group_by == "phase":
        return (str(row["stage_name"] or ""), str(row["phase_name"] or ""))
    if group_by == "task":
        return (str(row["task_id"] or ""),)
    if group_by == "tier":
        return (str(row["tier"] or ""),)
    return (str(row["tier"] or ""), str(row["account"] or ""), str(row["model"] or ""))


# 用途：
# - 为 LLM stats SQLite 连接启用 WAL，避免 Dashboard 读请求阻塞 runtime 写入
# 输入：
# - conn: 已打开的 SQLite 连接
# 输出：
# - 无；SQLite 会在无法切换时按 busy_timeout 等待
def _ensure_wal_mode(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")


# 用途：
# - 持久化并聚合 llm_tier 的统一 LLM 调用统计
# 输入：
# - stats_dir: tier runtime 统计目录
# 输出：
# - write/get_events/get_stats/get_summary 查询接口
class StatsCollector:
    # 用途：
    # - 初始化 SQLite stats store
    # 输入：
    # - stats_dir: tier runtime 统计目录
    # 输出：
    # - 可读写的 StatsCollector 实例
    def __init__(self, stats_dir: str) -> None:
        self._stats_dir = Path(stats_dir)
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._db_file = self._stats_dir / "llm_stats.sqlite3"
        self._db_lock = sqlite_operation_lock()
        self._write_failure_count = 0
        self._last_write_error_type = ""
        self._read_failure_count = 0
        self._last_read_error_type = ""
        self._init_db()

    # 用途：
    # - 记录一次 LLM 调用事件到 SQLite
    # 输入：
    # - event: tier router/server 生成的 LLM 调用统计事件
    # 输出：
    # - 无；写入失败时记录 authority 状态并原样抛出
    def write(self, event: dict[str, Any]) -> None:
        normalized = self._normalize_event(event)
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    self._insert_event(conn, normalized)
                    conn.commit()
        except Exception as exc:
            self._write_failure_count += 1
            self._last_write_error_type = type(exc).__name__
            raise

    # Purpose: Return the authoritative SQLite store health without reading secondary sources.
    # Inputs: Internal read/write failure counters accumulated by this collector instance.
    # Outputs: Stable health payload used by HTTP APIs to expose store failures.
    def authority_status(self) -> dict[str, Any]:
        healthy = self._write_failure_count == 0 and self._read_failure_count == 0
        return {
            "ok": healthy,
            "write_failure_count": self._write_failure_count,
            "read_failure_count": self._read_failure_count,
            "last_write_error_type": self._last_write_error_type,
            "last_read_error_type": self._last_read_error_type,
        }

    # Purpose: Record one authoritative stats read failure for later API disclosure.
    # Inputs: Exception raised while querying the SQLite store.
    # Outputs: None; increments the in-memory failure state.
    def _record_read_failure(self, exc: Exception) -> None:
        self._read_failure_count += 1
        self._last_read_error_type = type(exc).__name__

    # 用途：
    # - 按 query 聚合 llm_tier runtime 统计
    # 输入：
    # - query: project/stage/phase/task/backend/tier 等过滤条件
    # 输出：
    # - 已聚合的 TierStatsRow 列表
    def get_stats(self, query: TierStatsQuery) -> list[TierStatsRow]:
        events = self.get_events(query)
        if not events:
            return []
        return self._aggregate(events)

    # 用途：
    # - 按 project/stage/phase/task/tier/backend 从 SQLite 读取并在后端聚合 LLM 统计
    # 输入：
    # - query/group_by: 过滤条件和目标分组层级
    # 输出：
    # - JSON 可序列化聚合行列表；不返回原始 event
    def get_grouped_stats(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]:
        normalized_group = str(group_by or "").strip().lower()
        if normalized_group not in {"total", "project", "stage", "phase", "task", "tier", "backend"}:
            return []
        materialized = self._load_completed_grouped_summary(query, group_by=normalized_group)
        if normalized_group == "task" and materialized:
            return self._merge_task_group_materialized_and_live(
                query=query,
                materialized=materialized,
            )
        if materialized:
            return materialized
        return self._get_grouped_stats_from_events(query, group_by=normalized_group)

    # 用途：
    # - 从 live event 表按 total/project/stage/phase/task/tier/backend 聚合 LLM 统计
    # 输入：
    # - query/group_by: 过滤条件和目标分组层级
    # 输出：
    # - JSON 可序列化聚合行列表；不返回原始 event
    def _get_grouped_stats_from_events(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]:
        normalized_group = str(group_by or "").strip().lower()
        clauses, values = self._where_clause(query)
        clauses.extend(["backend != ''", "model != ''"])
        sql = (
            "SELECT project, stage_name, phase_name, task_id, task_key, tier, backend, "
            "account, backend_type, model, role, ok, latency_ms, prompt_tokens, completion_tokens, "
            "total_tokens, cached_tokens, prompt_chars, completion_chars, call_count, "
            "failed_call_count, provider_usage_available, usage_source, fallback_count "
            "FROM llm_call"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    rows = conn.execute(sql, values).fetchall()
                    groups: dict[tuple[str, ...], list[sqlite3.Row]] = {}
                    for row in rows:
                        groups.setdefault(_stats_group_key(row=row, group_by=normalized_group), []).append(row)
                    return [
                        self._aggregate_group_rows(group_by=normalized_group, key=key, rows=group_rows)
                        for key, group_rows in sorted(groups.items())
                    ]
        except sqlite3.Error as exc:
            self._record_read_failure(exc)
            return []

    # 用途：
    # - 精确查询 completed scope 的 LLM materialized summary
    # 输入：
    # - query/group_by: 查询条件和分组层级
    # 输出：
    # - 命中时返回 payload 列表；未命中或非精确查询返回空列表
    def _load_completed_grouped_summary(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]:
        started_at = self._started_at_text_from_query(query)
        if group_by != "task" and not started_at:
            return []
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    if group_by == "stage" and query.project_name and query.stage_name:
                        row = conn.execute(
                            """
                            SELECT payload_json FROM llm_stage_summary
                            WHERE project = ? AND stage_name = ? AND started_at = ?
                            """,
                            (query.project_name, query.stage_name, started_at),
                        ).fetchone()
                        return self._summary_payload_rows([row] if row else [])
                    if group_by == "phase" and query.project_name and query.stage_name and query.phase_name:
                        row = conn.execute(
                            """
                            SELECT payload_json FROM llm_phase_summary
                            WHERE project = ? AND stage_name = ? AND phase_name = ? AND started_at = ?
                            """,
                            (query.project_name, query.stage_name, query.phase_name, started_at),
                        ).fetchone()
                        return self._summary_payload_rows([row] if row else [])
                    if group_by == "task" and query.project_name:
                        return self._load_completed_task_group_summaries(conn=conn, query=query)
        except sqlite3.Error as exc:
            self._record_read_failure(exc)
            return []
        return []

    # 用途：
    # - 合并 task-level completed LLM summary 与 running task live event 聚合
    # 输入：
    # - query/materialized: task stats 查询条件和已命中的 completed summary rows
    # 输出：
    # - 已完成 task 使用 summary，未完成 task 使用 live event 的聚合结果
    def _merge_task_group_materialized_and_live(
        self,
        *,
        query: TierStatsQuery,
        materialized: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        live_rows = self._get_grouped_stats_from_events(query, group_by="task")
        materialized_keys = {
            str(row.get("task_identity") or row.get("task_id") or "").strip()
            for row in materialized
            if str(row.get("task_identity") or row.get("task_id") or "").strip()
        }
        merged = list(materialized)
        for row in live_rows:
            key = str(row.get("task_identity") or row.get("task_id") or "").strip()
            if key and key in materialized_keys:
                continue
            merged.append(row)
        return sorted(merged, key=lambda row: str(row.get("task_identity") or row.get("task_id") or ""))

    # 用途：
    # - 返回 llm_tier runtime 原始统计事件，供 dashboard 按 stage/phase/task 直接读取
    # 输入：
    # - query: project/stage/phase/task/backend/tier 等过滤条件
    # 输出：
    # - 已过滤并按时间倒序截断的 stats event 列表
    def get_events(self, query: TierStatsQuery) -> list[dict[str, Any]]:
        clauses, values = self._where_clause(query)
        sql = (
            "SELECT raw_json, ts, ts_epoch, project, stage_name, phase_name, task_id, task_key, "
            "tier, backend, account, backend_type, model, role, prompt_name, prompt_kind, ok, "
            "latency_ms, call_count, failed_call_count, prompt_tokens, completion_tokens, total_tokens, "
            "cached_tokens, prompt_chars, completion_chars, provider_usage_available, usage_source, "
            "is_fallback, fallback_count FROM llm_call"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        values.append(int(query.limit or 100))
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    rows = conn.execute(sql, values).fetchall()
        except sqlite3.Error as exc:
            self._record_read_failure(exc)
            return []
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(self._event_from_row(row))
        return events

    # 用途：
    # - 聚合当前 llm_tier runtime 统计摘要，可复用同一套 query 过滤条件
    # 输入：
    # - query: 可选 project/stage/phase/task/backend/tier 过滤条件
    # 输出：
    # - total_calls、total_tokens、fallback 与 active_backends 摘要
    def get_summary(self, query: TierStatsQuery | None = None) -> dict[str, Any]:
        resolved_query = replace(query) if query else TierStatsQuery()
        resolved_query.limit = max(int(resolved_query.limit or 0), 99999)
        all_rows = self.get_stats(resolved_query)
        total_calls = sum(r.calls for r in all_rows)
        total_tokens = sum(r.total_tokens for r in all_rows)
        total_fallback = sum(r.fallback_count for r in all_rows)
        active = sorted({r.backend for r in all_rows if r.backend})
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_fallback_count": total_fallback,
            "active_backends": active,
        }

    # 用途：
    # - 打开 SQLite 连接并使用 Row 访问字段
    # 输入：
    # - 无；读取 collector 的 db path
    # 输出：
    # - sqlite3.Connection
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_file, timeout=LLM_STATS_SQLITE_BUSY_TIMEOUT_MS / 1000)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {LLM_STATS_SQLITE_BUSY_TIMEOUT_MS}")
        return conn

    # 用途：
    # - 创建 stats table 和常用查询索引
    # 输入：
    # - 无；读取 collector 的 db path
    # 输出：
    # - 无；确保 schema 可用
    def _init_db(self) -> None:
        with self._db_lock:
            with closing(self._connect()) as conn:
                _ensure_wal_mode(conn)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_call (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT NOT NULL,
                        ts_epoch REAL NOT NULL,
                        project TEXT NOT NULL,
                        stage_name TEXT NOT NULL,
                        phase_name TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        task_key TEXT NOT NULL,
                        tier TEXT NOT NULL,
                        backend TEXT NOT NULL,
                        account TEXT NOT NULL DEFAULT '',
                        backend_type TEXT NOT NULL,
                        model TEXT NOT NULL,
                        role TEXT NOT NULL,
                        prompt_name TEXT NOT NULL,
                        prompt_kind TEXT NOT NULL,
                        ok INTEGER NOT NULL,
                        latency_ms REAL NOT NULL,
                        call_count INTEGER NOT NULL DEFAULT 1,
                        failed_call_count INTEGER NOT NULL DEFAULT 0,
                        prompt_tokens INTEGER NOT NULL,
                        completion_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        cached_tokens INTEGER NOT NULL DEFAULT 0,
                        prompt_chars INTEGER NOT NULL,
                        completion_chars INTEGER NOT NULL,
                        provider_usage_available INTEGER NOT NULL DEFAULT 0,
                        usage_source TEXT NOT NULL DEFAULT '',
                        is_fallback INTEGER NOT NULL,
                        fallback_count INTEGER NOT NULL,
                        raw_json TEXT NOT NULL
                    )
                    """
                )
                self._ensure_llm_call_columns(conn)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_call_task "
                    "ON llm_call(project, stage_name, phase_name, task_id, task_key)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_call_backend "
                    "ON llm_call(tier, account, model)"
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_call_ts ON llm_call(ts_epoch)")
                conn.execute("DROP TABLE IF EXISTS llm_aggregate_cache")
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS llm_stage_summary (
                        project TEXT NOT NULL,
                        stage_name TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (project, stage_name, started_at)
                    );
                    CREATE TABLE IF NOT EXISTS llm_phase_summary (
                        project TEXT NOT NULL,
                        stage_name TEXT NOT NULL,
                        phase_name TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (project, stage_name, phase_name, started_at)
                    );
                    CREATE TABLE IF NOT EXISTS llm_task_summary (
                        project TEXT NOT NULL,
                        stage_name TEXT NOT NULL,
                        phase_name TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (project, stage_name, phase_name, task_id, started_at)
                    );
                    """
                )
                conn.commit()

    # 用途：
    # - 将已有 llm_call 表升级到当前 stats schema
    # 输入：
    # - conn: 已打开的 SQLite 连接
    # 输出：
    # - 无；缺失列通过 ALTER TABLE 补齐
    def _ensure_llm_call_columns(self, conn: sqlite3.Connection) -> None:
        existing = {str(row[1]) for row in conn.execute("PRAGMA table_info(llm_call)").fetchall()}
        migrations = {
            "call_count": "ALTER TABLE llm_call ADD COLUMN call_count INTEGER NOT NULL DEFAULT 1",
            "failed_call_count": "ALTER TABLE llm_call ADD COLUMN failed_call_count INTEGER NOT NULL DEFAULT 0",
            "cached_tokens": "ALTER TABLE llm_call ADD COLUMN cached_tokens INTEGER NOT NULL DEFAULT 0",
            "provider_usage_available": (
                "ALTER TABLE llm_call ADD COLUMN provider_usage_available INTEGER NOT NULL DEFAULT 0"
            ),
            "usage_source": "ALTER TABLE llm_call ADD COLUMN usage_source TEXT NOT NULL DEFAULT ''",
            "account": "ALTER TABLE llm_call ADD COLUMN account TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in existing:
                conn.execute(statement)

    # 用途：
    # - 固化已完成 Stage / Phase / Task 的 LLM 聚合摘要
    # 输入：
    # - scope/project/stage/phase/task_id/started_at: runtime summary scope 和边界
    # 输出：
    # - 无；直接 upsert 对应 llm_*_summary 表
    def sync_completed_summary(
        self,
        *,
        scope: str,
        project: str,
        stage_name: str,
        phase_name: str = "",
        task_id: str = "",
        started_at: str = "",
    ) -> None:
        normalized_scope = str(scope or "").strip()
        query = TierStatsQuery(
            project_name=str(project or "").strip(),
            stage_name=str(stage_name or "").strip(),
            phase_name=str(phase_name or "").strip(),
            task_id=str(task_id or "").strip(),
            started_at_epoch=self._parse_time_to_epoch(started_at),
            started_at_text=str(started_at or "").strip(),
            group_by=normalized_scope,
            include_events=False,
            limit=999999,
        )
        rows = self._get_grouped_stats_from_events(query, group_by=normalized_scope)
        if not rows:
            rows = [self._empty_group_summary(query=query, group_by=normalized_scope)]
        payload = rows[0]
        payload["materialized"] = True
        payload["started_at"] = str(started_at or "").strip()
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    if normalized_scope == "stage":
                        conn.execute(
                            """
                            INSERT INTO llm_stage_summary (project, stage_name, started_at, payload_json, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(project, stage_name, started_at) DO UPDATE SET
                              payload_json=excluded.payload_json,
                              updated_at=excluded.updated_at
                            """,
                            (query.project_name, query.stage_name, str(started_at or ""), json.dumps(payload, ensure_ascii=False), time.time()),
                        )
                    elif normalized_scope == "phase":
                        conn.execute(
                            """
                            INSERT INTO llm_phase_summary (project, stage_name, phase_name, started_at, payload_json, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(project, stage_name, phase_name, started_at) DO UPDATE SET
                              payload_json=excluded.payload_json,
                              updated_at=excluded.updated_at
                            """,
                            (
                                query.project_name,
                                query.stage_name,
                                query.phase_name,
                                str(started_at or ""),
                                json.dumps(payload, ensure_ascii=False),
                                time.time(),
                            ),
                        )
                    elif normalized_scope == "task":
                        conn.execute(
                            """
                            INSERT INTO llm_task_summary (project, stage_name, phase_name, task_id, started_at, payload_json, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(project, stage_name, phase_name, task_id, started_at) DO UPDATE SET
                              payload_json=excluded.payload_json,
                              updated_at=excluded.updated_at
                            """,
                            (
                                query.project_name,
                                query.stage_name,
                                query.phase_name,
                                query.task_id,
                                str(started_at or ""),
                                json.dumps(payload, ensure_ascii=False),
                                time.time(),
                            ),
                        )
                    conn.commit()
        except sqlite3.Error:
            return

    # 用途：
    # - 清理指定 scope 的 LLM materialized summary
    # 输入：
    # - scope/project/stage/phase/task_id: 清理范围
    # 输出：
    # - 无；直接删除 llm_*_summary 表记录
    def clear_completed_summary(
        self,
        *,
        scope: str,
        project: str,
        stage_name: str,
        phase_name: str = "",
        task_id: str = "",
    ) -> None:
        normalized_scope = str(scope or "").strip()
        try:
            with self._db_lock:
                with closing(self._connect()) as conn:
                    if normalized_scope == "stage":
                        conn.execute("DELETE FROM llm_task_summary WHERE project = ? AND stage_name = ?", (project, stage_name))
                        conn.execute("DELETE FROM llm_phase_summary WHERE project = ? AND stage_name = ?", (project, stage_name))
                        conn.execute("DELETE FROM llm_stage_summary WHERE project = ? AND stage_name = ?", (project, stage_name))
                    elif normalized_scope == "phase":
                        conn.execute(
                            "DELETE FROM llm_task_summary WHERE project = ? AND stage_name = ? AND phase_name = ?",
                            (project, stage_name, phase_name),
                        )
                        conn.execute(
                            "DELETE FROM llm_phase_summary WHERE project = ? AND stage_name = ? AND phase_name = ?",
                            (project, stage_name, phase_name),
                        )
                    elif normalized_scope == "task":
                        conn.execute(
                            "DELETE FROM llm_task_summary WHERE project = ? AND stage_name = ? AND phase_name = ? AND task_id = ?",
                            (project, stage_name, phase_name, task_id),
                        )
                    conn.commit()
        except sqlite3.Error:
            return

    # 用途：
    # - 批量解析 llm_*_summary 表中的 payload_json
    # 输入：
    # - rows: SQLite rows，每行包含 payload_json
    # 输出：
    # - JSON object 列表
    def _summary_payload_rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for row in rows:
            if row is None:
                continue
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                payloads.append(payload)
        return payloads

    # 用途：
    # - 为 task group 查询读取已完成 Task 的 LLM materialized summary
    # 输入：
    # - conn/query: SQLite 连接和 task stats 查询条件
    # 输出：
    # - 已命中的 task summary rows；非精确 task 查询返回空列表
    def _load_completed_task_group_summaries(self, *, conn: sqlite3.Connection, query: TierStatsQuery) -> list[dict[str, Any]]:
        started_at_map = {
            str(task_id): str(started_at)
            for task_id, started_at in dict(getattr(query, "task_started_at_texts", {}) or {}).items()
            if str(task_id or "").strip() and str(started_at or "").strip()
        }
        if not started_at_map:
            started_at_map = {
                task_id: self._epoch_to_started_at_text(epoch)
                for task_id, epoch in dict(query.task_started_at_epochs or {}).items()
                if str(task_id or "").strip() and float(epoch or 0) > 0
            }
        if query.task_id and self._started_at_text_from_query(query):
            started_at_map = {query.task_id: self._started_at_text_from_query(query)}
        if not started_at_map:
            return []
        payloads: list[dict[str, Any]] = []
        for task_id, started_at in sorted(started_at_map.items()):
            row = conn.execute(
                """
                SELECT payload_json FROM llm_task_summary
                WHERE project = ? AND task_id = ? AND started_at = ?
                """,
                (query.project_name, task_id, started_at),
            ).fetchone()
            payloads.extend(self._summary_payload_rows([row] if row else []))
        return payloads

    # 用途：
    # - 构造无调用的空 LLM 聚合 summary，保证 completed scope 可以固化 0 calls
    # 输入：
    # - query/group_by: summary 身份和分组层级
    # 输出：
    # - Dashboard 可消费的空聚合行
    def _empty_group_summary(self, *, query: TierStatsQuery, group_by: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "group_by": group_by,
            "project_name": query.project_name,
            "stage_name": query.stage_name if group_by in {"stage", "phase", "task"} else "",
            "phase_name": query.phase_name if group_by in {"phase", "task"} else "",
            "task_id": query.task_id if group_by == "task" else "",
            "task_key": query.task_id.split("::")[-1] if group_by == "task" and query.task_id else "",
            "calls": 0,
            "success_count": 0,
            "fail_count": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_tokens": 0,
            "prompt_chars": 0,
            "completion_chars": 0,
            "latency_ms_total": 0,
            "latency_sample_count": 0,
            "fallback_count": 0,
            "has_prompt_tokens": False,
            "has_completion_tokens": False,
            "unknown_split_tokens": 0,
        }
        if group_by == "stage":
            payload["stage"] = query.stage_name
        if group_by == "phase":
            payload["phase_key"] = f"{query.stage_name}::{query.phase_name}"
        if group_by == "task":
            payload["task_identity"] = query.task_id
        for field in (
            "prompt_tokens_avg",
            "prompt_tokens_p50",
            "prompt_tokens_p70",
            "prompt_tokens_p95",
            "prompt_tokens_p99",
            "completion_tokens_avg",
            "completion_tokens_p50",
            "completion_tokens_p70",
            "completion_tokens_p95",
            "completion_tokens_p99",
            "prompt_chars_avg",
            "prompt_chars_p50",
            "prompt_chars_p70",
            "prompt_chars_p95",
            "prompt_chars_p99",
            "completion_chars_avg",
            "completion_chars_p50",
            "completion_chars_p70",
            "completion_chars_p95",
            "completion_chars_p99",
            "latency_avg_ms",
            "latency_p50_ms",
            "latency_p70_ms",
            "latency_p90_ms",
            "latency_p95_ms",
            "latency_p99_ms",
        ):
            payload[field] = 0
        return payload

    # 用途：
    # - 获取 query 中原始 started_at 文本
    # 输入：
    # - query: stats 查询条件
    # 输出：
    # - 原始 started_at 文本；缺失时为空
    def _started_at_text_from_query(self, query: TierStatsQuery) -> str:
        return str(getattr(query, "started_at_text", "") or "").strip()

    # 用途：
    # - 将 summary started_at 文本解析为 epoch
    # 输入：
    # - value: ISO 或 epoch 时间
    # 输出：
    # - 秒级 epoch；解析失败返回 0
    def _parse_time_to_epoch(self, value: Any) -> float:
        text = str(value or "").strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return self._parse_iso_time_to_epoch(text)

    # 用途：
    # - 将 ISO started_at 文本解析为 epoch
    # 输入：
    # - value: ISO UTC 时间文本
    # 输出：
    # - 秒级 epoch；解析失败返回 0
    def _parse_iso_time_to_epoch(self, value: str) -> float:
        try:
            parsed = time.strptime(value.replace("Z", "").split(".", 1)[0], "%Y-%m-%dT%H:%M:%S")
            return float(calendar.timegm(parsed))
        except ValueError:
            return 0.0

    # 用途：
    # - 将 task_started_at_map 中的 epoch 还原为 summary key 文本
    # 输入：
    # - epoch: 秒级 epoch
    # 输出：
    # - UTC ISO 文本
    def _epoch_to_started_at_text(self, epoch: float) -> str:
        return self._iso_timestamp(float(epoch or 0))

    # 用途：
    # - 将 event 规范化为 SQLite schema 字段
    # 输入：
    # - event: 原始统计事件
    # 输出：
    # - 字段完整、类型稳定的 event 字典
    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        raw_event = dict(event or {})
        metadata = raw_event.get("metadata") if isinstance(raw_event.get("metadata"), dict) else {}
        usage = raw_event.get("usage") if isinstance(raw_event.get("usage"), dict) else {}
        prompt_tokens = self._int_value(raw_event.get("prompt_tokens") or usage.get("prompt_tokens"))
        completion_tokens = self._int_value(raw_event.get("completion_tokens") or usage.get("completion_tokens"))
        total_tokens = self._int_value(raw_event.get("total_tokens") or usage.get("total_tokens"))
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens
        has_explicit_call_count = "call_count" in raw_event or "call_count" in usage
        call_count = self._int_value(raw_event.get("call_count") if "call_count" in raw_event else usage.get("call_count"))
        if call_count <= 0 and not has_explicit_call_count and self._is_aggregate_call_event(raw_event):
            call_count = 1
        failed_call_count = self._int_value(raw_event.get("failed_call_count") or usage.get("failed_call_count"))
        ts_epoch = self._event_epoch(raw_event)
        task_id = str(raw_event.get("task_id") or metadata.get("task_id") or "")
        task_parts = task_id.split("::")
        stage_name = str(raw_event.get("stage_name") or metadata.get("stage_name") or metadata.get("stage") or "")
        phase_name = str(raw_event.get("phase_name") or metadata.get("phase_name") or metadata.get("phase") or "")
        task_key = str(raw_event.get("task_key") or metadata.get("task_key") or "")
        if not stage_name and len(task_parts) >= 1:
            stage_name = task_parts[0]
        if not phase_name and len(task_parts) >= 2:
            phase_name = task_parts[1]
        if not task_key and len(task_parts) >= 3:
            task_key = "::".join(task_parts[2:])
        ok_value = raw_event.get("ok")
        if ok_value is None:
            ok_value = str(raw_event.get("status") or "").strip().lower() in {"ok", "success", "accepted"}
        if failed_call_count <= 0 and call_count > 0 and not bool(ok_value):
            failed_call_count = call_count
        backend = str(raw_event.get("backend") or "")
        model = str(raw_event.get("model") or raw_event.get("model_name") or "")
        account = str(raw_event.get("account") or raw_event.get("account_id") or "")
        if backend and model and not account:
            raise ValueError("account is required for Backend stats events")
        return {
            **raw_event,
            "ts": str(raw_event.get("ts") or self._iso_timestamp(ts_epoch)),
            "ts_epoch": ts_epoch,
            "project": str(
                raw_event.get("project")
                or raw_event.get("project_name")
                or metadata.get("project")
                or metadata.get("project_name")
                or ""
            ),
            "stage_name": stage_name,
            "phase_name": phase_name,
            "task_id": task_id,
            "task_key": task_key,
            "tier": str(raw_event.get("tier") or ""),
            "backend": backend,
            "account": account,
            "backend_type": str(raw_event.get("backend_type") or ""),
            "model": model,
            "role": str(raw_event.get("role") or raw_event.get("role_name") or ""),
            "prompt_name": str(raw_event.get("prompt_name") or ""),
            "prompt_kind": str(raw_event.get("prompt_kind") or ""),
            "ok": bool(ok_value),
            "latency_ms": self._float_value(raw_event.get("latency_ms") or usage.get("latency_ms")),
            "call_count": call_count,
            "failed_call_count": max(0, min(failed_call_count, call_count)) if call_count > 0 else 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": self._int_value(raw_event.get("cached_tokens") or usage.get("cached_tokens")),
            "prompt_chars": self._int_value(raw_event.get("prompt_chars") or usage.get("prompt_chars")),
            "completion_chars": self._int_value(raw_event.get("completion_chars") or usage.get("completion_chars")),
            "provider_usage_available": bool(
                raw_event.get("provider_usage_available") or usage.get("provider_usage_available")
            ),
            "usage_source": str(raw_event.get("usage_source") or usage.get("usage_source") or ""),
            "is_fallback": bool(raw_event.get("is_fallback")),
            "fallback_count": self._int_value(raw_event.get("fallback_count")),
        }

    # 用途：
    # - 写入一条规范化事件
    # 输入：
    # - conn/event: SQLite 连接和规范化后的 event
    # 输出：
    # - 无；事件插入 llm_call
    def _insert_event(self, conn: sqlite3.Connection, event: dict[str, Any]) -> None:
        conn.execute(
            """
            INSERT INTO llm_call (
                ts, ts_epoch, project, stage_name, phase_name, task_id, task_key,
                tier, backend, account, backend_type, model, role, prompt_name, prompt_kind,
                ok, latency_ms, call_count, failed_call_count, prompt_tokens, completion_tokens,
                total_tokens, cached_tokens, prompt_chars, completion_chars, provider_usage_available,
                usage_source, is_fallback, fallback_count, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["ts"],
                event["ts_epoch"],
                event["project"],
                event["stage_name"],
                event["phase_name"],
                event["task_id"],
                event["task_key"],
                event["tier"],
                event["backend"],
                event["account"],
                event["backend_type"],
                event["model"],
                event["role"],
                event["prompt_name"],
                event["prompt_kind"],
                1 if event["ok"] else 0,
                event["latency_ms"],
                event["call_count"],
                event["failed_call_count"],
                event["prompt_tokens"],
                event["completion_tokens"],
                event["total_tokens"],
                event["cached_tokens"],
                event["prompt_chars"],
                event["completion_chars"],
                1 if event["provider_usage_available"] else 0,
                event["usage_source"],
                1 if event["is_fallback"] else 0,
                event["fallback_count"],
                json.dumps(event, ensure_ascii=False),
            ),
        )

    # 用途：
    # - 构造 SQLite WHERE 条件
    # 输入：
    # - query: stats 查询条件
    # 输出：
    # - SQL 条件片段和参数列表
    def _where_clause(self, query: TierStatsQuery) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        mapping = {
            "project_name": "project",
            "stage_name": "stage_name",
            "phase_name": "phase_name",
            "task_id": "task_id",
            "task_key": "task_key",
            "tier": "tier",
            "backend": "backend",
            "role_name": "role",
        }
        for query_field, column in mapping.items():
            value = str(getattr(query, query_field) or "")
            if value:
                clauses.append(f"{column} = ?")
                values.append(value)
        task_id_prefix = str(query.task_id_prefix or "").strip()
        if task_id_prefix:
            clauses.append("task_id LIKE ? ESCAPE '\\'")
            values.append(f"{self._escape_like(task_id_prefix)}%")
        task_started_at_epochs = {
            str(task_id): float(started_at)
            for task_id, started_at in dict(query.task_started_at_epochs or {}).items()
            if str(task_id or "").strip() and float(started_at or 0) > 0
        }
        if task_started_at_epochs:
            task_clauses: list[str] = []
            for task_id, started_at in sorted(task_started_at_epochs.items()):
                task_clauses.append("(task_id = ? AND ts_epoch >= ?)")
                values.extend([task_id, started_at])
            clauses.append("(" + " OR ".join(task_clauses) + ")")
        if query.time_range_hours > 0:
            clauses.append("ts_epoch >= ?")
            values.append(time.time() - query.time_range_hours * 3600)
        if float(query.started_at_epoch or 0) > 0:
            clauses.append("ts_epoch >= ?")
            values.append(float(query.started_at_epoch or 0))
        return clauses, values

    # 用途：
    # - 转义 SQLite LIKE pattern 中的通配符，保证 prefix 查询按字面量匹配
    # 输入：
    # - value: 用户传入的 task_id_prefix
    # 输出：
    # - 可安全拼接 `%` 后缀的 LIKE pattern
    def _escape_like(self, value: str) -> str:
        return str(value or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # 用途：
    # - 将一个 SQLite 分组的 LLM 调用行聚合成 dashboard 可消费的统计行
    # 输入：
    # - group_by/key/rows: 分组层级、分组 key 和 SQLite 行集合
    # 输出：
    # - JSON 可序列化聚合 dict
    def _aggregate_group_rows(
        self,
        *,
        group_by: str,
        key: tuple[str, ...],
        rows: list[sqlite3.Row],
    ) -> dict[str, Any]:
        prompt_tokens = [self._int_value(row["prompt_tokens"]) for row in rows]
        completion_tokens = [self._int_value(row["completion_tokens"]) for row in rows]
        cached_tokens = [self._int_value(row["cached_tokens"]) for row in rows]
        prompt_chars = [self._int_value(row["prompt_chars"]) for row in rows]
        completion_chars = [self._int_value(row["completion_chars"]) for row in rows]
        latencies = [self._float_value(row["latency_ms"]) for row in rows]
        call_counts = [self._int_value(row["call_count"]) for row in rows]
        failed_call_counts = [self._int_value(row["failed_call_count"]) for row in rows]
        calls = sum(call_counts)
        first = rows[0]
        result: dict[str, Any] = {
            "group_by": group_by,
            "project_name": str(first["project"] or ""),
            "stage_name": str(first["stage_name"] or ""),
            "phase_name": str(first["phase_name"] or ""),
            "task_id": str(first["task_id"] or ""),
            "task_key": str(first["task_key"] or ""),
            "tier": str(first["tier"] or ""),
            "backend": str(first["backend"] or ""),
            "account": str(first["account"] or ""),
            "backend_type": str(first["backend_type"] or ""),
            "model_name": str(first["model"] or ""),
            "role_name": str(first["role"] or ""),
            "calls": calls,
            "success_count": sum(
                max(0, self._int_value(row["call_count"]) - self._int_value(row["failed_call_count"]))
                for row in rows
                if bool(row["ok"])
            ),
            "fail_count": sum(
                self._int_value(row["failed_call_count"]) if bool(row["ok"]) else self._int_value(row["call_count"])
                for row in rows
            ),
            "total_tokens": sum(self._int_value(row["total_tokens"]) for row in rows),
            "prompt_tokens": sum(prompt_tokens),
            "completion_tokens": sum(completion_tokens),
            "cached_tokens": sum(cached_tokens),
            "prompt_tokens_avg": self._avg_positive(prompt_tokens),
            "prompt_tokens_p50": self._percentile_positive(prompt_tokens, 0.50),
            "prompt_tokens_p70": self._percentile_positive(prompt_tokens, 0.70),
            "prompt_tokens_p95": self._percentile_positive(prompt_tokens, 0.95),
            "prompt_tokens_p99": self._percentile_positive(prompt_tokens, 0.99),
            "completion_tokens_avg": self._avg_positive(completion_tokens),
            "completion_tokens_p50": self._percentile_positive(completion_tokens, 0.50),
            "completion_tokens_p70": self._percentile_positive(completion_tokens, 0.70),
            "completion_tokens_p95": self._percentile_positive(completion_tokens, 0.95),
            "completion_tokens_p99": self._percentile_positive(completion_tokens, 0.99),
            "prompt_chars": sum(prompt_chars),
            "prompt_chars_avg": self._avg_positive(prompt_chars),
            "prompt_chars_p50": self._percentile_positive(prompt_chars, 0.50),
            "prompt_chars_p70": self._percentile_positive(prompt_chars, 0.70),
            "prompt_chars_p95": self._percentile_positive(prompt_chars, 0.95),
            "prompt_chars_p99": self._percentile_positive(prompt_chars, 0.99),
            "completion_chars": sum(completion_chars),
            "completion_chars_avg": self._avg_positive(completion_chars),
            "completion_chars_p50": self._percentile_positive(completion_chars, 0.50),
            "completion_chars_p70": self._percentile_positive(completion_chars, 0.70),
            "completion_chars_p95": self._percentile_positive(completion_chars, 0.95),
            "completion_chars_p99": self._percentile_positive(completion_chars, 0.99),
            "latency_ms_total": sum(latencies),
            "latency_sample_count": len([value for value in latencies if value > 0]),
            "latency_avg_ms": self._avg_positive(latencies),
            "latency_p50_ms": self._percentile_positive(latencies, 0.50),
            "latency_p70_ms": self._percentile_positive(latencies, 0.70),
            "latency_p90_ms": self._percentile_positive(latencies, 0.90),
            "latency_p95_ms": self._percentile_positive(latencies, 0.95),
            "latency_p99_ms": self._percentile_positive(latencies, 0.99),
            "fallback_count": sum(self._int_value(row["fallback_count"]) for row in rows),
            "latencies": [],
            "prompt_token_samples": [],
            "completion_token_samples": [],
            "prompt_lengths": [],
            "completion_lengths": [],
            "has_prompt_tokens": any(value > 0 for value in prompt_tokens),
            "has_completion_tokens": any(value > 0 for value in completion_tokens),
            "unknown_split_tokens": 0,
        }
        if group_by == "total":
            result["label"] = "Total"
            result["project_name"] = ""
            self._clear_non_group_identity_fields(result, keep=set())
        elif group_by == "project":
            result["project"] = key[0]
            result["project_name"] = key[0]
            self._clear_non_group_identity_fields(result, keep={"project_name"})
        elif group_by == "stage":
            result["stage"] = key[0]
            result["stage_name"] = key[0]
            self._clear_non_group_identity_fields(result, keep={"project_name", "stage_name"})
        elif group_by == "phase":
            result["stage_name"] = key[0]
            result["phase_name"] = key[1] if len(key) > 1 else ""
            result["phase_key"] = "::".join(key)
            self._clear_non_group_identity_fields(result, keep={"project_name", "stage_name", "phase_name"})
        elif group_by == "task":
            result["task_identity"] = key[0]
            self._clear_non_group_identity_fields(
                result,
                keep={"project_name", "stage_name", "phase_name", "task_id", "task_key"},
            )
        elif group_by == "tier":
            result["tier"] = key[0]
            self._clear_non_group_identity_fields(result, keep={"tier"})
        elif group_by == "backend":
            result["model"] = result["model_name"]
            if len(key) > 1:
                result["account"] = key[1]
        return result

    # 用途：
    # - 清除非当前分组维度的样本身份字段，避免聚合行暴露第一条 event 的 backend/model/role
    # 输入：
    # - result/keep: 聚合结果和必须保留的身份字段集合
    # 输出：
    # - 无；原地更新 result
    def _clear_non_group_identity_fields(self, result: dict[str, Any], *, keep: set[str]) -> None:
        for field in (
            "stage_name",
            "phase_name",
            "task_id",
            "task_key",
            "tier",
            "backend",
            "account",
            "backend_type",
            "model_name",
            "role_name",
        ):
            if field not in keep:
                result[field] = ""

    # 用途：
    # - 将 SQLite row 还原为 stats event
    # 输入：
    # - row: llm_call 查询结果
    # 输出：
    # - 包含 raw_json 原始字段和规范化字段的 event 字典
    def _event_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            event = json.loads(str(row["raw_json"] or "{}"))
        except json.JSONDecodeError:
            event = {}
        event.update(
            {
                "ts": row["ts"],
                "ts_epoch": row["ts_epoch"],
                "project": row["project"],
                "stage_name": row["stage_name"],
                "phase_name": row["phase_name"],
                "task_id": row["task_id"],
                "task_key": row["task_key"],
                "tier": row["tier"],
                "backend": row["backend"],
                "account": row["account"],
                "backend_type": row["backend_type"],
                "model": row["model"],
                "role": row["role"],
                "prompt_name": row["prompt_name"],
                "prompt_kind": row["prompt_kind"],
                "ok": bool(row["ok"]),
                "latency_ms": row["latency_ms"],
                "call_count": row["call_count"],
                "failed_call_count": row["failed_call_count"],
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "cached_tokens": row["cached_tokens"],
                "prompt_chars": row["prompt_chars"],
                "completion_chars": row["completion_chars"],
                "provider_usage_available": bool(row["provider_usage_available"]),
                "usage_source": row["usage_source"],
                "is_fallback": bool(row["is_fallback"]),
                "fallback_count": row["fallback_count"],
            }
        )
        return event

    # 用途：
    # - 将过滤后的事件按 tier/account/model 聚合成 dashboard 行
    # 输入：
    # - events: 已过滤的 stats event 列表
    # 输出：
    # - TierStatsRow 列表
    def _aggregate(self, events: list[dict[str, Any]]) -> list[TierStatsRow]:
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for event in events:
            if not self._is_aggregate_call_event(event):
                continue
            key = (
                str(event.get("tier") or ""),
                str(event.get("account") or ""),
                str(event.get("model") or ""),
            )
            groups.setdefault(key, []).append(event)

        rows: list[TierStatsRow] = []
        for key, group in groups.items():
            tier, account, model = key
            backend = str(group[0].get("backend", ""))
            counts = sum(self._int_value(event.get("call_count")) for event in group)
            successes = sum(
                max(
                    0,
                    self._int_value(event.get("call_count"))
                    - self._int_value(event.get("failed_call_count")),
                )
                for event in group
                if event.get("ok")
            )
            prompt_tokens = [self._int_value(event.get("prompt_tokens")) for event in group]
            completion_tokens = [self._int_value(event.get("completion_tokens")) for event in group]
            cached_tokens = [self._int_value(event.get("cached_tokens")) for event in group]
            prompt_chars = [self._int_value(event.get("prompt_chars")) for event in group]
            completion_chars = [self._int_value(event.get("completion_chars")) for event in group]
            latencies = [self._float_value(event.get("latency_ms")) for event in group]
            fallback = sum(self._int_value(event.get("fallback_count")) for event in group)
            failures = sum(
                self._int_value(event.get("failed_call_count"))
                if event.get("ok")
                else self._int_value(event.get("call_count"))
                for event in group
            )
            rows.append(
                TierStatsRow(
                    project_name=str(group[0].get("project", "")),
                    tier=tier,
                    backend=backend,
                    backend_type=str(group[0].get("backend_type", "")),
                    model_name=model,
                    role_name=str(group[0].get("role", "")),
                    account=account,
                    calls=counts,
                    success_count=successes,
                    fail_count=failures,
                    total_tokens=sum(self._int_value(event.get("total_tokens")) for event in group),
                    prompt_tokens=sum(prompt_tokens),
                    completion_tokens=sum(completion_tokens),
                    cached_tokens=sum(cached_tokens),
                    prompt_tokens_avg=self._avg_positive(prompt_tokens),
                    prompt_tokens_p50=self._percentile_positive(prompt_tokens, 0.50),
                    prompt_tokens_p70=self._percentile_positive(prompt_tokens, 0.70),
                    prompt_tokens_p95=self._percentile_positive(prompt_tokens, 0.95),
                    prompt_tokens_p99=self._percentile_positive(prompt_tokens, 0.99),
                    completion_tokens_avg=self._avg_positive(completion_tokens),
                    completion_tokens_p50=self._percentile_positive(completion_tokens, 0.50),
                    completion_tokens_p70=self._percentile_positive(completion_tokens, 0.70),
                    completion_tokens_p95=self._percentile_positive(completion_tokens, 0.95),
                    completion_tokens_p99=self._percentile_positive(completion_tokens, 0.99),
                    prompt_chars=sum(prompt_chars),
                    prompt_chars_avg=self._avg_positive(prompt_chars),
                    prompt_chars_p50=self._percentile_positive(prompt_chars, 0.50),
                    prompt_chars_p70=self._percentile_positive(prompt_chars, 0.70),
                    prompt_chars_p95=self._percentile_positive(prompt_chars, 0.95),
                    prompt_chars_p99=self._percentile_positive(prompt_chars, 0.99),
                    completion_chars=sum(completion_chars),
                    completion_chars_avg=self._avg_positive(completion_chars),
                    completion_chars_p50=self._percentile_positive(completion_chars, 0.50),
                    completion_chars_p70=self._percentile_positive(completion_chars, 0.70),
                    completion_chars_p95=self._percentile_positive(completion_chars, 0.95),
                    completion_chars_p99=self._percentile_positive(completion_chars, 0.99),
                    latency_avg_ms=self._avg_positive(latencies),
                    latency_p50_ms=self._percentile_positive(latencies, 0.50),
                    latency_p70_ms=self._percentile_positive(latencies, 0.70),
                    latency_p90_ms=self._percentile_positive(latencies, 0.90),
                    latency_p95_ms=self._percentile_positive(latencies, 0.95),
                    latency_p99_ms=self._percentile_positive(latencies, 0.99),
                    fallback_count=fallback,
                    exhausted_count=0,
                )
            )
        return rows

    # 用途：
    # - 判断 stats event 是否代表真实 backend 调用，避免排队 busy 诊断事件污染 calls/token/latency 聚合
    # 输入：
    # - event: 从 stats store 读取的一条事件
    # 输出：
    # - True 表示计入聚合；False 表示只保留为原始诊断事件
    def _is_aggregate_call_event(self, event: dict[str, Any]) -> bool:
        backend = str(event.get("backend") or "").strip()
        model = str(event.get("model") or "").strip()
        if backend and model:
            return True
        error_code = self._int_value(event.get("error_code"))
        error_message = str(event.get("error_message") or "")
        selection_debug = str(event.get("selection_debug") or "")
        if error_code == 1005:
            return False
        if error_message == "all_backends_busy" or error_message.startswith("all_backends_busy:"):
            return False
        if "request_busy" in selection_debug and not backend:
            return False
        return False

    # 用途：
    # - 从 event 中解析或补齐 epoch 时间
    # 输入：
    # - event: 原始统计事件
    # 输出：
    # - 秒级 epoch 时间
    def _event_epoch(self, event: dict[str, Any]) -> float:
        ts_epoch = self._float_value(event.get("ts_epoch"))
        if ts_epoch > 0:
            return ts_epoch
        ts = str(event.get("ts") or "")
        if ts:
            try:
                parsed = time.strptime(ts.replace("Z", "").split(".", 1)[0], "%Y-%m-%dT%H:%M:%S")
                return float(calendar.timegm(parsed))
            except ValueError:
                return time.time()
        return time.time()

    # 用途：
    # - 将 epoch 转为 UTC ISO 字符串
    # 输入：
    # - ts_epoch: 秒级 epoch 时间
    # 输出：
    # - YYYY-MM-DDTHH:MM:SSZ 字符串
    def _iso_timestamp(self, ts_epoch: float) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_epoch))

    # 用途：
    # - 将任意值安全转为 int
    # 输入：
    # - value: 可能为空或字符串的数值
    # 输出：
    # - int 值，无法转换时为 0
    def _int_value(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    # 用途：
    # - 将任意值安全转为 float
    # 输入：
    # - value: 可能为空或字符串的数值
    # 输出：
    # - float 值，无法转换时为 0.0
    def _float_value(self, value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    # 用途：
    # - 计算正数样本平均值，避免缺失 token 被 0 拉低
    # 输入：
    # - values: 样本列表
    # 输出：
    # - 平均值，保留两位小数
    def _avg_positive(self, values: list[int] | list[float]) -> float:
        positives = [float(value) for value in values if float(value) > 0]
        if not positives:
            return 0.0
        return round(sum(positives) / len(positives), 2)

    # 用途：
    # - 计算正数样本百分位，避免缺失 token 被 0 拉低
    # 输入：
    # - values/percentile: 样本列表和 0-1 百分位
    # 输出：
    # - 百分位值，保留两位小数
    def _percentile_positive(self, values: list[int] | list[float], percentile: float) -> float:
        positives = sorted(float(value) for value in values if float(value) > 0)
        if not positives:
            return 0.0
        if len(positives) == 1:
            return round(positives[0], 2)
        position = (len(positives) - 1) * percentile
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return round(positives[lower], 2)
        lower_value = positives[lower]
        upper_value = positives[upper]
        return round(lower_value + (upper_value - lower_value) * (position - lower), 2)
