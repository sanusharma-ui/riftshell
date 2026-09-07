import unittest
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.actions import AgentAction
from ai.agent_run import AgentRun
from ai.llm import AgentPlanner
from test_workspace_agent import make_config, SequencedGemini

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from ui.main_window import OrbitPanel, MainWindow, OrbitWorker, CommandWorker


class AgentRunTests(unittest.TestCase):
    def test_results_drive_next_action_then_final_answer(self):
        planner = AgentPlanner(make_config(Path.cwd()), ["where", "files"], [])
        planner._gemini = SequencedGemini(
            {"action": "shell", "command": "where", "message": "Checking location."},
            {"action": "shell", "command": "files", "message": "Checking files."},
            {"action": "respond", "message": "The folder contains main.py."},
        )
        task = AgentRun("Find the current folder and list its files", planner=planner)
        task.accept(planner.plan(task.objective))
        self.assertTrue(task.observe(SimpleNamespace(success=True, output="D:/demo")))
        action = task.accept(planner.continue_task(task.objective, task.observations))
        self.assertEqual(action.command, "files")
        task.observe(SimpleNamespace(success=True, output="main.py"))
        final = task.accept(planner.continue_task(task.objective, task.observations))
        self.assertEqual(final.action, "respond")
        self.assertTrue(task.stopped)
        self.assertIn("D:/demo", planner._gemini.prompts[1])
        self.assertIn("main.py", planner._gemini.prompts[2])

    def test_failure_is_evidence_and_duplicate_is_blocked(self):
        task = AgentRun("Check files")
        command = AgentAction("shell", command="files")
        task.accept(command)
        task.observe(SimpleNamespace(success=False, output="Access denied"))
        self.assertFalse(task.observations[0]["success"])
        self.assertEqual(task.accept(command).action, "respond")
        self.assertTrue(task.stopped)

    def test_stop_ignores_late_results(self):
        task = AgentRun("Check files")
        task.accept(AgentAction("shell", command="files"))
        task.stop()
        self.assertFalse(task.observe(SimpleNamespace(success=True, output="late result")))
        self.assertEqual(task.observations, [])

    def test_step_budget_and_output_bound(self):
        task = AgentRun("Inspect", max_steps=1)
        task.accept(AgentAction("shell", command="where"))
        task.observe(SimpleNamespace(success=True, output="x" * 10000))
        self.assertEqual(len(task.observations[0]["output"]), 6000)
        self.assertEqual(task.accept(AgentAction("shell", command="files")).action, "respond")

    def test_natural_query_reaches_model_instead_of_static_routing(self):
        planner = AgentPlanner(make_config(Path.cwd()), ["files"], [])
        planner._gemini = SequencedGemini({"action": "respond", "message": "Here is what a file system does."})
        action = planner.plan("Tell me how file systems work")
        self.assertEqual(action.action, "respond")
        self.assertEqual(len(planner._gemini.prompts), 1)

    def test_continuation_does_not_allow_other_file_target(self):
        planner = AgentPlanner(make_config(Path.cwd()), [], [])
        planner._gemini = SequencedGemini({"action": "code_write", "files": [{"path": "other.py", "content": "oops"}]})
        action = planner.continue_task("Fix app.py", [{"success": True, "output": "saved"}])
        self.assertEqual(action.action, "respond")
        self.assertIn("blocked", action.message)

    def test_related_file_inspection_can_continue(self):
        planner = AgentPlanner(make_config(Path.cwd()), [], [])
        planner._gemini = SequencedGemini(
            {"action": "inspect", "paths": ["ai/actions.py"], "objective": "Understand action types"},
            {"action": "respond", "message": "The planner returns a structured action."},
        )
        action = planner.plan("Explain ai/agent_run.py")
        self.assertEqual(action.action, "respond")
        self.assertIn("structured action", action.message)
        self.assertEqual(len(planner._gemini.prompts), 2)

    def test_worker_uses_result_continuation(self):
        planner = Mock()
        planner.continue_task.return_value = AgentAction("respond", "Checked the result.")
        task = AgentRun("Check files", planner=planner)
        task.observations.append({"success": True, "output": "main.py"})
        worker = OrbitWorker(Mock(), task.objective, task=task)
        with patch("ai.config.AIConfig.from_env", return_value=make_config(Path.cwd())):
            worker.run()
        planner.continue_task.assert_called_once_with(task.objective, task.observations)
        planner.plan.assert_not_called()

    def test_stopped_planner_does_not_call_provider(self):
        planner = AgentPlanner(make_config(Path.cwd()), [], [], cancelled=lambda: True)
        planner._call_provider = Mock()
        action = planner.plan("Explain dependency injection")
        self.assertEqual(action.action, "respond")
        planner._call_provider.assert_not_called()

    def test_requested_file_stays_bound_to_original_directory(self):
        planner = AgentPlanner(make_config(Path.cwd()), [], [])
        planner._task_origin_dir = Path.cwd()
        planner.current_dir_provider = lambda: Path.cwd() / "ai"
        planner._gemini = SequencedGemini({"action": "code_write", "files": [{"path": "app.py", "content": "wrong directory"}]})
        action = planner.continue_task("Fix app.py", [{"success": True, "output": "changed directory"}])
        self.assertEqual(action.action, "respond")
        self.assertIn("blocked", action.message)


class OrbitLoopUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.session = SimpleNamespace(shell=SimpleNamespace(ctx=SimpleNamespace(cwd=Path.cwd())), is_busy=False)
        self.panel = OrbitPanel(lambda: self.session)
        self.panel.task = AgentRun("Inspect the project")
        self.panel.task_session = self.session
        self.panel.task_cwd = Path.cwd()
        self.emitted = []
        self.panel.action_requested.connect(lambda *args: self.emitted.append(args))

    def tearDown(self):
        self.panel.stop_task()
        self.panel.stream_timer.stop()
        self.panel.close()
        self.panel.deleteLater()

    def test_risky_next_step_waits_for_its_own_approval(self):
        action = AgentAction("shell", command="run python check.py")
        self.panel._show_plan(action)
        self.assertEqual(self.emitted, [])
        self.assertIs(self.panel.pending_action, action)
        self.panel.approve()
        self.assertEqual(self.emitted, [(action, True, None)])
        self.assertFalse(self.panel.input.isEnabled())

    def test_stop_discards_late_planner_action(self):
        self.panel.stop_task()
        self.panel._show_plan(AgentAction("shell", command="files"))
        self.assertEqual(self.emitted, [])

    def test_directory_change_invalidates_review(self):
        self.panel._show_plan(AgentAction("shell", command="run python check.py"))
        self.session.shell.ctx.cwd = Path.cwd().parent
        self.panel.approve()
        self.assertEqual(self.emitted, [])
        self.assertTrue(self.panel.task.stopped)

    def test_tab_switch_keeps_original_execution_session(self):
        self.session.input = Mock()
        self.session.run_command = Mock(return_value=True)
        other = Mock()
        window = SimpleNamespace(orbit=self.panel, current_session=lambda: other)
        MainWindow._run_orbit_action(window, AgentAction("shell", command="files"))
        self.session.run_command.assert_called_once_with(approval_granted=False)
        other.run_command.assert_not_called()

    def test_result_schedules_continuation_without_unlocking_input(self):
        self.panel._show_plan(AgentAction("shell", command="files"))
        self.panel.show_execution_result("files", SimpleNamespace(success=True, output="main.py"))
        self.assertTrue(self.panel.continue_timer.isActive())
        self.assertFalse(self.panel.input.isEnabled())
        self.assertEqual(self.panel.task.observations[0]["output"], "main.py")

    def test_command_exception_returns_a_failure_result(self):
        shell = Mock()
        shell.execute_line.side_effect = RuntimeError("command error")
        worker = CommandWorker(shell, "files")
        results = []
        worker.result_ready.connect(results.append)
        worker.run()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("command error", results[0].output)
