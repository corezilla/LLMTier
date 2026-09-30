"""Case ID: UT-TOOL-002

Unit tests for the environment tooling (system test plan §3/§6):

  tools/check_env.py — A-class readiness aggregation + exit codes, B-class
      LAN detection.
  tools/reset_env.py — reset-ladder ordering, dry-run, backup, kill parsing.
  tools/deploy.py    — artifact pin + rsync/ssh/rollback command construction.

Deterministic: no network, no ssh, no subprocess execution against a real
host. HTTP and subprocess calls are mocked/monkeypatched.

Dependencies: none (stdlib only; mock via unittest.mock).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import check_env  # noqa: E402
import deploy  # noqa: E402
import reset_env  # noqa: E402


# ---------------------------------------------------------------------------
# check_env.py
# ---------------------------------------------------------------------------

class CheckEnvConfigTests(unittest.TestCase):
    def test_build_config_maps_overrides(self):
        args = argparse.Namespace(
            base_url="http://10.0.0.5:8181", admin_token="tok-a", data_token="tok-d",
            m5air_omlx="http://10.0.0.5:9000/v1", m5mac_omlx="http://10.0.0.6:9000/v1",
            lan_ip="192.168.1.50", timeout=3.0, python="/py", repo_root=REPO,
        )
        cfg = check_env.build_config(args)
        self.assertEqual("http://10.0.0.5:8181", cfg.base_url)
        self.assertEqual("tok-a", cfg.admin_token)
        self.assertEqual("192.168.1.50", cfg.lan_ip_override)
        self.assertEqual(REPO / "src", cfg.src_root)
        self.assertEqual(REPO / "tests" / "fixtures" / "v03_fake_provider.py", cfg.fake_provider_script)


class CheckEnvAChecksTests(unittest.TestCase):
    def setUp(self):
        self.cfg = check_env.EnvConfig()

    def _patch_get(self, mapping):
        def fake_get(url, headers=None, timeout=5.0):
            return mapping.get(url, (0, "unmapped"))
        patcher = mock.patch.object(check_env, "http_get", side_effect=fake_get)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_healthz_pass_and_fail(self):
        self._patch_get({f"{self.cfg.base_url}/healthz": (200, '{"status":"ok","version":"0.3"}')})
        self.assertTrue(check_env.check_healthz(self.cfg).ok)
        self._patch_get({f"{self.cfg.base_url}/healthz": (200, '{"status":"down","version":"0.3"}')})
        self.assertFalse(check_env.check_healthz(self.cfg).ok)
        self._patch_get({f"{self.cfg.base_url}/healthz": (200, '{"status":"ok"}')})
        self.assertFalse(check_env.check_healthz(self.cfg).ok)

    def test_readyz_requires_all_seven_fixed_tiers(self):
        # §2.1.2 oracle (matches api_test_v03 conftest `_check_m5air_readyz` and
        # tools/check_env.check_readyz): all 7 fixed tiers must be present.
        # Extra (non-fixed) tiers are informational, not a readiness failure.
        good = {"models": [{"id": t} for t in check_env.FIXED_TIERS]}
        self._patch_get({f"{self.cfg.base_url}/readyz": (200, __import__("json").dumps(good))})
        self.assertTrue(check_env.check_readyz(self.cfg).ok)
        short = {"models": [{"id": t} for t in check_env.FIXED_TIERS[:-1]]}
        self._patch_get({f"{self.cfg.base_url}/readyz": (200, __import__("json").dumps(short))})
        self.assertFalse(check_env.check_readyz(self.cfg).ok)
        extra = {"models": [{"id": t} for t in check_env.FIXED_TIERS] + [{"id": "Bonus"}]}
        self._patch_get({f"{self.cfg.base_url}/readyz": (200, __import__("json").dumps(extra))})
        self.assertTrue(check_env.check_readyz(self.cfg).ok)

    def test_secret_ref_must_have_secret(self):
        # §2.1.5: `secret_ref` is write-only (ProviderView never returns it), so
        # readiness asserts the observable fact `has_secret=true` only
        # (matches api_test_v03 conftest `_check_provider_omlx_m5mac_secret_ref`).
        url = f"{self.cfg.base_url}/v1/providers/provider_omlx_m5mac"
        self._patch_get({url: (200, '{"has_secret":true}')})
        self.assertTrue(check_env.check_provider_omlx_m5mac_secret_ref(self.cfg).ok)
        self._patch_get({url: (200, '{"has_secret":false}')})
        self.assertFalse(check_env.check_provider_omlx_m5mac_secret_ref(self.cfg).ok)

    def test_required_resources_missing_provider_fails(self):
        mapping = {}
        for pid in check_env.REQUIRED_A_PROVIDERS:
            mapping[f"{self.cfg.base_url}/v1/providers/{pid}"] = (200, "{}")
        for did in check_env.REQUIRED_A_DEPLOYMENTS:
            mapping[f"{self.cfg.base_url}/v1/deployments/{did}"] = (200, "{}")
        self._patch_get(mapping)
        self.assertTrue(check_env.check_required_a_resources(self.cfg).ok)
        mapping[f"{self.cfg.base_url}/v1/providers/processor_local"] = (200, "{}")
        self._patch_get(mapping)
        self.assertTrue(check_env.check_required_a_resources(self.cfg).ok)
        mapping[f"{self.cfg.base_url}/v1/providers/provider_minimax"] = (404, "{}")
        self._patch_get(mapping)
        self.assertFalse(check_env.check_required_a_resources(self.cfg).ok)


class CheckEnvAggregationTests(unittest.TestCase):
    def test_summarize_all_pass(self):
        results = [check_env.CheckResult("A1", "l", True, "d"),
                   check_env.CheckResult("A2", "l", True, "d")]
        report = check_env.summarize(results)
        self.assertTrue(report["all_pass"])
        self.assertEqual(2, report["passed"])
        self.assertEqual(0, report["failed"])

    def test_summarize_any_fail(self):
        results = [check_env.CheckResult("A1", "l", True, "d"),
                   check_env.CheckResult("A2", "l", False, "d")]
        report = check_env.summarize(results)
        self.assertFalse(report["all_pass"])
        self.assertEqual(1, report["failed"])

    def test_main_exit_zero_when_all_pass(self):
        with mock.patch.object(check_env, "run_checks",
                               return_value=[check_env.CheckResult("A1", "l", True, "d")]):
            self.assertEqual(0, check_env.main(["--class", "a"]))
            self.assertEqual(check_env.EXIT_OK, check_env.main(["--class", "a"]))

    def test_main_exit_two_when_any_fail(self):
        with mock.patch.object(check_env, "run_checks",
                               return_value=[check_env.CheckResult("A1", "l", False, "d")]):
            self.assertEqual(2, check_env.main(["--class", "a"]))
            self.assertEqual(check_env.EXIT_FAIL, check_env.main(["--json", "--class", "all"]))

    def test_run_checks_selects_class(self):
        with mock.patch("check_env.A_CHECKS", (lambda cfg: check_env.CheckResult("A1", "a", True, "") ,)), \
             mock.patch("check_env.B_CHECKS", (lambda cfg: check_env.CheckResult("B1", "b", True, "") ,)):
            self.assertEqual(["A1"], [r.id for r in check_env.run_checks("a", check_env.EnvConfig())])
            self.assertEqual(["B1"], [r.id for r in check_env.run_checks("b", check_env.EnvConfig())])
            self.assertEqual(["A1", "B1"], [r.id for r in check_env.run_checks("all", check_env.EnvConfig())])

    def test_run_checks_never_crashes_on_check_exception(self):
        def boom(cfg):
            raise RuntimeError("kaboom")
        with mock.patch("check_env.A_CHECKS", (boom,)), mock.patch("check_env.B_CHECKS", ()):
            results = check_env.run_checks("a", check_env.EnvConfig())
        self.assertEqual(1, len(results))
        self.assertFalse(results[0].ok)

    def test_detect_lan_ip_override_wins(self):
        self.assertEqual("192.168.1.77", check_env.detect_lan_ip("192.168.1.77"))

    def test_detect_lan_ip_env_override(self):
        with mock.patch.dict("os.environ", {"LLMTIER_TEST_LAN_IP": "192.168.1.88"}):
            self.assertEqual("192.168.1.88", check_env.detect_lan_ip())


# ---------------------------------------------------------------------------
# reset_env.py
# ---------------------------------------------------------------------------

class ResetPlanTests(unittest.TestCase):
    def test_plan_order_matches_plan_section(self):
        names = [step.__name__ for step in reset_env.reset_plan()]
        self.assertEqual(
            ["step_backup", "step_restore_or_rebuild", "step_clear_injections",
             "step_reset_ledger", "step_kill_leftovers", "step_recheck"],
            names,
        )

    def test_dry_run_skips_mutation(self):
        cfg = reset_env.ResetConfig(dry_run=True, db_path=Path("/nonexistent/state.sqlite3"))
        result = reset_env.step_backup(cfg)
        self.assertTrue(result.ok)  # nonexistent db -> skip

    def test_guard_requires_yes(self):
        with mock.patch.object(reset_env, "run_reset") as runner:
            rc = reset_env.main([])
            self.assertEqual(reset_env.EXIT_FAIL, rc)
            runner.assert_not_called()
            runner.return_value = []
            rc = reset_env.main(["--yes"])
        self.assertEqual(reset_env.EXIT_OK, rc)
        runner.assert_called_once()

    def test_failed_step_makes_nonzero(self):
        with mock.patch.object(reset_env, "run_reset",
                               return_value=[reset_env.StepResult("x", False, "boom")]):
            self.assertEqual(reset_env.EXIT_FAIL, reset_env.main(["--yes"]))


class ResetBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "state.sqlite3"

    def test_backup_database_copies_content(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db))
        conn.execute("CREATE TABLE t(x INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
        conn.commit()
        conn.close()
        dest = Path(self.tmp.name) / "state.sqlite3.bak"
        reset_env.backup_database(self.db, dest)
        self.assertTrue(dest.exists())
        check = sqlite3.connect(str(dest))
        self.assertEqual(42, check.execute("SELECT x FROM t").fetchone()[0])
        check.close()

    def test_step_backup_makes_backup_when_db_present(self):
        self.db.touch()
        cfg = reset_env.ResetConfig(db_path=self.db)
        result = reset_env.step_backup(cfg)
        self.assertTrue(result.ok)
        backups = list(Path(self.tmp.name).glob("state.sqlite3.bak-*"))
        self.assertEqual(1, len(backups))

    def test_step_backup_no_backup_flag_skips(self):
        cfg = reset_env.ResetConfig(db_path=self.db, no_backup=True)
        result = reset_env.step_backup(cfg)
        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)

    def test_default_backup_path_is_stable_for_fixed_clock(self):
        import datetime as dt
        now = dt.datetime(2026, 9, 30, 12, 34, 56)
        path = reset_env.default_backup_path(self.db, now)
        self.assertEqual("state.sqlite3.bak-20260930-123456", path.name)


class ResetRemoteBackupTests(unittest.TestCase):
    """Remote (m5air) backup — the safety invariant for the live LAN instance."""

    def test_remote_backup_dest_defaults_to_sibling_backups_dir(self):
        cfg = reset_env.ResetConfig(
            remote_db_host="m5air",
            remote_db_path="/Users/mlp/LLMTier-dev/state.sqlite3",
        )
        dest = reset_env.remote_backup_dest(cfg, stamp="20261001-010101")
        self.assertEqual(
            "/Users/mlp/LLMTier-dev/backups/state.sqlite3.bak-20261001-010101", dest
        )

    def test_remote_backup_command_is_ssh_with_online_backup(self):
        cfg = reset_env.ResetConfig(
            remote_db_host="m5air",
            remote_db_path="/Users/mlp/LLMTier-dev/state.sqlite3",
        )
        cmd = reset_env.remote_backup_command(cfg, "/Users/mlp/LLMTier-dev/backups/x.bak")
        self.assertEqual("ssh", cmd[0])
        self.assertEqual("m5air", cmd[1])
        self.assertIn("sqlite3", cmd[2])
        self.assertIn(".backup", cmd[2])

    def test_step_backup_remote_dry_run(self):
        cfg = reset_env.ResetConfig(
            dry_run=True,
            remote_db_host="m5air",
            remote_db_path="/Users/mlp/LLMTier-dev/state.sqlite3",
        )
        result = reset_env.step_backup(cfg)
        self.assertTrue(result.ok)
        self.assertIn("would back up /Users/mlp/LLMTier-dev/state.sqlite3", result.detail)

    def test_step_backup_remote_runs_online_backup(self):
        cfg = reset_env.ResetConfig(
            remote_db_host="m5air",
            remote_db_path="/Users/mlp/LLMTier-dev/state.sqlite3",
        )
        fake = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("reset_env.subprocess.run", return_value=fake) as runner:
            result = reset_env.step_backup(cfg)
        self.assertTrue(result.ok, result.detail)
        args = runner.call_args.args[0]
        self.assertEqual("ssh", args[0])
        self.assertIn(".backup", args[-1])

    def test_step_backup_remote_failure_is_reported(self):
        cfg = reset_env.ResetConfig(
            remote_db_host="m5air",
            remote_db_path="/Users/mlp/LLMTier-dev/state.sqlite3",
        )
        fake = mock.Mock(returncode=1, stdout="", stderr="sqlite3: not found")
        with mock.patch("reset_env.subprocess.run", return_value=fake):
            result = reset_env.step_backup(cfg)
        self.assertFalse(result.ok)
        self.assertIn("remote backup failed", result.detail)


class ResetRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "state.sqlite3"
        self.bak = Path(self.tmp.name) / "old.bak"
        self.bak.write_bytes(b"backup")

    def test_mutually_exclusive_restore_and_rebuild(self):
        cfg = reset_env.ResetConfig(db_path=self.db, restore=self.bak, rebuild=True)
        self.assertFalse(reset_env.step_restore_or_rebuild(cfg).ok)

    def test_restore_requires_db(self):
        cfg = reset_env.ResetConfig(restore=self.bak)
        self.assertFalse(reset_env.step_restore_or_rebuild(cfg).ok)

    def test_restore_copies_backup(self):
        self.db.write_bytes(b"live")
        cfg = reset_env.ResetConfig(db_path=self.db, restore=self.bak)
        result = reset_env.step_restore_or_rebuild(cfg)
        self.assertTrue(result.ok)
        self.assertEqual(b"backup", self.db.read_bytes())

    def test_rebuild_creates_fresh_db(self):
        self.db.write_bytes(b"live")
        cfg = reset_env.ResetConfig(db_path=self.db, rebuild=True)
        result = reset_env.step_restore_or_rebuild(cfg)
        self.assertTrue(result.ok)
        self.assertTrue(self.db.exists())
        self.assertEqual(b"", self.db.read_bytes())


class ResetInjectionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = reset_env.ResetConfig()

    def test_clear_injections_patches_each_deployment_and_verifies(self):
        calls = []

        def fake_request(method, url, token=None, body=None, timeout=5.0):
            calls.append((method, url, body))
            if method == "GET" and url.endswith("/v1/deployments"):
                return 200, '{"data":[{"id":"dep_a"},{"id":"dep_b"}]}'
            if method == "GET":
                return 200, "[]"  # verify empty
            if method == "PATCH":
                return 200, "[]"
            return 404, "{}"

        with mock.patch.object(reset_env, "_request", side_effect=fake_request):
            result = reset_env.step_clear_injections(self.cfg)
        self.assertTrue(result.ok, result.detail)
        patches = [c for c in calls if c[0] == "PATCH"]
        self.assertEqual(2, len(patches))
        self.assertTrue(all(c[2] == {"items": []} for c in patches))

    def test_clear_injections_fails_when_not_empty(self):
        def fake_request(method, url, token=None, body=None, timeout=5.0):
            if method == "GET" and url.endswith("/v1/deployments"):
                return 200, '{"data":[{"id":"dep_a"}]}'
            if method == "GET":
                return 200, '[{"type":"fault_502"}]'
            return 200, "[]"

        with mock.patch.object(reset_env, "_request", side_effect=fake_request):
            result = reset_env.step_clear_injections(self.cfg)
        self.assertFalse(result.ok)


class ResetLedgerTests(unittest.TestCase):
    def test_ledger_deletes_usage(self):
        seen = {}

        def fake_request(method, url, token=None, body=None, timeout=5.0):
            seen["method"], seen["url"] = method, url
            return 200, '{"deleted":3}'

        with mock.patch.object(reset_env, "_request", side_effect=fake_request):
            result = reset_env.step_reset_ledger(reset_env.ResetConfig())
        self.assertTrue(result.ok)
        self.assertEqual("DELETE", seen["method"])
        self.assertTrue(seen["url"].endswith("/v1/usage"))

    def test_ledger_skip_flag(self):
        result = reset_env.step_reset_ledger(reset_env.ResetConfig(no_ledger=True))
        self.assertTrue(result.ok)
        self.assertTrue(result.skipped)


class ResetKillTests(unittest.TestCase):
    def test_find_leftover_pids_only_matches_temp_instances(self):
        ps = "\n".join([
            "  100 /py -m http_api --host 127.0.0.1 --port 55 --database /tmp/llmtier_b_abc/test.sqlite3",
            "  200 /py -m http_api --host 0.0.0.0 --port 8181 --database /Users/mlp/LLMTier-dev/state.sqlite3",
            "  300 /py -m http_api --host 127.0.0.1 --port 66 --database /tmp/llmtier_check_env_xyz/check.sqlite3",
            "  400 grep http_api",
        ])
        self.assertEqual([100, 300], reset_env.find_leftover_pids(ps, self_pid=999))

    def test_find_leftover_pids_excludes_self(self):
        ps = "  100 /py -m http_api --database /tmp/llmtier_b_x/test.sqlite3"
        self.assertEqual([], reset_env.find_leftover_pids(ps, self_pid=100))

    def test_step_kill_dry_run_lists_pids(self):
        ps = "  100 /py -m http_api --database /tmp/llmtier_b_x/test.sqlite3"
        with mock.patch.object(reset_env, "_read_ps", return_value=ps):
            result = reset_env.step_kill_leftovers(reset_env.ResetConfig(dry_run=True))
        self.assertTrue(result.ok)
        self.assertIn("100", result.detail)


class ResetRecheckTests(unittest.TestCase):
    def test_build_readiness_command_shape(self):
        cfg = reset_env.ResetConfig(kind="a", base_url="http://h:1", admin_token="t")
        cmd = reset_env.build_readiness_command(cfg)
        self.assertIn("check_env.py", cmd[1])
        self.assertIn("--class", cmd)
        self.assertIn("a", cmd)
        self.assertIn("--json", cmd)

    def test_recheck_reports_failure(self):
        fake = mock.Mock(returncode=2, stdout="failed", stderr="")
        with mock.patch("reset_env.subprocess.run", return_value=fake):
            result = reset_env.step_recheck(reset_env.ResetConfig())
        self.assertFalse(result.ok)


# ---------------------------------------------------------------------------
# deploy.py
# ---------------------------------------------------------------------------

class DeployPinTests(unittest.TestCase):
    def test_artifact_pin_reads_openapi_and_schema(self):
        pin = deploy.artifact_pin(REPO)
        self.assertRegex(pin["openapi_version"], r"^0\.3-")
        self.assertEqual("2", pin["schema_version"])
        self.assertNotIn(pin["git_commit"], ("", "unknown"))

    def test_read_helper_fallbacks(self):
        missing = Path("/nonexistent/repo")
        self.assertEqual("unknown", deploy.read_openapi_version(missing))
        self.assertEqual("unknown", deploy.read_schema_version(missing))

    def test_step_pin_reports_missing(self):
        with mock.patch.object(deploy, "artifact_pin",
                               return_value={"git_commit": "unknown", "openapi_version": "x",
                                             "schema_version": "2"}):
            result, _ = deploy.step_pin(deploy.DeployConfig())
        self.assertFalse(result.ok)


class DeployCommandTests(unittest.TestCase):
    def setUp(self):
        self.cfg = deploy.DeployConfig(repo_root=REPO)

    def test_rsync_command_synced_src_and_target(self):
        cmd = deploy.rsync_command(self.cfg)
        self.assertEqual("rsync", cmd[0])
        self.assertIn(str(REPO / "src") + "/", cmd)
        self.assertEqual("m5air:/Users/mlp/LLMTier-dev/", cmd[-1])
        self.assertIn("--exclude", cmd)
        self.assertIn("state.sqlite3*", cmd)

    def test_find_pid_uses_lsof_on_port(self):
        cmd = deploy.find_pid_command(self.cfg)
        self.assertEqual(["ssh", "m5air", "/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN -t"], cmd)

    def test_kill_command_uses_term(self):
        cmd = deploy.kill_command(self.cfg, "4242")
        self.assertEqual(["ssh", "m5air", "kill -TERM 4242"], cmd)

    def test_start_command_has_314_python_pythonpath_and_module(self):
        cmd = deploy.start_command(self.cfg)
        remote = cmd[-1]
        self.assertIn(deploy.PYTHON314, remote)
        self.assertIn("PYTHONPATH=src", remote)
        self.assertIn("-m http_api", remote)
        self.assertIn("--port 8181", remote)
        self.assertIn(deploy.REMOTE_DB, remote)

    def test_start_command_never_contains_token_values(self):
        cfg = deploy.DeployConfig(repo_root=REPO, admin_token="SUPERSECRET",
                                  data_token="ALSOSECRET")
        cmd = deploy.start_command(cfg)
        for token in ("SUPERSECRET", "ALSOSECRET"):
            self.assertNotIn(token, " ".join(cmd))
            self.assertNotIn(token, cmd[-1])

    def test_start_command_reads_tokens_from_stdin(self):
        # Tokens are delivered on stdin, never argv (local or remote ps).
        cfg = deploy.DeployConfig(repo_root=REPO, admin_token="SUPERSECRET",
                                  data_token="ALSOSECRET")
        remote = deploy.start_command(cfg)[-1]
        self.assertIn("read -r LLMTIER_ADMIN_TOKEN", remote)
        self.assertIn("read -r LLMTIER_DATA_TOKEN", remote)
        payload = deploy.start_command_stdin(cfg)
        self.assertEqual("SUPERSECRET\nALSOSECRET\n", payload)

    def test_rollback_command_copies_backup(self):
        cmd = deploy.rollback_command(self.cfg, Path("/remote/backups/state.bak"))
        self.assertIn("cp /remote/backups/state.bak", cmd[-1])


class DeployFlowTests(unittest.TestCase):
    def test_dry_run_does_not_execute_subprocess(self):
        cfg = deploy.DeployConfig(repo_root=REPO, dry_run=True)
        with mock.patch("deploy.subprocess.run") as runner:
            results, pin = deploy.run_deploy(cfg)
        # read_git_commit legitimately shells out to git; no ssh/rsync may run.
        remote_calls = [c for c in runner.call_args_list
                        if c.args and c.args[0] and c.args[0][0] in ("ssh", "rsync")]
        self.assertEqual([], remote_calls)
        self.assertTrue(all(r.ok for r in results))
        self.assertEqual("2", pin["schema_version"])

    def test_pin_only_stops_after_pin(self):
        cfg = deploy.DeployConfig(repo_root=REPO, dry_run=True)
        results, _ = deploy.run_deploy(cfg, pin_only=True)
        self.assertEqual(["pin"], [r.name for r in results])

    def test_guard_requires_yes(self):
        with mock.patch.object(deploy, "run_deploy") as runner:
            rc = deploy.main([])
            self.assertEqual(deploy.EXIT_FAIL, rc)
            runner.assert_not_called()
            runner.return_value = ([deploy.StepResult("pin", True, "ok")], {})
            rc = deploy.main(["--pin-only"])
        self.assertEqual(deploy.EXIT_OK, rc)
        runner.assert_called_once()

    def test_rollback_dry_run_ok(self):
        cfg = deploy.DeployConfig(repo_root=REPO, dry_run=True)
        results = deploy.run_rollback(cfg, Path("/remote/backups/state.bak"))
        self.assertTrue(all(r.ok for r in results))
        self.assertEqual(["pin", "rollback"], [r.name for r in results])

    def test_rollback_reports_failure(self):
        cfg = deploy.DeployConfig(repo_root=REPO)
        fake = mock.Mock(returncode=1, stdout="rollback-missing", stderr="")
        with mock.patch("deploy.subprocess.run", return_value=fake):
            results = deploy.run_rollback(cfg, Path("/nope.bak"))
        self.assertFalse(results[-1].ok)

    def test_step_start_delivers_tokens_on_stdin_not_argv(self):
        cfg = deploy.DeployConfig(repo_root=REPO, admin_token="SUPERSECRET",
                                  data_token="ALSOSECRET")
        fake = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("deploy.subprocess.run", return_value=fake) as runner:
            result = deploy.step_start(cfg)
        self.assertTrue(result.ok, result.detail)
        call = runner.call_args
        argv = call.args[0]
        self.assertNotIn("SUPERSECRET", " ".join(argv))
        self.assertNotIn("ALSOSECRET", " ".join(argv))
        self.assertEqual("SUPERSECRET\nALSOSECRET\n", call.kwargs.get("input"))


if __name__ == "__main__":
    unittest.main()
