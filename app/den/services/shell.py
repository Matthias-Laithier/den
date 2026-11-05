import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CHECK_TIMEOUT_SECONDS = 30
QUERY_TIMEOUT_SECONDS = 60
INSTALL_STEP_TIMEOUT_SECONDS = 3600
COMMAND_COLOR = "\033[1;34m"
FAILURE_COLOR = "\033[1;31m"
DIM = "\033[2m"
RESET = "\033[0m"
SUDO = "/usr/bin/sudo"
ASKPASS_SCRIPT = f"""#!/bin/bash
cache="$(dirname "$0")/password"
for attempt in 1 2 3; do
  [[ -s "$cache" ]] && break
  printf '[den] sudo password for %s: ' "$USER" >/dev/tty
  read -rs password </dev/tty || exit 1
  echo >/dev/tty
  if printf '%s\\n' "$password" | {SUDO} -S -k -v -p '' 2>/dev/null; then
    (umask 077 && printf '%s' "$password" >"$cache")
  else
    echo "Sorry, try again." >/dev/tty
  fi
done
cat "$cache"
"""
SUDO_SHIM = f'#!/bin/bash\nexec {SUDO} -A "$@"\n'


class CommandFailed(Exception):
    pass


def succeeds(command: str) -> bool:
    try:
        return (
            subprocess.run(
                ["bash", "-c", command], capture_output=True, timeout=CHECK_TIMEOUT_SECONDS, check=False
            ).returncode
            == 0
        )
    except subprocess.TimeoutExpired as error:
        raise CommandFailed(f"Timed out after {CHECK_TIMEOUT_SECONDS}s: {command}") from error


def is_available(program: str) -> bool:
    return shutil.which(program) is not None


def output(*args: str, accepted_exit_codes: tuple[int, ...] = (0,), timeout: int = QUERY_TIMEOUT_SECONDS) -> str:
    try:
        result = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise CommandFailed(f"Timed out after {timeout}s: {' '.join(args)}") from error
    if result.returncode not in accepted_exit_codes:
        raise CommandFailed(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _run_step(step: str, env: dict[str, str]) -> bool:
    print(f"{COMMAND_COLOR}$ {step}{RESET}", flush=True)
    try:
        succeeded = (
            subprocess.run(["bash", "-c", step], env=env, timeout=INSTALL_STEP_TIMEOUT_SECONDS, check=False).returncode
            == 0
        )
    except subprocess.TimeoutExpired:
        succeeded = False
    if not succeeded:
        print(f"{FAILURE_COLOR}failed{RESET}", flush=True)
    return succeeded


def _executable(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o700)
    return path


def _sudo_environment(directory: Path) -> dict[str, str]:
    askpass = _executable(directory / "askpass", ASKPASS_SCRIPT)
    shim = _executable(directory / "bin" / "sudo", SUDO_SHIM)
    path = f"{shim.parent}{os.pathsep}{os.environ.get('PATH', '')}"
    return {**os.environ, "SUDO_ASKPASS": str(askpass), "PATH": path}


def run_steps(steps: list[str]) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="den-sudo-") as directory:
        env = _sudo_environment(Path(directory))
        failed = [step for step in steps if not _run_step(step, env)]
    try:
        input(f"\n{DIM}Press enter to go back to den{RESET}")
    except EOFError:
        pass
    return failed
