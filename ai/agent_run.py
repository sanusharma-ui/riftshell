"""Bounded task state shared by the desktop planner and execution callbacks."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ai.actions import AgentAction


@dataclass
class AgentRun:
    objective: str
    max_steps: int = 8
    planner: object = None
    observations: list[dict] = field(default_factory=list)
    pending: AgentAction | None = None
    stopped: bool = False
    steps: int = 0
    _seen: set[str] = field(default_factory=set)

    def accept(self, action: AgentAction) -> AgentAction:
        if self.stopped:
            return AgentAction("respond", "This task has been stopped.")
        if action.action == "respond":
            self.stopped = True
            return action
        signature = repr((action.action, action.command, action.paths,
                          [(f.path, f.content) for f in action.files]))
        key = hashlib.sha256(signature.encode()).hexdigest()
        if self.steps >= self.max_steps or key in self._seen:
            self.stopped = True
            return AgentAction("respond", "I paused because this task reached its step limit or repeated an action. Review the results before starting another attempt.")
        self._seen.add(key)
        self.steps += 1
        self.pending = action
        return action

    def observe(self, result) -> bool:
        if self.stopped or self.pending is None:
            return False
        action, self.pending = self.pending, None
        self.observations.append({
            "action": action.action,
            "command": action.command,
            "paths": [f.path for f in action.files],
            "success": bool(result.success),
            "output": str(result.output)[-6000:],
        })
        return True

    def stop(self):
        self.stopped = True
        self.pending = None
