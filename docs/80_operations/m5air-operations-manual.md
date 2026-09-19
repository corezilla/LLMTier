<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier m5air Operations Manual

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-m5air-operations-manual` |
| Document Version | `0.2.0-draft.2` |
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
| Canonical Path | `docs/80_operations/m5air-operations-manual.md` |
| Supersedes | `llmtier-m5air-manual-start-runbook@0.1.0-draft.1` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目的和适用范围

本文是LLMTier在测试机`m5air`上的完整操作手册，覆盖环境确认、启动停止、Web UI、Provider与Tier管理、
状态和并发、Usage/Audit/Logs、Secret、备份恢复、版本更新、故障处理和安全边界。

本手册描述当前已经存在的V0.3单节点实现，不把未来设计写成已交付能力。以下约束始终成立：

- 不配置`launchd`、systemd、登录项或任何开机自启；m5air重启后LLMTier保持停止；
- 不部署反向代理，服务直接监听局域网`0.0.0.0:8181`；
- 当前是可信局域网测试部署，不是公网或production部署；
- 当前只有一个LLMTier进程和一个SQLite运行数据库，不支持多实例、HA或共享SQLite；
- Provider probe、真实模型请求和Embedding请求可能访问外部服务，必须由operator明确执行；
- `overall.runtime_activation=false`；当前部署用于调试和验证，不代表production activation。

## 2. 环境与目录

| 项目 | 当前值 |
|---|---|
| SSH入口 | `ssh m5air` |
| SSH用户 | `mlp` |
| 当前局域网地址 | `192.168.1.9`；使用前应重新核对 |
| 项目目录 | `/Users/mlp/LLMTier-dev` |
| Python | `/usr/local/bin/python3`，当前为Python 3.14.3 |
| 源码入口 | `/Users/mlp/LLMTier-dev/src` |
| 运行数据库 | `/Users/mlp/LLMTier-dev/state.sqlite3` |
| Secret目录 | `/Users/mlp/LLMTier-dev/secrets` |
| 进程日志 | `/Users/mlp/LLMTier-dev/llmtier.log` |
| PID文件 | `/Users/mlp/LLMTier-dev/llmtier.pid` |
| 监听地址 | `0.0.0.0:8181` |
| Web UI | `http://192.168.1.9:8181/` |

不要使用`/usr/bin/python3`：当前版本为Python 3.9.6，低于项目要求的Python 3.11。

`/Users/mlp/LLMTier-dev`当前是部署目录，不是Git工作树。部署版本必须通过开发仓库的commit SHA和部署清单记录，
不能在m5air上用`git status`或`git pull`推断、更新版本。

## 3. 系统对象与责任

### 3.1 Provider

Provider表示一个云服务商账号或本地OpenAI-compatible服务，包含名称、类型、API Root、Secret引用、启用状态、账号用量源、账号并发/最小间隔/RPM和版本。
Provider本身不等于模型，也不定义Tier。

### 3.2 Deployment（页面上的Tier Member或Model）

Deployment把一个Provider与实际`backend_model`绑定，并声明Responses或Embeddings能力。一个Provider可以有多个
Deployment。页面上的模型状态和并发属于Deployment，不属于Provider账号余额。

### 3.3 Tier（Service Level）

当前固定Tier为：`Senior`、`Junior`、`Worker`、`Associate`、`Engineer`、`Executor`和`Embedding-v1`。
Tier下面按顺序挂载一个或多个Deployment。Tier不能删除；可以编辑成员和成员顺序对应的路由候选集合。

普通Tier只接受支持Responses的成员；`Embedding-v1`只接受冻结的BGE-M3向量空间：1024维、batch上限32、
单输入token上限8192。能力不兼容时保存会失败，不能通过页面强行绕过。

### 3.4 路由和并发

请求只在指定Tier内选择已启用Provider、已启用Deployment且健康状态为`healthy`的成员。选择策略先比较当前
运行数，再按Tier成员顺序选择。当前每个Deployment的默认最大并发为1；每个Tier队列最多32个请求，排队等待
最长30秒。路由同时遵守Deployment最大并发及Provider账号最大并发、最小请求间隔和RPM；达到限制返回429，全部后端不可用返回503。

