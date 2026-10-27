#!/usr/bin/env python3
"""Synapse AI - CLI Interface for terminal-based AI brain interaction."""
import sys
import os
import json
import asyncio
from pathlib import Path

# Windows 下强制使用 UTF-8 编码，解决中文输入/输出乱码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from brain import SynapseBrain
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# ANSI colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_PURPLE = "\033[35m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_BLUE = "\033[34m"
C_GRAY = "\033[90m"

ICONS = {
    "thinking": "\U0001F9E0",
    "tool_call": "⚙",
    "tool_result": "✔",
    "response": "✨",
}


def print_banner():
    print(f"""{C_PURPLE}{C_BOLD}
   _____                               _
  / ____|                             | |
 | (___  _   _ _ __  _ __   __ _  ___ | |_  ___
  \___ \| | | | '_ \| '_ \ / _` |/ _ \| __|/ _ \\
  ____) | |_| | | | | |_) | (_| | (_) | |_|  __/
 |_____/ \__, |_| |_| .__/ \__,_|\___/ \__|\___|
          __/ |     | |
         |___/      |_|   {C_CYAN}AI Brain Studio{C_RESET}

{C_DIM}Powered by DeepSeek | Type /help for commands, /quit to exit{C_RESET}
""")
    print(f"{C_GRAY}{'='*60}{C_RESET}")


def print_help():
    print(f"""
{C_BOLD}Commands:{C_RESET}
  {C_CYAN}/help{C_RESET}      Show this help
  {C_CYAN}/quit{C_RESET}      Exit Synapse AI
  {C_CYAN}/clear{C_RESET}     Clear conversation history
  {C_CYAN}/tools{C_RESET}     List available tools
  {C_CYAN}/model{C_RESET}     Show current model info
  {C_CYAN}/history{C_RESET}   Show conversation history
  {C_CYAN}/save <file>{C_RESET}  Save conversation to file

{C_BOLD}Tips:{C_RESET}
  - Just type anything to chat with the AI brain
  - The AI will decide when to use tools automatically
  - You'll see the neural thought chain as it processes
""")


async def main():
    print_banner()

    # Check API key
    api_key = DEEPSEEK_API_KEY
    if api_key == "your-api-key-here":
        api_key = input(f"{C_YELLOW}Enter your DeepSeek API key: {C_RESET}").strip()
        if not api_key:
            print(f"{C_RED}API key required. Set DEEPSEEK_API_KEY env var.{C_RESET}")
            return

    brain = SynapseBrain(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
    )

    print(f"{C_GREEN}Brain initialized. Model: {brain.model}{C_RESET}\n")

    history = []

    while True:
        try:
            user_input = input(f"{C_BOLD}{C_PURPLE}You > {C_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_YELLOW}Goodbye!{C_RESET}")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()
            if cmd == "/quit" or cmd == "/exit":
                print(f"{C_YELLOW}Goodbye!{C_RESET}")
                break
            elif cmd == "/help":
                print_help()
                continue
            elif cmd == "/clear":
                history = []
                print(f"{C_GREEN}Conversation cleared.{C_RESET}")
                continue
            elif cmd == "/tools":
                print(f"\n{C_BOLD}Available Tools:{C_RESET}")
                for t in brain.tools:
                    print(f"  {C_CYAN}{t.name:20s}{C_RESET} {t.description}")
                print()
                continue
            elif cmd == "/model":
                print(f"{C_GRAY}Model: {brain.model}{C_RESET}")
                continue
            elif cmd == "/history":
                print(f"\n{C_GRAY}Conversation history ({len(history)} messages):{C_RESET}")
                for i, msg in enumerate(history):
                    role = "You" if msg["role"] == "user" else "AI"
                    preview = msg["content"][:100]
                    print(f"  {C_DIM}{i+1}.{C_RESET} [{role}] {preview}")
                print()
                continue
            elif cmd == "/save":
                parts = user_input.split(maxsplit=1)
                filename = parts[1] if len(parts) > 1 else "conversation.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
                print(f"{C_GREEN}Saved to {filename}{C_RESET}")
                continue
            else:
                print(f"{C_RED}Unknown command: {cmd}{C_RESET}")
                continue

        # Process message
        print(f"{C_CYAN}Brain is thinking...{C_RESET}", end="\r")
        try:
            result = await brain.think(user_input, history)

            # Show thought chain
            for t in result["thoughts"]:
                icon = ICONS.get(t["type"], "  ")
                color = {
                    "thinking": C_GRAY,
                    "tool_call": C_CYAN,
                    "tool_result": C_GREEN,
                    "response": C_PURPLE,
                }.get(t["type"], "")

                short = t["content"][:80]
                print(f"  {color}{icon} [{t['type']:12s}]{C_RESET} {short}")

            print(f"\n{C_BOLD}Synapse > {C_RESET}", end="")
            print(result["response"])
            print(f"{C_GRAY}{'='*60}{C_RESET}")

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result["response"]})

            # Keep history manageable
            if len(history) > 40:
                history = history[-40:]

        except Exception as e:
            print(f"\n{C_RED}Error: {e}{C_RESET}")


if __name__ == "__main__":
    asyncio.run(main())
