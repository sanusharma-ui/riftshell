"""Bounded task state shared by the desktop planner and execution callbacks."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable

from ai.actions import AgentAction
from ai.modes import OrbitMode


@dataclass
class AgentRun:
    objective: str
    max_steps: int = 8
    planner: object = None
    mode: OrbitMode | None = None
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
                          [(f.path, f.content) for f in action.files],
                          action.tool, action.tool_args))
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


@dataclass
class AgentLoop:
    """Runs a multi-step task: plan -> execute -> observe -> plan the next step.

    The loop ends when: the planner answers (respond), an action has
    continue_after_result=False, the step limit is reached, an action repeats,
    the user cancels, or an action was not executed (e.g. approval declined).

    on_action(action) must run ONE action and return its result (an object with
    .success and .output), or None when the action was not executed.
    on_progress(message) and cancelled() are optional callbacks.
    first_action lets the UI pass an action it already planned, so the first
    step is not planned twice.

    run() blocks until the task ends - call it from a worker thread, not the UI thread.
    """
    objective: str
    planner: object
    on_action: Callable
    on_progress: Callable | None = None
    cancelled: Callable | None = None
    max_steps: int = 8
    observations: list[dict] = field(default_factory=list)
    steps: int = 0
    finished: bool = False
    _seen: set[str] = field(default_factory=set)

    def _finish(self, message: str) -> str:
        self.finished = True
        return message

    def run(self, first_action: AgentAction | None = None) -> str:
        action = first_action if first_action is not None else self.planner.plan(self.objective)
        while not self.finished:
            if self.cancelled and self.cancelled():
                return self._finish("Task was cancelled.")
            if action.action == "respond":
                return self._finish(action.message)

            signature = repr((action.action, action.command, action.paths,
                              [(f.path, f.content) for f in action.files],
                              action.tool, action.tool_args))
            key = hashlib.sha256(signature.encode()).hexdigest()
            if key in self._seen:
                return self._finish("Task paused: the same action came up twice. Review the results before continuing.")
            if self.steps >= self.max_steps:
                return self._finish(f"Task paused after {self.max_steps} steps. Review the results and continue if needed.")
            self._seen.add(key)
            self.steps += 1
            if self.on_progress:
                self.on_progress(f"Step {self.steps}: {action.message or action.command or action.action}")

            try:
                result = self.on_action(action)
            except Exception as exc:  # keep the loop from crashing the UI thread
                return self._finish(f"Task stopped: step {self.steps} failed ({exc}).")
            if result is None:
                return self._finish(f"Task stopped: step {self.steps} was not executed.")

            self.observations.append({
                "step": self.steps,
                "action": action.action,
                "command": action.command,
                "paths": [f.path for f in action.files],
                "success": bool(result.success),
                "output": str(result.output)[-3000:],
            })
            if not getattr(action, "continue_after_result", False):
                return self._finish(f"Done. {action.message}".strip())
            action = self.planner.continue_task(self.objective, self.observations)
        return "Task completed."
