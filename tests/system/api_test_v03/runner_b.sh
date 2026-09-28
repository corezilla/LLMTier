#!/usr/bin/env bash
# B 类 runner：只跑标记为 api_b 的临时 SQLite 实例 case（CRUD / 注入）
# 文件集合由 pytest marker 生成，不再手工维护列表。
# 退出码：0 = 全部 PASS；非零 = 有 FAIL
set -euo pipefail

cd "$(dirname "$0")/../../.."
export PYTHONPATH=src

exec python3 -m pytest tests/system/api_test_v03/ -m api_b -v \
  --tb=short \
  -o "addopts=" \
  "$@"
