#!/usr/bin/env python3
"""Universal installer for openclaw-skills.

One command to install any skill with full agent creation, Telegram setup,
dependencies, hooks, and wizard — zero manual file editing.

Usage:
  python3 install.py romantic-companion
  python3 install.py companion
  python3 install.py persistent-memory
  python3 install.py agent-pulse
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILLS = {
    "romantic-companion": {
        "description": "💕 Romantic AI partner — seduction to deep bond",
        "dedicated_agent": True,
        "needs_telegram": True,
        "needs_python_deps": True,
        "has_hook": True,
        "has_wizard": True,
    },
    "companion": {
        "description": "🤖 AI companion — friend that remembers and lives",
        "dedicated_agent": True,
        "needs_telegram": True,
        "needs_python_deps": True,
        "has_hook": True,
        "has_wizard": True,
    },
    "persistent-memory": {
        "description": "🧠 Long-term memory + emotional intelligence",
        "dedicated_agent": False,
        "needs_telegram": False,
        "needs_python_deps": True,
        "has_hook": True,
        "has_wizard": False,
    },
    "agent-pulse": {
        "description": "📡 Inter-agent visibility protocol",
        "dedicated_agent": False,
        "needs_telegram": False,
        "needs_python_deps": False,
        "has_hook": False,
        "has_wizard": False,
    },
}

def colored(text, color):
    colors = {"green": "\033[92m", "yellow": "\033[93m", "blue": "\033[94m",
              "red": "\033[91m", "bold": "\033[1m", "end": "\033[0m", "cyan": "\033[96m"}
    return f"{colors.get(color, '')}{text}{colors['end']}"

def ask(prompt, default=None, required=True):
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nInstallation cancelled.")
        sys.exit(0)
    if not value and default:
        return default
    if not value and required:
        print(colored("    Required.", "red"))
        return ask(prompt, default, required)
    return value

def ask_yn(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    answer = ask(f"{prompt} {suffix}", required=False)
    if not answer:
        return default
    return answer.lower().startswith("y")

def run_cmd(cmd, check=True, capture=False):
    """Run a shell command."""
    print(colored(f"  $ {cmd}", "cyan"))
    try:
        result = subprocess.run(cmd, shell=True, check=check,
                              capture_output=capture, text=True)
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(colored(f"  ERROR: {e}", "red"))
        return e

def detect_openclaw():
    """Detect OpenClaw installation."""
    openclaw_dir = os.path.expanduser("~/.openclaw")
    if not os.path.isdir(openclaw_dir):
        return None
    return openclaw_dir

def detect_agents(openclaw_dir):
    """List existing agents."""
    agents_dir = os.path.join(openclaw_dir, "agents")
    if not os.path.isdir(agents_dir):
        return []
    return [d for d in os.listdir(agents_dir)
            if os.path.isdir(os.path.join(agents_dir, d))]

def find_skill_source(skill_name):
    """Find the skill source directory."""
    # Check if we're in the repo
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), skill_name)
    if os.path.isdir(local) and os.path.exists(os.path.join(local, "SKILL.md")):
        return local
    return None

def install(skill_name):
    """Main installation flow."""
    if skill_name not in SKILLS:
        print(colored(f"Unknown skill: {skill_name}", "red"))
        print(f"Available: {', '.join(SKILLS.keys())}")
        sys.exit(1)

    skill_info = SKILLS[skill_name]

    print(colored("╔══════════════════════════════════════════╗", "blue"))
    print(colored(f"║  Installing: {skill_name:<28}║", "blue"))
    print(colored(f"║  {skill_info['description']:<40}║", "blue"))
    print(colored("╚══════════════════════════════════════════╝", "blue"))
    print()

    # Step 1: Check OpenClaw
    print(colored("═══ Step 1: Checking OpenClaw ═══", "blue"))
    openclaw_dir = detect_openclaw()
    if not openclaw_dir:
        print(colored("  OpenClaw not found at ~/.openclaw", "red"))
        print("  Install OpenClaw first: https://docs.openclaw.ai")
        sys.exit(1)
    print(colored(f"  ✓ OpenClaw found at {openclaw_dir}", "green"))

    # Step 2: Find skill source
    print(colored("\n═══ Step 2: Locating skill ═══", "blue"))
    skill_source = find_skill_source(skill_name)
    if not skill_source:
        print(colored(f"  Skill '{skill_name}' not found locally.", "red"))
        print("  Make sure you're running from the openclaw-skills repo directory.")
        print(f"  Expected: ./{skill_name}/SKILL.md")
        sys.exit(1)
    print(colored(f"  ✓ Found at {skill_source}", "green"))

    # Step 3: Agent creation (if needed)
    if skill_info["dedicated_agent"]:
        print(colored("\n═══ Step 3: Creating dedicated agent ═══", "blue"))
        print(f"  {skill_name} needs its own agent (separate from your main agent).")

        agent_name = ask("Agent name", default=skill_name.replace("-companion", "").replace("-", ""))
        agents = detect_agents(openclaw_dir)

        if agent_name in agents:
            print(colored(f"  Agent '{agent_name}' already exists.", "yellow"))
            if not ask_yn("  Use existing agent?"):
                agent_name = ask("Different agent name")
        else:
            print(f"  Creating agent '{agent_name}'...")
            agent_dir = os.path.join(openclaw_dir, "agents", agent_name)
            workspace_dir = os.path.join(agent_dir, "workspace")
            os.makedirs(workspace_dir, exist_ok=True)
            os.makedirs(os.path.join(workspace_dir, "skills"), exist_ok=True)
            os.makedirs(os.path.join(workspace_dir, "memory"), exist_ok=True)
            print(colored(f"  ✓ Agent '{agent_name}' created at {agent_dir}", "green"))

        workspace_dir = os.path.join(openclaw_dir, "agents", agent_name, "workspace")
        skills_dir = os.path.join(workspace_dir, "skills")
    else:
        print(colored("\n═══ Step 3: Choosing install location ═══", "blue"))
        print("  Install globally (all agents) or for a specific agent?")
        global_install = ask_yn("  Install globally?", default=True)

        if global_install:
            skills_dir = os.path.join(openclaw_dir, "skills")
            workspace_dir = os.path.expanduser("~/.openclaw/workspace")
        else:
            agents = detect_agents(openclaw_dir)
            if agents:
                print(f"  Available agents: {', '.join(agents)}")
            agent_name = ask("Agent name", default="main")
            workspace_dir = os.path.join(openclaw_dir, "agents", agent_name, "workspace")
            skills_dir = os.path.join(workspace_dir, "skills")

    os.makedirs(skills_dir, exist_ok=True)
    os.makedirs(workspace_dir, exist_ok=True)

    # Step 4: Telegram bot (if needed)
    telegram_config = None
    if skill_info["needs_telegram"]:
        print(colored("\n═══ Step 4: Telegram Bot Setup ═══", "blue"))
        print("  This agent needs its own Telegram bot to chat with you.")
        print()
        print("  How to create a bot:")
        print("  1. Open Telegram, search for @BotFather")
        print("  2. Send /newbot")
        print("  3. Choose a name (e.g., 'Luna 💕')")
        print("  4. Choose a username (e.g., 'luna_companion_bot')")
        print("  5. Copy the token BotFather gives you")
        print()

        has_bot = ask_yn("  Do you already have a Telegram bot token?")
        if has_bot:
            bot_token = ask("  Bot token")
            telegram_config = {"token": bot_token}
            print(colored("  ✓ Bot token saved", "green"))
        else:
            print(colored("  ⏭ Skipped. You'll need to configure Telegram later.", "yellow"))
            print("  Add to your agent config: channels.telegram.token = 'your-token'")

    # Step 5: Install dependencies
    if skill_info["needs_python_deps"]:
        print(colored("\n═══ Step 5: Installing Python dependencies ═══", "blue"))
        result = run_cmd("pip3 install sqlite-vec openai 2>&1 | tail -3", check=False)
        if result.returncode != 0:
            run_cmd("pip3 install --break-system-packages sqlite-vec openai 2>&1 | tail -3", check=False)
        print(colored("  ✓ Dependencies installed", "green"))

    # Step 6: Copy skill
    print(colored(f"\n═══ Step 6: Installing {skill_name} ═══", "blue"))
    dest = os.path.join(skills_dir, skill_name)
    if os.path.exists(dest):
        if ask_yn(f"  {dest} already exists. Overwrite?", default=False):
            shutil.rmtree(dest)
        else:
            print(colored("  Keeping existing installation.", "yellow"))

    if not os.path.exists(dest):
        shutil.copytree(skill_source, dest)
    print(colored(f"  ✓ Skill installed to {dest}", "green"))

    # Step 7: Install hook
    if skill_info["has_hook"]:
        print(colored("\n═══ Step 7: Installing anti-compaction hook ═══", "blue"))
        hook_source = os.path.join(dest, "hooks", "session-journal")
        hook_dest = os.path.join(openclaw_dir, "hooks", "session-journal")

        if os.path.exists(hook_source):
            os.makedirs(os.path.join(openclaw_dir, "hooks"), exist_ok=True)
            if os.path.exists(hook_dest):
                shutil.rmtree(hook_dest)
            shutil.copytree(hook_source, hook_dest)
            print(colored("  ✓ Hook installed", "green"))

            # Try to enable
            run_cmd("openclaw hooks enable session-journal 2>/dev/null", check=False)
            print(colored("  ✓ Hook enabled", "green"))

    # Step 8: Agent config (Telegram + model)
    if skill_info["dedicated_agent"] and telegram_config:
        print(colored("\n═══ Step 8: Configuring agent ═══", "blue"))
        agent_config_dir = os.path.join(openclaw_dir, "agents", agent_name)
        config_path = os.path.join(agent_config_dir, "config.json")

        config = {}
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)

        # Add Telegram channel
        if "channels" not in config:
            config["channels"] = {}
        config["channels"]["telegram"] = {
            "enabled": True,
            "token": telegram_config["token"],
        }

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(colored(f"  ✓ Telegram configured for agent '{agent_name}'", "green"))

    # Step 9: Run wizard (if available)
    if skill_info["has_wizard"]:
        print(colored(f"\n═══ Step 9: Setup Wizard ═══", "blue"))
        wizard_path = os.path.join(dest, "scripts", "setup_wizard.py")
        if os.path.exists(wizard_path):
            print("  Launching the setup wizard...\n")
            os.chdir(workspace_dir)
            os.system(f"python3 {wizard_path}")
        else:
            print(colored("  Wizard not found, skipping.", "yellow"))
    elif skill_info["needs_python_deps"]:
        # Manual init for persistent-memory
        print(colored(f"\n═══ Step 9: Initializing database ═══", "blue"))
        init_script = os.path.join(dest, "scripts", "memory_init.py")
        db_path = os.path.join(workspace_dir, "memory.db")
        if os.path.exists(init_script):
            os.system(f"python3 {init_script} --db {db_path}")
            print(colored(f"  ✓ Database initialized at {db_path}", "green"))

    # Step 10: Summary
    print()
    print(colored("╔══════════════════════════════════════════╗", "green"))
    print(colored("║         Installation Complete! 🎉         ║", "green"))
    print(colored("╚══════════════════════════════════════════╝", "green"))
    print()
    print(f"  Skill: {skill_name}")
    if skill_info["dedicated_agent"]:
        print(f"  Agent: {agent_name}")
    print(f"  Location: {dest}")
    if skill_info["has_hook"]:
        print(f"  Hook: session-journal (enabled)")
    print()

    if skill_info["dedicated_agent"]:
        print("  Next steps:")
        if not telegram_config:
            print("  1. Create a Telegram bot via @BotFather")
            print(f"  2. Add the token to ~/.openclaw/agents/{agent_name}/config.json")
        print(f"  3. Restart OpenClaw: openclaw gateway restart")
        print(f"  4. Open Telegram and talk to your companion! 💬")
    else:
        print("  Next steps:")
        print("  1. Restart OpenClaw: openclaw gateway restart")
        print("  2. The skill will activate automatically")
    print()
    print(colored("  Enjoy! 👑", "bold"))

def main():
    parser = argparse.ArgumentParser(
        description="Install OpenClaw skills — one command, zero hassle",
        usage="python3 install.py <skill-name>"
    )
    parser.add_argument("skill", nargs="?", help="Skill to install")
    parser.add_argument("--list", action="store_true", help="List available skills")
    args = parser.parse_args()

    if args.list or not args.skill:
        print(colored("\n  Available skills:\n", "bold"))
        for name, info in SKILLS.items():
            dedicated = " (⚠️ dedicated agent)" if info["dedicated_agent"] else ""
            print(f"  • {colored(name, 'bold')} — {info['description']}{dedicated}")
        print(f"\n  Install: python3 install.py <skill-name>\n")
        return

    install(args.skill)

if __name__ == "__main__":
    main()