暂停某个模型只阻止后续请求路由到该Deployment；已经运行的请求继续执行。Tier状态和各成员状态相互独立显示。

## 4. 安全模式与API Key

当前m5air使用：

```text
LLMTIER_TRUSTED_LAN_MODE=1
```

来自loopback、RFC1918或IPv6 ULA地址的无Authorization请求会获得共享consumer/operator权限。因此，能访问
该可信局域网的主机可以调用模型并修改配置。此模式没有用户级身份隔离，不得暴露到公网、访客Wi-Fi或不可信LAN。

Provider API Key不直接写入Web UI、SQLite、日志或Git。Provider只保存以下两种引用之一：

- `file:/Users/mlp/LLMTier-dev/secrets/<provider>.txt`
- `env:PROVIDER_API_KEY`

推荐m5air使用`file:`。Secret文件只包含Key本身，不加引号，不在末尾附注释。创建后设置权限：

```bash
chmod 700 /Users/mlp/LLMTier-dev/secrets
chmod 600 /Users/mlp/LLMTier-dev/secrets/*
```

Web UI编辑已有Provider时，API Key Reference留空表示保留当前引用；输入新引用会替换旧引用。页面只显示
`Configured`或`None`，永不回显Key。不要把Key粘贴到API Key Reference字段。

Provider账号用量凭据规则：

- MiniMax Token Plan直接复用API Key或单独的API Key reference，调用`https://www.minimaxi.com/v1/token_plan/remains`；不需要、也不应配置console cookie；
- 火山Coding Plan用OpenAPI AK与SK签名读取，分别配置`usage_access_key_ref`和`usage_secret_key_ref`；推理API Key不能替代它们；
- 本地Provider显示Unlimited；未配置用量源时显示Not refreshed/Unavailable，不填0；
- 页面刷新按钮会访问外部Provider，必须由operator显式确认；普通页面刷新只读取最后持久快照。

## 5. 首次部署和空库初始化

本节只用于全新部署目录或全新空数据库。现有m5air数据库已经初始化，正常启动必须跳过本节。

1. 准备Python 3.11+、源码目录、owner-only Secret目录和一次性bootstrap JSON；
2. bootstrap JSON必须完整包含`providers`、`deployments`、`service_levels`；
3. 先验证所有`file:`或`env:` Secret引用存在；
4. 启动空库时唯一一次传入`--settings`；
5. 成功后SQLite保存bootstrap摘要并成为唯一配置authority。

示例形状：

```bash
PYTHONPATH=/path/to/src \
  /usr/local/bin/python3 -m llmtier_v03 \
  --host 127.0.0.1 \
  --port 8181 \
  --database /path/to/new-state.sqlite3 \
  --settings /path/to/bootstrap-settings.json
```

初始化后的正常启动不得再次传`--settings`，也不得用`settings.json`覆盖SQLite。

## 6. 每次启动前检查

登录并进入部署目录：

```bash
ssh m5air
cd /Users/mlp/LLMTier-dev
```

核对当前地址、解释器、源码、数据库、Secret目录和端口：

```bash
ipconfig getifaddr en0
/usr/local/bin/python3 --version
PYTHONPATH=/Users/mlp/LLMTier-dev/src /usr/local/bin/python3 -m llmtier_v03 --help
test -f /Users/mlp/LLMTier-dev/state.sqlite3
test -d /Users/mlp/LLMTier-dev/secrets
/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN
```

最后一条无输出表示端口未监听。若已有监听者，先识别进程，不要启动第二实例。不要读取或打印Secret内容。

建议在服务停止时检查SQLite和权限：

```bash
/usr/bin/sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 'PRAGMA integrity_check;'
stat -f '%Sp %Su:%Sg %N' \
  /Users/mlp/LLMTier-dev \
  /Users/mlp/LLMTier-dev/state.sqlite3 \
  /Users/mlp/LLMTier-dev/secrets
```

