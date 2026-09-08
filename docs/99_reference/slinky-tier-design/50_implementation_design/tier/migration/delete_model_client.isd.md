# `src/utils/model_client.py` Deletion ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Approved Deletion

target_file: `src/utils/model_client.py`
target_state: `delete`

上游：`docs/40_module_design/tier/tier_client_module.md`、`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。
source_file: `src/utils/model_client.py`

TierClient是唯一model调用入口。删除`ModelRequest`、`ModelResponse`、`ModelClient`、`MockModelClient`、`ProxyModelClient`和`build_model_client_from_config`；测试替身改为Tier public boundary注入，不保留direct provider、HTTP fallback或compat wrapper。门禁包括全仓import清零、Service不可达时无Backend调用/本地stats，以及Role调用真实IPC Contract Test。
