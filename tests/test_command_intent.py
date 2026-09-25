import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from ai.actions import AgentAction
from ai.command_intent import (
    CommandCandidate, Extraction, IntentRule, RuleIntentExtractor, valid_candidate,
)
from ai.llm import AgentPlanner
from ai.safety import SafetyPolicy
from core.base import BaseCommand, CommandResult
from core.parser import CommandParser
from core.registry import CommandRegistry
from core.shell import Shell
from test_ai_providers import make_config


LISTING_CASES = {
    "show me folders": "folders",
    "SHOW ME FOLDERS!": "folders",
    "Could you please show me all the folders?": "folders",
    "show me only folders here": "folders",
    "list directories right here": "folders",
    "display all the directories inside the current folder": "folders",
    "show folders in src": "folders src",
    "show me all the folders inside the directory src": "folders src",
    'list only directories in "My  Reports"': 'folders "My  Reports"',
    'show folders in "D:\\Do Not Delete"': 'folders "D:\\Do Not Delete"',
    "show folders in .": "folders .",
    "show folders in ..": "folders ..",
    "show me all the files": "files",
    "show files here": "files",
    "display files inside this directory": "files",
    "show me files and folders": "files",
    "list folders and files here": "files",
    "display files and directories in src": "files src",
    "list directories and files inside src": "files src",
    "mujhe folders dikhao": "folders",
    "mujhe saare folders dikha do": "folders",
    "mujhe sirf directories dikhao": "folders",
    "is folder ke folders dikhao": "folders",
    "is folder ki files dikhao": "files",
    '"is" folder ke folders dikhao': "folders is",
    "./is ke folders dikhao": "folders ./is",
    "current directory ke folders batao": "folders",
    "mujhe current folder ke saare directories dikhao": "folders",
    "src ke folders dikhao": "folders src",
    "src folder ki directories dikha do": "folders src",
    'mujhe "My Reports" ke sirf folders dikhao!': 'folders "My Reports"',
    "mujhe saari files dikhao": "files",
    "is directory ki files dikha do": "files",
    "src ke files dikhao": "files src",
    "mujhe src ki files dikhao": "files src",
}


class CommandIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Shell().registry
        cls.extractor = RuleIntentExtractor(cls.registry.all_names(), metadata=cls.registry.list_metadata())

    def test_english_requests_map_to_complete_commands(self):
        cases = {
            "Where are we?": "where",
            "Could you please show my current directory?": "where",
            "Hey Orbit, please list the files in this folder.": "files",
            "I would like you to show me the files": "files",
            "List all directories": "folders",
            "Show files in src": "files src",
            "Please go to the folder src": "cd src",
            "Change directory to ../docs": "cd ../docs",
            "Go up one level": "up",
            "Go to my home folder": "home",
            "Clear the terminal, please": "clear",
            "Show running processes": "processes",
            "Show system information": "system",
            "Show RAM usage": "memory",
            "Show free disk space": "disk",
            "List available drives": "drives",
            "What is my IP address?": "ip",
            "Show network information": "network",
            "Show active connections": "netstat",
            "Show command history": "history",
            "What time is it?": "now",
            "What is today's date?": "today",
            "Show my username": "me",
            "Show computer name": "pc",
            "Show system uptime": "uptime",
            "Show installed plugins": "plugins",
            "Show RiftShell version": "version",
            "Show available commands": "help",
            "Show the directory tree": "tree",
            "Show git status": "gstatus",
            "Git branches": "gbranch",
            "Show the git diff": "gdiff",
            "Git log": "glog",
            "Git remotes": "gremote",
            "Create a folder named reports": "makefolder reports",
            "Make an empty file notes.txt": "makefile notes.txt",
            "Delete the file notes.txt": "delete confirm notes.txt",
            "Remove notes.txt": "delete confirm notes.txt",
            "Open notes.txt": "open notes.txt",
            "Copy notes.txt to backup.txt": "duplicate notes.txt backup.txt",
            "Move file notes.txt into Archive": "shift notes.txt Archive",
            "Rename notes.txt as saved.txt": "rename notes.txt saved.txt",
            "Show the first 10 lines of notes.txt": "head notes.txt 10",
            "Display last 5 lines from notes.txt": "tail notes.txt 5",
            "Ping example.com": "ping example.com",
        }
        for text, command in cases.items():
            with self.subTest(text=text):
                result = self.extractor.extract(text)
                self.assertEqual(result.status, "matched")
                self.assertEqual(result.match.command, command)

    def test_hinglish_requests(self):
        for text, command in {
            "files dikhao": "files", "saari files dikhao": "files",
            "mujhe files dikhao": "files", "current folder ki files dikhao": "files",
            "hum kis folder mein hain": "where", "current folder batao": "where",
            "sirf folders dikhao": "folders", "src mein jao": "cd src",
            "src folder me jao": "cd src", "src ki files dikhao": "files src",
            "parent folder mein jao": "up", "home folder me jao": "home",
            "terminal clear karo": "clear", "git status dikhao": "gstatus",
            "ram usage batao": "memory", "system info dikha do": "system",
            "reports folder banao": "makefolder reports",
            "notes.txt khali file banao": "makefile notes.txt",
            "notes.txt file delete karo": "delete confirm notes.txt",
            "notes.txt ko backup.txt copy karo": "duplicate notes.txt backup.txt",
        }.items():
            with self.subTest(text=text):
                self.assertEqual(self.extractor.extract(text).match.command, command)

    def test_listing_variants_preserve_target_and_folder_filter(self):
        for text, expected in LISTING_CASES.items():
            with self.subTest(text=text):
                result = self.extractor.extract(text)
                self.assertEqual(result.status, "matched")
                self.assertEqual(result.match.command, expected)

    def test_listing_expansion_does_not_discard_constraints_or_extra_actions(self):
        for text in (
            "show me folders", "show me all the folders", "show folders in src",
            "show files and folders here", "mujhe folders dikhao", "src ke folders dikhao",
        ):
            for prefix in ("don't ", "do not ", "explain how to ", "if possible "):
                with self.subTest(text=prefix + text):
                    self.assertIsNone(self.extractor.extract(prefix + text).match)
            for suffix in (" and delete notes.txt", " but don't execute", " mat karo", " nahi",
                           "; delete confirm notes.txt", " recursively", " sorted by size"):
                with self.subTest(text=text + suffix):
                    self.assertIsNone(self.extractor.extract(text + suffix).match)
        for text in (
            "show folders in it", "show folders in the directory", "show folders in My Reports",
            'show folders in "src; delete confirm notes.txt"', "show folders in $HOME",
            "show folders in *.txt", "show folders in src.", "show folders in src then run tests",
            "show hidden folders here", "show only files here", "show files and delete folders",
            "mujhe folders nahi dikhao", "is folder ke folders mat dikhao",
            "is ke folders dikhao",
            "show me folders\nand files", "show folders in src and docs",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.extractor.extract(text).match)

    def test_chat_negation_explanations_and_incomplete_requests_abstain(self):
        cases = (
            "Hello, how are you?", "I feel sad today", "history of India",
            "Now tell me who Elon Musk is", "Show me how files work",
            "What does delete do?", "Delete command kya karti hai?",
            "Can you explain how to list files?", "How do I go to src?",
            "Should I delete the file notes.txt?", "I might create a folder reports",
            "Don't delete the file notes.txt", "Do not list files", "Never clear the terminal",
            "notes.txt file delete mat karo", "files nahi dikhao", "files dikhao mat",
            "List files and then delete notes.txt", "Show files but don't delete anything",
            "If it exists delete the file notes.txt", "Go to src then run tests",
            "Create a file app.py with a calculator", "Write code in app.py",
            "app.py mein code likho", "Read notes.txt", "Explain README.md",
            'Say "list files"', '"list files"', "The user said list files",
            "go to it", "delete the file that", "create file something",
            "ping me", "ping us", "go to him",
            "delete my doubts", "move on to something else", "open your mind",
            "show files in the folder", "create a folder", "rename it to notes.txt",
            "delete the file notes.txt please don't", "list files\nthen delete notes.txt",
            "show files in src; delete confirm notes.txt", "create file a.txt > b.txt",
            'create file "a.txt; delete confirm b.txt"', "go to $HOME", "go to %TEMP%",
            "delete the file *.txt", "delete the file foo?", "go to src.",
            "copy a.txt to b.txt and explain it", "files dikhao aur delete karo",
            "x" * 5000,
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(self.extractor.extract(text).status, "no_match")

    def test_paths_keep_case_spaces_and_backslashes_and_round_trip(self):
        text = 'Copy "D:\\My  Work\\Report.TXT" to "D:\\Archive\\Report.TXT"'
        candidate = self.extractor.extract(text).match
        self.assertEqual(candidate.arguments, (r"D:\My  Work\Report.TXT", r"D:\Archive\Report.TXT"))
        parsed = CommandParser().parse(candidate.command)
        self.assertEqual(len(parsed.args), 2)
        self.assertTrue(valid_candidate(candidate, self.registry.all_names()))
        # Literal paths can contain words that would be negation in prose.
        self.assertEqual(self.extractor.extract('Go to "D:\\Do Not Delete"').match.arguments,
                         (r"D:\Do Not Delete",))

    def test_negation_and_additional_instructions_are_never_truncated(self):
        for request in ("list files", "create folder reports", "delete file notes.txt", "copy a.txt to b.txt"):
            for prefix in ("don't ", "do not ", "never ", "why would I ", "how do I ", "if possible don't "):
                with self.subTest(text=prefix + request):
                    self.assertIsNone(self.extractor.extract(prefix + request).match)
            for suffix in (" and run tests", " but don't execute", " mat karo", " nahi", " if it exists", " or maybe not"):
                with self.subTest(text=request + suffix):
                    self.assertIsNone(self.extractor.extract(request + suffix).match)

    def test_unavailable_commands_and_conflicts_do_not_execute(self):
        self.assertEqual(RuleIntentExtractor(["where"]).extract("list files").status, "no_match")
        rules = (
            IntentRule("one", "files", "Files", phrases=("show entries",)),
            IntentRule("two", "folders", "Folders", phrases=("show entries",)),
        )
        result = RuleIntentExtractor(["files", "folders"], rules=rules).extract("show entries")
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.match)

    def test_plugins_opt_in_using_registry_metadata(self):
        class HealthCommand(BaseCommand):
            name = "health"
            def execute(self, ctx, args):
                return CommandResult(output="ok")
        registry = CommandRegistry()
        registry.register(HealthCommand(), extra={"orbit_intents": (
            IntentRule("health_check", "health", "Checking health.", phrases=("check service health",)),
            IntentRule("wrong_owner", "files", "Wrong.", phrases=("list secrets",)),
        )})
        extractor = RuleIntentExtractor(registry.all_names(), metadata=registry.list_metadata())
        self.assertEqual(extractor.extract("Please check service health").match.command, "health")
        self.assertEqual(extractor.extract("list secrets").status, "no_match")

    def test_extraction_does_not_bypass_approval_policy(self):
        policy = SafetyPolicy()
        for text in ("Delete file notes.txt", "Move notes.txt to archive.txt", "Rename notes.txt to old.txt"):
            with self.subTest(text=text):
                self.assertTrue(policy.check_shell_command(self.extractor.extract(text).match.command).requires_approval)