`integrity_check`必须输出`ok`。部署目录和Secret目录应为owner-only；数据库、WAL、SHM、日志、PID及Secret文件
应限制为owner读写。需要修正时：

```bash
chmod 700 /Users/mlp/LLMTier-dev /Users/mlp/LLMTier-dev/secrets
chmod 600 /Users/mlp/LLMTier-dev/state.sqlite3* \
  /Users/mlp/LLMTier-dev/llmtier.log \
  /Users/mlp/LLMTier-dev/secrets/*
```

## 7. 手工启动

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

`nohup`只保证SSH断开后进程继续运行，不提供开机自启。机器重启后必须重新执行本节。

## 8. 启动验证

### 8.1 进程与端口

```bash
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,ppid=,etime=,command=
/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN
tail -n 40 /Users/mlp/LLMTier-dev/llmtier.log
```

命令必须包含`python3 -m llmtier_v03`，监听必须显示`*:8181`或等效的所有接口形式。

### 8.2 无副作用检查

```bash
curl -sS -i http://127.0.0.1:8181/healthz
curl -sS -i http://127.0.0.1:8181/readyz
curl -sS -o /dev/null -w 'UI HTTP %{http_code}\n' http://127.0.0.1:8181/
```

- `/healthz` HTTP 200只证明进程和HTTP服务可响应；
- `/readyz`只有所有固定Tier都available时才返回ready/200；degraded或not_ready返回503；
- Web UI HTTP 200只证明静态页面可加载，不证明Provider可调用。

然后从另一台局域网机器打开`http://192.168.1.9:8181/`。如果`ipconfig`显示地址变化，应使用新地址并更新
运维记录，不要继续假设`192.168.1.9`不变。

不要把Provider probe或真实模型请求放入自动启动检查。

## 9. Web UI操作

Web UI为英文界面，入口是根路径`/`；`/ui/`只是同一页面的兼容静态路径，不作为用户书签。

### 9.1 Home

顶部显示Gateway总状态、可用Tier数量、可用模型数量、当前运行数/总并发、版本和页面更新时间。Home主体使用无背景
树形结构：Tier显示自己的状态、总并发和Tier Usage；Tier下成员分别显示自己的状态、并发、Provider和类型。

状态图标不显示长文字，鼠标悬停或键盘聚焦后显示含义：

| 状态 | 含义 |
|---|---|
| Ready | Tier至少有一个可路由的健康成员 |
| Idle | 成员健康，当前没有请求运行 |
| Running | 成员当前确有请求运行；不是服务启动状态 |
| Paused | 用户已暂停该Deployment，新请求不再进入 |
| Disabled | Provider被禁用 |
| Probing | 正在检查后端 |
| Attention/Degraded | 仍有部分能力但需要关注 |
| Unreachable | 后端探测失败或不可达 |
| Empty | Tier没有成员 |
| Unknown | 尚无可信健康事实 |

成员右侧操作：

- Pause/Resume：切换Deployment的`enabled`；Running时暂停会要求确认，已有请求继续；
- Probe：调用Provider的`GET /models`并更新成员健康状态；需要确认，会产生外部网络访问；
- Edit Tier：打开Tier抽屉，添加、修改或移除成员。

Tier不能删除。移除成员只解除Tier关联，不删除Deployment。不能移除Tier的最后一个成员；能力不兼容的成员不能保存。

### 9.2 Providers

Providers页面管理Cloud Provider和Local Backend。字段包括Provider Name、Type、API Root、API Key Reference、
Usage Source、账号最大并发、最小请求间隔、RPM和Enabled。添加Tier成员前必须先有Provider。

- Edit：修改Provider名称、类型、API Root、Secret引用或启用状态；
- Delete：只有未被任何Deployment引用时才能删除，否则返回resource in use；
- Status：由Provider启用状态及其Deployment状态汇总；
- Account Usage：普通显示最后持久快照；点击刷新并确认后，MiniMax用API Key读取Token Plan，火山用AK/SK读取Coding Plan；
- Calls/Tokens：请求真正选定后记录Provider/Deployment绑定，并聚合该Provider的最高Usage版本；unknown不填0；
- Running/Max：显示该Provider账号当前运行数和配置的账号最大并发；Deployment自身上限仍独立生效。

