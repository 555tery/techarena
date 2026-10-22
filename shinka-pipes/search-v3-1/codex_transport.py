"""Restrict Headless Codex calls to supplied text, without workspace/history tools."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
DISABLED = ("shell_tool", "unified_exec", "code_mode", "code_mode_host", "apps", "plugins",
            "memories", "multi_agent", "multi_agent_v2", "computer_use", "browser_use",
            "browser_use_external", "in_app_browser", "view_image", "image_generation",
            "skill_search", "hooks", "tool_suggest", "workspace_dependencies")


def command(arguments, cwd):
    if arguments in (["login", "status"], ["--version"], ["-V"]):
        return [CODEX, *arguments]
    if "exec" not in arguments or "resume" in arguments or "fork" in arguments:
        raise ValueError("model transport accepts only fresh codex exec calls")
    args = [arg for arg in arguments if arg != "--search"]
    at = args.index("exec") + 1
    args[at:at] = ["--ignore-user-config", "--ignore-rules", "-C", str(cwd)]
    for feature in DISABLED:
        args[at:at] = ["-c", f"features.{feature}=false"]
    for setting in ('web_search="disabled"', "project_doc_max_bytes=0", "skills.include_instructions=false",
                    "features.skip_host_skill_discovery=true", "agents.enabled=false", "memories.use_memories=false",
                    'service_tier="default"', "include_apps_instructions=false"):
        args[at:at] = ["-c", setting]
    return [CODEX, *args]


def main():
    # Outside project ancestors so their .codex config cannot add MCP servers.
    directory = Path(tempfile.mkdtemp(prefix="shinka-text-only-"))
    args = command(sys.argv[1:], directory)
    env = os.environ.copy()
    # Headless receives the transcript normally; an empty cwd has no corpus or allocator.
    os.execve(CODEX, args, env)


if __name__ == "__main__":
    main()
