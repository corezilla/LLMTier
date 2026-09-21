#!/usr/bin/env bash
# A 类 runner：跑 m5air 现有 state 上的 53 个读 / 无状态写 case
# 退出码：0 = 全部 PASS；非零 = 有 FAIL/BLOCKED
set -euo pipefail

cd "$(dirname "$0")/../../.."
export PYTHONPATH=src
exec python3 -m pytest tests/system/api_test_v03/ -v \
  --tb=short \
  -o "addopts=" \
  "$@"