配置保存成功不代表Provider健康；保存后由operator决定是否执行Probe。

### 9.3 Usage & Audit

`Token Usage`默认读取最近7天的统一token事实，显示Request、Tier model、Endpoint、Input、Output、Total和
measurement status。缺失事实显示Unknown，绝不填0。当前页面展示第一页，最多100条；响应Usage和查询到的同一
request事实不能重复相加。

`Audit Log`记录管理变更的actor、action、target、result和时间。它记录管理动作，不记录prompt或模型输出。

### 9.4 Logs

Logs页面默认读取最近7天脱敏运行日志，可以按level和module过滤。日志包含Time、Level、Module、Event、Summary和
Request ID。Request ID用于关联一次HTTP请求。日志不得出现API Key、Authorization、prompt、模型输出、reasoning、
向量或原始header。

## 10. 日常巡检

每日或每次调试前建议执行：

```bash
curl -sS http://127.0.0.1:8181/healthz
curl -sS http://127.0.0.1:8181/readyz
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,etime=,%cpu=,%mem=,command=
/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN
tail -n 100 /Users/mlp/LLMTier-dev/llmtier.log
```

同时在Home检查：Gateway状态、Tier可用数、模型可用数、Running/Max和异常图标；在Usage & Audit检查Unknown突增、
管理失败；在Logs按error/warning筛选。不要因`healthz`成功就忽略`readyz`失败。

## 11. Provider和Tier变更流程

1. 明确变更目标和影响的Tier；
2. 先创建Secret文件或环境变量，只保存引用；
3. 在Providers添加或修改Provider；
4. 在Home打开目标Tier的Edit；
5. 从已有Provider选择，填写Deployment Name和Backend Model ID；
6. 保存后检查Tier能力校验结果；
7. 经operator确认后执行Probe；
8. 检查成员和Tier状态、Audit、Logs；
9. 需要真实验证时，再单独批准最小模型/Embedding请求。

修改和删除使用版本/ETag并发保护。如果页面提示版本冲突，刷新后重新检查当前值，不要盲目重复提交。Provider、
Deployment或Tier有关联时，先解除引用再删除；Tier本身固定且不可删除。

## 12. 手工停止与重启

先读取PID并核对命令：

```bash
pid="$(cat /Users/mlp/LLMTier-dev/llmtier.pid)"
ps -p "$pid" -o pid=,command=
```

确认是LLMTier后发送正常终止信号并等待最多60秒：

```bash
kill -TERM "$pid"
i=0
while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 60 ]; do
  sleep 1
  i=$((i + 1))
done
if kill -0 "$pid" 2>/dev/null; then
  echo 'LLMTier did not stop within 60 seconds; investigate before forcing termination'
else
  rm -f /Users/mlp/LLMTier-dev/llmtier.pid
  echo 'LLMTier stopped'
fi
```

不要在未保全日志和SQLite状态前直接`kill -9`。重启严格依次执行：停止→启动前检查→启动→启动验证。旧进程仍监听
8181时不得启动第二实例，也不得换端口保留并行实例。

## 13. 日志与磁盘管理

`llmtier.log`是stdout/stderr追加日志；脱敏运行事件同时保存在SQLite中并通过Logs页面读取。当前没有自动日志轮转。
定期检查：

```bash
du -h /Users/mlp/LLMTier-dev/llmtier.log
du -h /Users/mlp/LLMTier-dev/state.sqlite3*
df -h /Users/mlp/LLMTier-dev
```

需要轮转时先正常停止服务，再将日志改名并以600权限创建新文件，随后启动并验证。禁止在服务运行时删除SQLite、
`-wal`或`-shm`文件。

## 14. 备份与恢复

