from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


class AgentBackendMixin:
    def _run_cli(
        self,
        command: list[str],
        cwd: str,
        timeout: int,
        input_text: str,
    ) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                command,
                cwd=cwd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timed_out": True,
            }

    def _write_result_message(self, stdout: str, output_path: str) -> None:
        Path(output_path).write_text(stdout, encoding="utf-8")

    def _acquire_file_lock(self, lock_path: str) -> bool:
        lock_file = Path(lock_path)
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY)
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError):
            os.close(fd)
            return False
