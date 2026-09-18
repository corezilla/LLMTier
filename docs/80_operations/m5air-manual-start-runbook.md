<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier m5air Manual Start Runbook

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-m5air-manual-start-runbook` |
| Document Version | `0.1.0-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | 待定 |
| Created Date | `2026-09-18` |
| Last Modified Date | `2026-09-18` |
| Template Version | `0.1.0` |
| Template ID | `operations.release` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/80_operations/m5air-manual-start-runbook.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 适用范围

本文说明如何在测试机`m5air`上手工启动、检查、停止和重新启动LLMTier V0.3。该部署不配置
`launchd`、systemd、登录项或任何开机自启；机器重启后服务保持停止，必须由operator再次执行本文启动步骤。

本手册只适用于当前可信局域网测试环境：

| 项目 | 固定值 |
|---|---|
| SSH入口 | `ssh m5air` |
| 项目目录 | `/Users/mlp/LLMTier-dev` |
| Python | `/usr/local/bin/python3`，当前为Python 3.14.3 |
| 数据库 | `/Users/mlp/LLMTier-dev/state.sqlite3` |
| 日志 | `/Users/mlp/LLMTier-dev/llmtier.log` |
| PID文件 | `/Users/mlp/LLMTier-dev/llmtier.pid` |
| 监听地址 | `0.0.0.0:8181` |
| 局域网入口 | `http://192.168.1.9:8181/` |

不要使用`/usr/bin/python3`：m5air上的该解释器当前为Python 3.9.6，低于项目要求的Python 3.11。

## 2. 启动前检查

登录并进入项目目录：

```bash
ssh m5air
cd /Users/mlp/LLMTier-dev
```

确认解释器、数据库和Secret目录存在，并确认8181尚未被占用：

```bash
/usr/local/bin/python3 --version
test -f /Users/mlp/LLMTier-dev/state.sqlite3
test -d /Users/mlp/LLMTier-dev/secrets
lsof -nP -iTCP:8181 -sTCP:LISTEN
```

最后一条命令无输出表示端口未监听，可以继续。若已有监听进程，先识别进程，不要再次启动第二个实例。
不要打印、复制或修改`secrets/`中的内容。

现有SQLite已经完成bootstrap，是运行配置的唯一authority。正常重启不得传入`--settings`，也不得用
`settings.json`覆盖数据库；`--settings`只用于全新空数据库的首次初始化。

## 3. 手工启动

在m5air终端执行：

```bash
cd /Users/mlp/LLMTier-dev
umask 077
nohup env \
  PYTHONPATH=/Users/mlp/LLMTier-dev/src \
  LLMTIER_TRUSTED_LAN_MODE=1 \
  /usr/local/bin/python3 -m llmtier_v03 \
  --host 0.0.0.0 \
  --port 8181 \
  --database /Users/mlp/LLMTier-dev/state.sqlite3 \
  >> /Users/mlp/LLMTier-dev/llmtier.log 2>&1 &
echo $! > /Users/mlp/LLMTier-dev/llmtier.pid
```

`nohup`只保证SSH断开后进程继续运行，不提供开机自启。m5air重启后必须重新执行本节。

## 4. 启动结果检查

先确认PID、进程命令和端口：

```bash
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,ppid=,etime=,command=
lsof -nP -iTCP:8181 -sTCP:LISTEN
tail -n 40 /Users/mlp/LLMTier-dev/llmtier.log
```

进程命令必须包含`python3 -m llmtier_v03`，监听必须是`*:8181`或等效的所有接口表示。然后执行无副作用检查：

```bash
curl -sS -i http://127.0.0.1:8181/healthz
curl -sS -i http://127.0.0.1:8181/readyz
curl -sS -o /dev/null -w 'UI HTTP %{http_code}\n' http://127.0.0.1:8181/
```

`healthz`返回HTTP 200只证明服务进程可响应；`readyz`还反映Tier可用性，可能返回degraded或503，不能用
health成功替代ready成功。随后从另一台局域网机器打开：

```text
http://192.168.1.9:8181/
```

不要在启动检查中自动执行backend probe或真实模型请求；它们可能产生费用并改变provider状态。

## 5. 查看状态和日志

```bash
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,etime=,%cpu=,%mem=,command=
tail -f /Users/mlp/LLMTier-dev/llmtier.log
```

日志不得包含API Key、Authorization、Prompt、模型输出或Embedding内容。发现此类内容时停止复制日志并按安全问题处理。

## 6. 手工停止

读取PID后先核对命令，确认它确实是LLMTier进程：

```bash
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,command=
```

确认无误后发送正常终止信号并等待最多60秒：

```bash
kill -TERM "$pid"
i=0
while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 60 ]; do
  sleep 1
  i=$((i + 1))
done
if kill -0 "$pid" 2>/dev/null; then
  echo "LLMTier did not stop within 60 seconds; investigate before forcing termination"
else
  rm -f /Users/mlp/LLMTier-dev/llmtier.pid
  echo "LLMTier stopped"
fi
```

不要在未保全日志和确认SQLite状态前直接使用`kill -9`。端口释放后再启动新实例。

## 7. 手工重启

重启不是一个独立机制：严格依次执行第6节停止、第2节检查、第3节启动和第4节验证。不得在旧进程仍监听
8181时启动第二个进程，也不得通过换端口保留两个并行实例。

## 8. 常见故障

| 现象 | 检查和处理 |
|---|---|
| `Connection refused` | 服务未启动或已随机器重启停止；检查PID、日志和8181监听，再按第3节启动 |
| PID文件存在但进程不存在 | 这是stale PID；确认8181无监听后，启动命令会写入新PID |
| `Address already in use` | 使用`lsof`识别现有监听者；不要启动第二实例或随意换端口 |
| Python语法/导入错误 | 确认使用`/usr/local/bin/python3`且`PYTHONPATH`指向项目`src` |
| `healthz`成功但`readyz`失败 | 服务活着但Tier不可用；检查脱敏日志、Provider网络和配置，不盲目重启或probe |
| Provider Secret不可用 | 检查Secret文件存在性和owner-only权限；禁止输出文件内容 |
| SQLite locked/corrupt | 停止服务并保全数据库、`-wal`和`-shm`文件；不要直接编辑或删除状态文件 |
| 局域网无法访问 | 核对监听为`0.0.0.0:8181`、m5air地址仍是`192.168.1.9`且本机防火墙允许8181 |

## 9. 安全边界

`LLMTIER_TRUSTED_LAN_MODE=1`允许loopback、RFC1918和ULA来源在没有Bearer时使用共享operator/data权限。
因此同一可信局域网内的主机可以调用模型和修改配置。此模式不得用于公网、访客网络或不可信LAN；它不是
production TLS/SSO方案。若网络边界发生变化，先停止服务并重新评审认证方式，不要仅修改监听地址继续运行。

本文不授权真实provider probe、模型调用、凭据变更、数据库恢复或迁移；这些操作另行确认。
