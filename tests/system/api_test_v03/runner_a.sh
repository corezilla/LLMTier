#!/usr/bin/env bash
# A 类 runner：只跑标记为 api_a 的 m5air 现有 state case（读 / 无状态写）
# 退出码：0 = 全部 PASS；非零 = 有 FAIL/BLOCKED
set -euo pipefail

cd "$(dirname "$0")/../../.."
export PYTHONPATH=src
exec python3 -m pytest tests/system/api_test_v03/ -m api_a -v \
  --tb=short \
  -o "addopts=" \
  "$@"
