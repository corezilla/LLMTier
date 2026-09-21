"""A 类 case 共用常量。

不在 conftest.py 里——pytest 不会通过 sys.path 提供 conftest 模块（设计上如此），
所以 from conftest import 在测试文件里直接 import 会失败。
"""
from __future__ import annotations

FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")

M5AIR_BASE = "http://192.168.1.9:8181"
DATA_TOKEN = "dev-data"
ADMIN_TOKEN = "dev-admin"
OMLX_TOKEN = "9832"
