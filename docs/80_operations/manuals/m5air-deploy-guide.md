<!-- STD_DOCUMENT_COVER_BEGIN -->
# m5air 代码更新与重启指南

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `m5air-deploy-guide` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `operations.maintenance` |
| Template Version | `0.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/80_operations/manuals/m5air-deploy-guide.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 环境信息

| 项目 | 值 |
|------|---|
| 主机 | `192.168.1.9` (m5air) |
| 代码目录 | `/Users/mlp/LLMTier-dev/`（非 git repo，是源码快照） |
| 数据库 | `/Users/mlp/LLMTier-dev/state.sqlite3` |
| 进程端口 | `8181`（监听 `0.0.0.0`） |
| 日志 | `/Users/mlp/LLMTier-dev/llmtier.log` |
| Python | `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` |

---

## 查找当前进程

```bash
ssh m5air "ps aux | grep 'http_api.*8181' | grep -v grep"
```

会返回类似：
```
mlp  24280  ...  /Library/Frameworks/Python.framework/Versions/3.14/...  -m http_api --host 0.0.0.0 --port 8181 ...
```

**记住 PID**（第二列），用于后续 kill。

---

## 同步代码到 m5air

在**本机**（m5mac）执行 rsync，只同步改过的文件：

```bash
# 核心服务（每次必同步）
rsync -avz /Users/ben/work/LLMTier/src/http_api/app.py m5air:/Users/mlp/LLMTier-dev/src/http_api/app.py
rsync -avz /Users/ben/work/LLMTier/src/management/admin.py m5air:/Users/mlp/LLMTier-dev/src/management/admin.py
rsync -avz /Users/ben/work/LLMTier/src/http_api/auth.py m5air:/Users/mlp/LLMTier-dev/src/http_api/auth.py
rsync -avz /Users/ben/work/LLMTier/src/inference/providers/ m5air:/Users/mlp/LLMTier-dev/src/inference/providers/

# WebUI（修改了界面文件时同步）
rsync -avz /Users/ben/work/LLMTier/src/web_ui/app.js m5air:/Users/mlp/LLMTier-dev/src/web_ui/app.js
rsync -avz /Users/ben/work/LLMTier/src/web_ui/index.html m5air:/Users/mlp/LLMTier-dev/src/web_ui/index.html
rsync -avz /Users/ben/work/LLMTier/src/web_ui/styles.css m5air:/Users/mlp/LLMTier-dev/src/web_ui/styles.css
rsync -avz /Users/ben/work/LLMTier/src/web_ui/icons.svg m5air:/Users/mlp/LLMTier-dev/src/web_ui/icons.svg

# 测试文件（修改了测试时同步）
rsync -avz /Users/ben/work/LLMTier/tests/unit/v03/test_webui_contract.py m5air:/Users/mlp/LLMTier-dev/tests/unit/v03/test_webui_contract.py
```

**注意**：`/Users/mlp/LLMTier-dev/` 本身不是 git repo，所以 git push 不会更新 m5air，必须手动 rsync。

---

## 重启服务

```bash
# 1. kill 旧进程（替换 <PID> 为实际进程 ID）
ssh m5air "kill <PID>"

# 2. 等待进程退出
sleep 1

# 3. 启动新进程
ssh m5air "cd /Users/mlp/LLMTier-dev && \
  LLMTIER_ADMIN_TOKEN=dev-admin \
  LLMTIER_DATA_TOKEN=dev-data \
  PYTHONPATH=src \
  /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  -m http_api \
  --host 0.0.0.0 \
  --port 8181 \
  --database /Users/mlp/LLMTier-dev/state.sqlite3 \
  >> /Users/mlp/LLMTier-dev/llmtier.log 2>&1 &"
```

---

## 验证服务正常

```bash
# 健康检查
ssh m5air "curl http://localhost:8181/healthz"

# 带 token 的 API 调用
ssh m5air "curl http://localhost:8181/v1/providers -H 'Authorization: Bearer dev-admin'"

# 验证新功能（以 provider models 为例）
ssh m5air "curl http://localhost:8181/v1/providers/provider_minimax/models -H 'Authorization: Bearer dev-admin'"

# 查看日志
ssh m5air "tail -5 /Users/mlp/LLMTier-dev/llmtier.log"
```

---

## 常见问题

### 启动后 503 auth_not_configured
→ 没加 `LLMTIER_ADMIN_TOKEN` 和 `LLMTIER_DATA_TOKEN` 环境变量。

### 启动后 TypeError: dataclass() got an unexpected keyword argument 'slots'
→ 用了系统 Python 3.9 而不是 3.14。必须用 `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`。

### 改了代码但页面没变化
→ 没重启服务，或者 rsync 没同步到正确的文件。用 `ssh m5air "grep -c '函数名' /Users/mlp/LLMTier-dev/src/<module>/..."` 验证文件内容。

### 浏览器打开页面空白
→ 服务没启动，或网络不通。先 `ssh m5air "curl http://localhost:8181/healthz"` 验证。

---

## 目录结构说明

```
/Users/mlp/LLMTier-dev/          ← m5air 运行目录（不是 git repo）
├── src/<module>/               ← 源码
│   ├── app.py                   ← 主入口
│   ├── admin.py                 ← Admin API
│   ├── auth.py                  ← 认证
│   ├── providers/               ← Provider 适配器
│   └── webui/                   ← Web UI（app.js, index.html, styles.css）
├── state.sqlite3                ← 数据库
├── llmtier.log                  ← 日志
└── secrets/                     ← Provider API key 等密钥
    └── omlx-secret-key.txt
```

### 已删除的空目录
- `/Users/mlp/llmtier-src/` — 已删除（空的）