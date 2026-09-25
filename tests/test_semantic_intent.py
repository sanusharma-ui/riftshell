import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai.actions import AgentAction
from ai.command_intent import CommandCandidate, Extraction, valid_candidate
from ai.intent_model import local_encoder
from ai.llm import AgentPlanner
from ai.safety import SafetyPolicy
from ai.semantic_catalog import SEMANTIC_INTENTS, SemanticIntent
from ai.semantic_intent import HybridIntentExtractor, SemanticIntentExtractor, bind, valid_spec
from core.registry import CommandMetadata
from core.shell import Shell
from semantic_cases import NEGATIVES, PARAPHRASES
from test_ai_providers import make_config


class SemanticContractTests(unittest.TestCase):
    def test_every_registered_command_has_a_reviewed_schema_or_equivalent(self):
        commands = {meta.name for meta in Shell().registry.list_metadata()}
        covered = {item.command for item in SEMANTIC_INTENTS} | {"goto"}
        self.assertEqual(commands - covered, set())

    def test_local_model_missing_keeps_existing_rules_and_silent_misses(self):
        shell = Shell()
        extractor = HybridIntentExtractor(shell.registry.all_names())
        with patch("ai.semantic_intent._index", return_value=None):
            self.assertEqual(extractor.extract("show me folders").match.command, "folders")
            self.assertEqual(extractor.extract("Which subdirectories exist here?").status, "no_match")

    def test_exact_matches_and_noncommands_never_load_the_local_model(self):
        extractor = HybridIntentExtractor(Shell().registry.all_names())
        with patch("ai.semantic_intent._index", side_effect=AssertionError("model loaded")):
            self.assertEqual(extractor.extract("show me folders").match.command, "folders")
            for text in ("Hello", "Explain recursion", "don't erase a.txt", "x" * 5000):
                self.assertEqual(extractor.extract(text).status, "no_match")

    def test_untrusted_adapter_cannot_claim_local_semantic_execution(self):
        shell = Shell()
        planner = AgentPlanner(make_config(gemini_api_key="test"), shell.registry.all_names(), [])
        candidate = CommandCandidate("guess", "files", (), "guess", source="local_semantic", confidence=0.99)
        planner.intent_extractor = SimpleNamespace(extract=lambda text: Extraction("matched", (candidate,)))
        with patch.object(planner, "_request_model_action", return_value=(AgentAction("respond", "Thinking"), [], "gemini")) as model:
            self.assertEqual(planner.plan("check something").action, "respond")
            model.assert_called_once()

    def test_schema_bindings_preserve_literal_values_and_argument_roles(self):
        intents = {item.key: item for item in SEMANTIC_INTENTS}
        result = bind(intents["move_path"], 'Relocate "D:\\My  Work\\A.txt" into "D:\\Archive"')
        self.assertEqual(result[0], (r"D:\My  Work\A.txt", r"D:\Archive"))
        self.assertIsNone(bind(intents["unzip_here"], "Unpack a.zip into Archive"))
        self.assertIsNone(bind(intents["delete_path"], "Erase my worries"))
        self.assertIsNone(bind(intents["search_names"], "Find files containing some text"))
        self.assertIsNone(bind(intents["random_range"], "Pick a number between 9 and 2"))

    def test_semantic_ambiguity_and_low_scores_do_not_execute(self):
        extractor = SemanticIntentExtractor(["files", "folders"])
        for scores, status in (((0.8, 0.79), "ambiguous"), ((0.4, 0.3), "no_match")):
            candidates = [CommandCandidate(name, name, (), name, source="local_semantic", confidence=score)
                          for name, score in zip(("files", "folders"), scores)]
            with patch.object(extractor, "rank", return_value=candidates):
                result = extractor.extract("show entries")
                self.assertEqual(result.status, status)
                self.assertIsNone(result.match)

    def test_plugins_require_explicit_owning_semantic_schema(self):
        spec = SemanticIntent("health", "health", ("Check service health",))
        wrong = SemanticIntent("wrong", "files", ("Show private files",))
        metadata = [CommandMetadata("health", description="Delete all files", source="plugin", plugin="health",
                                    extra={"orbit_semantics": (spec, wrong)})]
        extractor = SemanticIntentExtractor(["health"], metadata)
        self.assertEqual(extractor.intents, (spec,))
        self.assertEqual(SemanticIntentExtractor(["health"], [CommandMetadata("health", description="Check health")]).intents, ())

    def test_malformed_plugin_schemas_are_ignored(self):
        malformed = (
            SemanticIntent("empty", "health", ()),
            SemanticIntent("wrong_arity", "health", ("Check service",), "one"),
            SemanticIntent("bad_index", "health", ("Check service",), arguments=("{3}",)),
            SemanticIntent("bad_expansion", "health", ("Check service",), "one", ("path",), ("*0",)),
            SemanticIntent("unknown_kind", "health", ("Check service",), "one", ("anything",), ("{0}",)),
        )
        for spec in SEMANTIC_INTENTS:
            self.assertTrue(valid_spec(spec), spec.key)
        for spec in malformed:
            self.assertFalse(valid_spec(spec))
        metadata = [CommandMetadata("health", extra={"orbit_semantics": malformed})]
        self.assertEqual(SemanticIntentExtractor(["health"], metadata).intents, ())


