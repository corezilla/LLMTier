#!/usr/bin/env bash
# B 类 runner：跑临时 SQLite 实例上的 15 个 CRUD case
# 退出码：0 = 全部 PASS；非零 = 有 FAIL
set -euo pipefail

cd "$(dirname "$0")/../../.."
export PYTHONPATH=src

B_CLASS_FILES=(
    tests/system/api_test_v03/at_adm_prov_02.py
    tests/system/api_test_v03/at_adm_prov_05.py
    tests/system/api_test_v03/at_adm_prov_06.py
    tests/system/api_test_v03/at_adm_prov_07.py
    tests/system/api_test_v03/at_adm_prov_08.py
    tests/system/api_test_v03/at_adm_prov_09.py
    tests/system/api_test_v03/at_adm_depl_02.py
    tests/system/api_test_v03/at_adm_depl_04.py
    tests/system/api_test_v03/at_adm_depl_05.py
    tests/system/api_test_v03/at_adm_sl_02.py
    tests/system/api_test_v03/at_adm_sl_02b.py
    tests/system/api_test_v03/at_adm_sl_04.py
    tests/system/api_test_v03/at_adm_sl_04b.py
    tests/system/api_test_v03/at_adm_sl_05.py
    tests/system/api_test_v03/at_obs_03.py
)

exec python3 -m pytest "${B_CLASS_FILES[@]}" -v --tb=short -o "addopts=" "$@"