当前实现没有内置定时备份、加密备份、自动保留或restore命令。以下是m5air测试环境的人工冷备份流程，不等于
production备份方案。Secret必须和数据库分开保管，不能把Key写进备份清单。

### 14.1 创建冷备份

1. 按第12节正常停止服务；
2. 确认8181已释放；
3. 执行checkpoint和完整性检查；
4. 复制数据库并生成摘要。

```bash
cd /Users/mlp/LLMTier-dev
/usr/bin/sqlite3 state.sqlite3 'PRAGMA wal_checkpoint(FULL); PRAGMA integrity_check;'
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 -p "backups/$stamp"
cp -p state.sqlite3 "backups/$stamp/state.sqlite3"
shasum -a 256 "backups/$stamp/state.sqlite3" > "backups/$stamp/SHA256SUMS"
chmod 600 "backups/$stamp/state.sqlite3" "backups/$stamp/SHA256SUMS"
```

输出必须包含`ok`。备份目录当前仍在同一磁盘，只能防止误操作，不能防止主机或磁盘故障。复制到异机或加密介质
属于另行批准的运维操作。

### 14.2 恢复

恢复会改变运行状态，必须明确选择备份并保留故障数据库：

```bash
cd /Users/mlp/LLMTier-dev
test ! -e llmtier.pid
shasum -a 256 -c backups/<timestamp>/SHA256SUMS
failed_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mv state.sqlite3 "state.sqlite3.failed.$failed_stamp"
test ! -e state.sqlite3-wal || mv state.sqlite3-wal "state.sqlite3-wal.failed.$failed_stamp"
test ! -e state.sqlite3-shm || mv state.sqlite3-shm "state.sqlite3-shm.failed.$failed_stamp"
cp -p backups/<timestamp>/state.sqlite3 state.sqlite3
chmod 600 state.sqlite3
/usr/bin/sqlite3 state.sqlite3 'PRAGMA integrity_check;'
```

只有摘要和`integrity_check`通过后才能启动。恢复后先检查Registry、Usage和Audit，再由operator决定是否Probe。
环境恢复不等于上游Piko任务成功，也不会恢复中断的模型请求。

## 15. 版本更新与回滚

更新前必须在开发仓库完成测试、提交和push，并记录commit SHA。m5air部署目录不是Git仓库，因此更新必须使用受控文件同步，
并排除以下运行数据：

```text
state.sqlite3*
secrets/
llmtier.log
llmtier.pid
backups/
```

标准顺序：

1. 记录当前部署commit/清单和数据库摘要；
2. 正常停止服务并创建冷备份；
3. 在开发机先做同步dry-run，确认不会覆盖运行数据；
4. 同步已提交的源码、静态UI和必要文档；
5. 在m5air运行完整单元测试或批准的部署验证；
6. 检查数据库schema兼容性；
7. 启动并执行health/readiness/UI检查；
8. 需要外部调用时另行批准Probe和最小smoke；
9. 记录部署版本、时间、验证结果和operator。

回滚必须同时满足旧代码与当前数据库schema兼容。不能只覆盖源码后盲目启动；如需恢复数据库，按第14节恢复同一版本对应的备份。
当前没有自动migration rollback或蓝绿部署。

## 16. 故障处理

