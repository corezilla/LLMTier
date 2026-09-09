from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backends import list_backends
from client import DEFAULT_TRACE_PATH, DEFAULT_TRACE_STATE_PATH, TierClient
from quota_manager import _default_quota_state_dir
from tier_config import TierConfig


class IndependentRuntimeBoundaryTests(unittest.TestCase):
    def test_default_config_is_project_local(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = TierConfig()

        expected = Path(__file__).resolve().parents[1] / "config" / "settings.json"
        self.assertEqual(config._settings_path, expected)

    def test_explicit_llmtier_config_is_the_only_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            config_path = Path(temporary_dir) / "settings.json"
            config_path.write_text("{}", encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "LLMTIER_CONFIG": str(config_path),
                    "SLINKY_TIER_CONFIG": "/must/not/be/read.json",
                },
                clear=True,
            ):
                config = TierConfig()

        self.assertEqual(config._settings_path, config_path.resolve())

    def test_default_state_is_project_local(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            state_dir = _default_quota_state_dir()

        self.assertEqual(state_dir, Path(__file__).resolve().parents[1] / "state" / "quota")

    def test_client_trace_defaults_use_project_state_not_legacy_workspace(self) -> None:
        expected_state_dir = Path(__file__).resolve().parents[1] / "state"
        self.assertEqual(Path(DEFAULT_TRACE_STATE_PATH), expected_state_dir / "tier_debug.json")
        self.assertEqual(Path(DEFAULT_TRACE_PATH), expected_state_dir / "tier_trace.jsonl")
        self.assertNotIn("workspaces", DEFAULT_TRACE_STATE_PATH)
        self.assertNotIn("workspaces", DEFAULT_TRACE_PATH)

    def test_client_trace_follows_llmtier_state_dir_without_new_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            with patch.dict(os.environ, {"LLMTIER_STATE_DIR": temporary_dir}, clear=True):
                client = TierClient()
        self.assertEqual(Path(client._trace_state_path), Path(temporary_dir).resolve() / "tier_debug.json")

    def test_authoritative_registry_excludes_agent_and_cli_runners(self) -> None:
        self.assertEqual(
            set(list_backends()),
            {
                "debug",
                "deepseek",
                "llama_cpp",
                "local",
                "minimax",
                "omlx",
                "opencode_go",
                "volc",
                "xfyun",
            },
        )


if __name__ == "__main__":
    unittest.main()