class ShellLiteralArgumentTests(unittest.TestCase):
    def test_text_values_and_arithmetic_reach_commands_without_grouping_quotes(self):
        shell = Shell()
        for command, expected in (
            ('echo "hello  world"', "hello  world"),
            ('calc "2 + 3"', "5"),
            ('base64 encode "hello world"', "aGVsbG8gd29ybGQ="),
            ('setvar GREETING "hello  world"', "GREETING=hello  world"),
        ):
            with self.subTest(command=command):
                result = shell.execute_line(command)
                self.assertTrue(result.success, result.output)
                self.assertEqual(result.output, expected)
        result = shell.execute_line('hash text "hello  world"')
        self.assertIn(hashlib.sha256(b"hello  world").hexdigest(), result.output)

    def test_git_receives_a_single_literal_message_without_running_git(self):
        shell = Shell()
        with patch("plugins.git.plugin.subprocess.run", return_value=SimpleNamespace(stdout="ok", stderr="", returncode=0)) as run:
            # The loader can import plugins under its own module name; patching
            # subprocess.run intercepts the shared module either way.
            shell.execute_line('gcommit -m "Fix  quoted text"')
        self.assertEqual(run.call_args.args[0], ["git", "commit", "-m", "Fix  quoted text"])


@unittest.skipUnless(local_encoder() is not None, "Run python scripts/setup_intent_model.py for real-model evaluation")
class RealSemanticModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = Shell()
        cls.extractor = HybridIntentExtractor(cls.shell.registry.all_names(), metadata=cls.shell.registry.list_metadata())

    def test_english_paraphrases_across_command_catalog(self):
        for text, expected in PARAPHRASES.items():
            with self.subTest(text=text):
                result = self.extractor.extract(text)
                self.assertIsNotNone(result.match, [(c.command, c.confidence) for c in result.candidates])
                self.assertEqual(result.match.command, expected)
                self.assertTrue(valid_candidate(result.match, self.shell.registry.all_names()))

    def test_negative_requests_do_not_autoexecute(self):
        for text in NEGATIVES:
            with self.subTest(text=text):
                self.assertIsNone(self.extractor.extract(text).match)

    def test_negation_and_extra_instructions_around_every_paraphrase_abstain(self):
        for text in PARAPHRASES:
            for modified in ("Don't " + text, "Explain how to " + text,
                             text + " but do not execute", text + " and erase notes.txt",
                             text + " if it exists", "The user said " + text):
                with self.subTest(text=modified):
                    self.assertIsNone(self.extractor.extract(modified).match)

    def test_planner_routes_paraphrases_without_cloud_calls(self):
        planner = AgentPlanner(make_config(gemini_api_key="test"), self.shell.registry.all_names(),
                               self.shell.registry.catalog_entries(), command_metadata=self.shell.registry.list_metadata())
        with patch.object(planner, "_ensure_provider", side_effect=AssertionError("provider initialized")), \
             patch.object(planner, "_request_model_action", side_effect=AssertionError("cloud called")):
            for text, expected in PARAPHRASES.items():
                with self.subTest(text=text):
                    action = planner.plan(text)
                    self.assertEqual(action.command, expected)
                    self.assertFalse(action.continue_after_result)

    def test_risky_semantic_matches_keep_existing_approval_policy(self):
        for text in ('Erase the file notes.txt', 'Relocate notes.txt into Archive',
                     'Stop the process notepad.exe', 'Upload local Git commits to the remote repository',
                     'Execute the native command "python -c dangerous()"'):
            with self.subTest(text=text):
                candidate = self.extractor.extract(text).match
                self.assertIsNotNone(candidate)
                self.assertTrue(SafetyPolicy().check_shell_command(candidate.command).requires_approval)

    def test_real_filesystem_and_text_operations(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root = Path(temp)
            shell = Shell(start_dir=root, workspace_root=root, allow_outside_workspace=False)
            for text in ('Build a new directory called "My Reports"',
                         'Generate a blank file called "My Reports/notes.txt"',
                         'What subdirectories are inside "My Reports"',
                         'Compute "2 + 3"', 'Convert "hello world" to base64'):
                with self.subTest(text=text):
                    candidate = self.extractor.extract(text).match
                    self.assertIsNotNone(candidate)
                    result = shell.execute_line(candidate.command)
                    self.assertTrue(result.success, result.output)
            self.assertTrue((root / "My Reports" / "notes.txt").is_file())
            self.assertEqual(result.output, "aGVsbG8gd29ybGQ=")
            candidate = self.extractor.extract('Navigate into the directory "../outside workspace"').match
            self.assertIsNotNone(candidate)
            self.assertFalse(shell.execute_line(candidate.command).success)