| 现象 | 检查与处理 |
|---|---|
| 浏览器无法打开 | 核对进程、`*:8181`监听、m5air当前IP和macOS防火墙 |
| `Connection refused` | 服务未启动或已随重启停止；按第6至8节处理 |
| PID文件存在但进程不存在 | 这是stale PID；确认8181无监听后重新启动并覆盖PID |
| `Address already in use` | 用`lsof`识别监听者；不启动第二实例、不换端口绕过 |
| Python导入错误 | 使用`/usr/local/bin/python3`并设置正确`PYTHONPATH` |
| `healthz`成功、`readyz`失败 | 服务存活但一个或多个Tier不可用；查Home、Provider、Logs和Secret引用 |
| Home显示Unknown | 尚未Probe或没有可信健康事实；确认后执行一次Probe |
| Home显示Paused | Deployment被用户暂停；确认原因后Resume，不以重启替代 |
| Home显示Running | 当前确有请求占用该模型；等待完成或检查调用方，不把它解释为服务运行状态 |
| Probe失败 | 检查API Root、Secret引用、DNS/网络、Provider `/models`兼容性；不要输出Key |
| 401/403 | 检查可信LAN来源或Bearer配置，不通过关闭认证解决 |
| 404 model not found | Tier不存在、没有启用成员，或请求模型ID不精确 |
| 429 | Tier队列满或等待超时；减少并发、等待后重试，不跨Tier自动降级 |
| 502 | Provider返回错误或响应不符合标准契约；按Request ID查Logs |
| 503 | bootstrap、认证、Provider、Usage store或Tier可用性问题；按错误码定位 |
| Provider无法删除 | 仍被Deployment引用；先在Tier移除并处理Deployment引用 |
| SQLite locked/corrupt | 停止服务，保全数据库/WAL/SHM；不要直接编辑或删除；按备份恢复流程处理 |
| 磁盘空间不足 | 停止写入压力，检查日志、数据库和备份；不直接删除活动数据库文件 |
| 周期性 503 / Empty reply / "Too many open files" 反复出现 | 疑似 FD 泄漏；先 `lsof -p $(cat /Users/mlp/LLMTier-dev/llmtier.pid) | wc -l` 与 `ulimit -n`（默认 256）对比，超过 ~200 重启清空；`llmtier.log` 反复出现 `OSError: [Errno 24]` 或 `sqlite3.OperationalError: unable to open database file` 是征兆；定位 `src/llmtier_v03/app.py` 的 `_static` 与 `_run`；属 §17 长期能力限制项，单独 follow-up |
| 本地 Provider（provider_local）调用返回 401 | 当前 OMLX 进程需 `Authorization: Bearer`，但 `provider_local.has_secret=false` 时 `src/llmtier_v03/providers/openai.py` 不发送 Authorization 头；二选一对齐：让 OMLX 接受匿名访问 / 为 `provider_local` 配 `file:` 或 `env:` 形式的 secret_ref |

故障证据至少保留：发生时间、部署版本、Request ID、health/readiness结果、脱敏日志、受影响Tier/Provider和已执行动作。
任何日志中若出现Credential、Prompt、模型输出或Embedding内容，停止传播并按安全事件处理。

## 17. 当前能力限制

以下能力当前不存在或未形成可执行production机制：

- 开机自启和进程监督；
- TLS、SSO和用户级权限隔离；
- 自动日志轮转、自动告警和on-call系统；
- Provider账号余额或配额查询；
- Provider维度的精确token归因；
- 自动加密备份、异机备份、保留策略和定期restore rehearsal；
- HA、多实例、共享数据库和自动故障转移；
- 中断模型调用的结果恢复、Invocation查询或exactly-once；
- 自动跨Tier fallback；
- production runtime activation。

不得通过新增临时脚本、第二数据库、平行配置、旧接口或Provider直连来绕过这些限制。确有新需求时先修改设计并评审。

## 18. 操作清单

### 启动

- [ ] 确认m5air地址、Python、数据库、Secret目录和权限
- [ ] 确认8181无监听者
- [ ] 确认SQLite integrity为`ok`
- [ ] 手工启动单一进程
- [ ] 核对PID、监听、healthz、readyz和根页面
- [ ] 不自动Probe、不自动发真实模型请求

### 配置变更

- [ ] 只保存Secret引用，不保存Key值
- [ ] 明确受影响Provider、Deployment和Tier
- [ ] 保存后检查Audit和Logs
- [ ] 由operator确认后Probe
- [ ] 需要真实调用时单独确认费用和数据边界

### 停止或更新

- [ ] 核对PID确属LLMTier
- [ ] 正常TERM并等待最多60秒
- [ ] 确认8181释放
- [ ] 更新前完成冷备份和摘要
- [ ] 排除state、secrets、logs、PID和backups后再同步代码
- [ ] 更新后重新执行完整启动验证
