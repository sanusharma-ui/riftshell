"""Patch ai/llm.py _remember_action to include live current_dir for nav commands."""
from pathlib import Path
import re

src = Path("ai/llm.py")
content = src.read_text(encoding="utf-8")

old = (
    '    def _remember_action(self, user_text: str, action: AgentAction) -> AgentAction:\n'
    '        self.memory.add("user", user_text)\n'
    '        summary = f"Proposed action (execution not confirmed): {action.action}; Command: {action.command or \'(none)\'}; Response: {action.message}"\n'
    '        self.memory.add("assistant", summary)\n'
    '        return action\n'
)

new = (
    '    # Navigation commands whose successful execution changes the tracked location.\n'
    '    _NAV_COMMANDS = {"cd", "goto", "chdir", "up", "home"}\n'
    '\n'
    '    def _remember_action(self, user_text: str, action: AgentAction) -> AgentAction:\n'
    '        self.memory.add("user", user_text)\n'
    '        # For navigation shell actions, record the actual live directory so that\n'
    '        # subsequent prompts (e.g. "where") never infer location from stale memory.\n'
    '        nav_note = ""\n'
    '        if (\n'
    '            action.action == "shell"\n'
    '            and action.command\n'
    '            and action.command.strip().split()[0].lower() in self._NAV_COMMANDS\n'
    '            and self.current_dir_provider\n'
    '        ):\n'
    '            nav_note = f"; Live directory after navigation: {self.current_dir_provider()}"\n'
    '        summary = (\n'
    '            f"Proposed action (execution not confirmed): {action.action}; "\n'
    '            f"Command: {action.command or \'(none)\'}; Response: {action.message}"\n'
    '            + nav_note\n'
    '        )\n'
    '        self.memory.add("assistant", summary)\n'
    '        return action\n'
)

if old in content:
    updated = content.replace(old, new)
    src.write_text(updated, encoding="utf-8")
    import ast
    ast.parse(updated)
    print("Patched and syntax OK.")
else:
    print("FAIL: pattern not found")
    idx = content.find("def _remember_action")
    print(repr(content[idx:idx+400]))
