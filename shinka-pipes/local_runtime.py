"""Local-only runtime configuration; importing this module starts no jobs."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent
TASK = ROOT / "task-synthetic"
HEADLESS = ROOT / "runtime/node_modules/@roberttlange/headless/dist/cli.js"


def subscription_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY",
        "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY", "CODEX_MODEL",
    ):
        env.pop(name, None)
    env["HEADLESS_BILLING"] = "subscription"
    env["SHINKA_PRICING_MODE"] = "offline"
    env["SHINKA_HEADLESS_TIMEOUT"] = "900"
    env["SHINKA_HEADLESS_COMMAND"] = str(ROOT / "headless.sh")
    env["PIPES_SHINKA_ROOT"] = str(ROOT)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MPLCONFIGDIR"] = str(ROOT / ".tmp/matplotlib")
    env["PATH"] = str(ROOT / ".venv/bin") + os.pathsep + env.get("PATH", "")
    # The model is explicit in the active task; inspect native auth routing only.
    config_dir = Path(env.get("CODEX_HOME", str(Path.home() / ".codex")))
    config_path = config_dir / "config.toml"
    if config_path.is_file():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        if config.get("model_provider", "openai") != "openai":
            raise RuntimeError("Codex uses a custom provider; subscription-only setup requires openai.")
        if config.get("forced_login_method") == "api":
            raise RuntimeError("Codex is configured for API login; ChatGPT login is required.")
    return env


def check_prerequisites(env: dict[str, str]) -> dict[str, str]:
    node = shutil.which("node", path=env["PATH"])
    codex = shutil.which("codex", path=env["PATH"])
    if not node or not codex or not HEADLESS.is_file():
        raise RuntimeError("Node, Codex CLI, or local Headless is missing; see README.md.")
    version = subprocess.check_output([node, "--version"], text=True, env=env, timeout=15).strip()
    if int(version.lstrip("v").split(".")[0]) < 22:
        raise RuntimeError("Headless requires Node 22 or newer.")
    auth = subprocess.run([codex, "login", "status"], env=env, text=True,
                          capture_output=True, timeout=20, check=False)
    if auth.returncode or "Logged in using ChatGPT" not in auth.stdout + auth.stderr:
        raise RuntimeError("Codex CLI is not signed in through ChatGPT; no API fallback is allowed.")
    return {"node": version, "codex": codex, "auth": "ChatGPT", "billing": "subscription"}