class PlannerIntentIntegrationTests(unittest.TestCase):
    def planner(self, **overrides):
        shell = Shell()
        return AgentPlanner(make_config(ai_provider="gemini", gemini_api_key="test-key", **overrides),
                            shell.registry.all_names(), shell.registry.catalog_entries(),
                            command_metadata=shell.registry.list_metadata())

    def test_clear_requests_do_not_initialize_or_call_a_provider(self):
        planner = self.planner()
        with patch.object(planner, "_ensure_provider", side_effect=AssertionError("provider initialized")), \
             patch.object(planner, "_request_model_action", side_effect=AssertionError("model called")):
            for prompt, expected in (("Please list files", "files"), ("files dikhao", "files"),
                                     ("where", "where"), ("/cmd files", "files"),
                                     ("Delete file notes.txt", "delete confirm notes.txt")):
                with self.subTest(prompt=prompt):
                    action = planner.plan(prompt)
                    self.assertEqual(action.command, expected)
                    self.assertFalse(action.continue_after_result)
        self.assertIsNone(planner._gemini)
        self.assertIsNone(planner._groq)

    def test_listing_variants_skip_provider_and_result_continuation(self):
        planner = self.planner()
        with patch.object(planner, "_ensure_provider", side_effect=AssertionError("provider initialized")), \
             patch.object(planner, "_request_model_action", side_effect=AssertionError("model called")):
            for prompt, expected in LISTING_CASES.items():
                with self.subTest(prompt=prompt):
                    action = planner.plan(prompt)
                    self.assertEqual(action.action, "shell")
                    self.assertEqual(action.command, expected)
                    self.assertFalse(action.continue_after_result)

    def test_no_match_keeps_normal_reasoning_without_an_extra_model_call(self):
        planner = self.planner()
        for text in ("Explain dependency injection", "List files and then check git status",
                     "files mat dikhao", "What does delete do?", "Open your mind"):
            with self.subTest(text=text), patch.object(planner, "_request_model_action", return_value=(
                AgentAction("respond", "Reasoned answer"), [], "gemini",
            )) as model:
                action = planner.plan(text)
                self.assertEqual(action.message, "Reasoned answer")
                model.assert_called_once()
                self.assertIn(text, model.call_args.args[0])
                self.assertNotIn("Unconfirmed command candidates", model.call_args.args[0])

    def test_sdk_setup_is_lazy_and_only_the_selected_provider_is_initialized(self):
        with patch.dict("sys.modules", {"groq": SimpleNamespace(Groq=unittest.mock.Mock())}):
            import groq
            shell = Shell()
            planner = AgentPlanner(make_config(ai_provider="groq", groq_api_key="test-key"),
                                   shell.registry.all_names(), shell.registry.catalog_entries())
            planner.plan("list files")
            groq.Groq.assert_not_called()
            planner._ensure_provider("groq")
            planner._ensure_provider("groq")
            groq.Groq.assert_called_once_with(api_key="test-key", timeout=30, max_retries=0)
            self.assertIsNone(planner._gemini)

    def test_offline_miss_does_not_use_permissive_legacy_command_regex(self):
        shell = Shell()
        planner = AgentPlanner(make_config(), shell.registry.all_names(), shell.registry.catalog_entries())
        for text in ("delete my doubts", "go to src then delete files", "don't take a screenshot"):
            with self.subTest(text=text):
                self.assertEqual(planner.plan(text).action, "respond")

    def test_candidate_adapters_are_validated_and_ml_suggestions_are_not_autoexecuted(self):
        planner = self.planner()
        for candidate in (
            CommandCandidate("bad", "files;delete", (), "bad"),
            CommandCandidate("bad", "files", ("x; delete confirm y",), "bad"),
            CommandCandidate("guess", "files", (), "guess", source="ml", confidence=0.99),
        ):
            with self.subTest(candidate=candidate):
                planner.intent_extractor = type("Adapter", (), {"extract": lambda _, text: Extraction("matched", (candidate,))})()
                with patch.object(planner, "_request_model_action", return_value=(AgentAction("respond", "Thinking"), [], "gemini")) as model:
                    self.assertEqual(planner.plan("check something").action, "respond")
                    model.assert_called_once()
                    if candidate.source == "ml":
                        self.assertIn("Unconfirmed command candidates", model.call_args.args[0])

    def test_ambiguous_rules_give_orbit_hints_instead_of_choosing_by_order(self):
        planner = self.planner()
        planner.intent_extractor = RuleIntentExtractor(planner.command_names, rules=(
            IntentRule("one", "files", "Files", phrases=("show entries",)),
            IntentRule("two", "folders", "Folders", phrases=("show entries",)),
        ))
        with patch.object(planner, "_request_model_action", return_value=(
            AgentAction("respond", "Files and folders, or folders only?"), [], "gemini",
        )) as model:
            self.assertEqual(planner.plan("show entries").action, "respond")
            model.assert_called_once()
            self.assertIn('"command": "files"', model.call_args.args[0])
            self.assertIn('"command": "folders"', model.call_args.args[0])

    def test_explicit_offline_screenshot_still_works(self):
        shell = Shell()
        planner = AgentPlanner(make_config(), shell.registry.all_names(), shell.registry.catalog_entries())
        self.assertEqual(planner.plan("take a screenshot").action, "screenshot")

    def test_extracted_commands_execute_against_real_shell_in_isolated_workspace(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root = Path(temp)
            shell = Shell(start_dir=root, workspace_root=root, allow_outside_workspace=False)
            planner = AgentPlanner(make_config(workspace_root=root), shell.registry.all_names(), shell.registry.catalog_entries())
            for text in ('Create a folder named "My Reports"', 'Create an empty file "My Reports/Notes.TXT"'):
                result = shell.execute_line(planner.plan(text).command)
                self.assertTrue(result.success, result.output)
            self.assertTrue((root / "My Reports" / "Notes.TXT").is_file())
            action = planner.plan('List files in "My Reports"')
            result = shell.execute_line(action.command)
            self.assertTrue(result.success, result.output)
            self.assertIn("Notes.TXT", result.output)
            (root / "My Reports" / "Nested Folder").mkdir()
            for text in ('show me folders', 'show folders in "My Reports"',
                         'mujhe "My Reports" ke folders dikhao'):
                result = shell.execute_line(planner.plan(text).command)
                self.assertTrue(result.success, result.output)
                self.assertIn("My Reports" if text == "show me folders" else "Nested Folder", result.output)
                self.assertNotIn("Notes.TXT", result.output)
            result = shell.execute_line(planner.plan('show folders in "../outside workspace"').command)
            self.assertFalse(result.success)
            self.assertIn("Blocked path outside", result.output)
            for text in (
                'Copy "My Reports/Notes.TXT" to "My Reports/Copy.TXT"',
                'Rename "My Reports/Copy.TXT" to "Renamed Copy.TXT"',
                'Move "My Reports/Renamed Copy.TXT" to "My Reports/Final Copy.TXT"',
            ):
                result = shell.execute_line(planner.plan(text).command)
                self.assertTrue(result.success, result.output)
            self.assertTrue((root / "My Reports" / "Final Copy.TXT").is_file())
            # Quoting must not weaken workspace containment.
            result = shell.execute_line(planner.plan('Go to "../outside workspace"').command)
            self.assertFalse(result.success)
            self.assertIn("Blocked path outside", result.output)


if __name__ == "__main__":
    unittest.main()
