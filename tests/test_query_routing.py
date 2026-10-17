"""Routing contracts and held-out queries, without network or real credentials."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from ai.actions import AgentAction, FileWrite
from ai.intent_model import local_encoder
from ai.modes import OrbitMode, default_modes, estimated_tokens
from ai.prompt_builder import build_conversation_prompt
from ai.provider_runtime import ProviderRuntime
from ai.query_intent import QUERY_EXAMPLES, QueryIntent, classify_query
from ai.safety import SafetyPolicy
from test_ai_providers import make_config, make_planner


def planner_for_test(**kwargs):
    planner = make_planner(make_config(ai_provider="gemini", gemini_api_key="test", **kwargs))
    planner.provider_runtime = ProviderRuntime()
    return planner


class ConversationRoutingTests(unittest.TestCase):
    def test_confident_conversation_skips_command_and_workspace_matching(self):
        planner = planner_for_test()
        planner.intent_extractor.extract = Mock(side_effect=AssertionError("command extraction"))
        planner._fallback_plan = Mock(side_effect=AssertionError("workspace routing"))
        planner._call_provider = Mock(return_value='{"action":"respond","message":"A useful explanation."}')
        with patch("ai.llm.classify_query", return_value=QueryIntent("conversation", .8, .3)):
            action = planner.plan("Explain an unfamiliar topic")
        self.assertEqual(action, AgentAction("respond", "A useful explanation."))
        planner._call_provider.assert_called_once()

    def test_unknown_and_misclassified_knowledge_queries_get_small_prompt(self):
        # Even an incorrect workspace prediction must not force full planning.
        for route in (QueryIntent(), QueryIntent("workspace", .95, .3)):
            with self.subTest(route=route.kind):
                planner = planner_for_test()
                planner._fallback_plan = Mock(side_effect=AssertionError("premature inspection"))
                planner._call_provider = Mock(return_value='{"action":"respond","message":"Here is the answer."}')
                with patch("ai.llm.classify_query", return_value=route):
                    action = planner.plan("Explain a project management methodology")
                self.assertEqual(action.message, "Here is the answer.")
                prompt = planner._call_provider.call_args.args[1]
                self.assertNotIn("Available Commands & Aliases", prompt)
                self.assertNotIn("Runtime context", prompt)
                planner._call_provider.assert_called_once()

    def test_missing_encoder_still_answers_unknown_question_without_catalog(self):
        with patch("ai.query_intent._query_index", return_value=None):
            self.assertEqual(classify_query("An unfamiliar question"), QueryIntent())
            planner = planner_for_test()
            planner._call_provider = Mock(return_value='{"action":"respond","message":"Answer."}')
            with patch("ai.semantic_intent._index", return_value=None):
                self.assertEqual(planner.plan("What makes distant galaxies appear red?").message, "Answer.")
            self.assertNotIn("Available Commands & Aliases", planner._call_provider.call_args.args[1])
            planner._call_provider.assert_called_once()

    def test_classifier_failures_and_long_requests_abstain_without_truncation(self):
        with patch("ai.query_intent._query_index", side_effect=RuntimeError("model unavailable")):
            self.assertEqual(classify_query("Explain a topic"), QueryIntent())
        with patch("ai.query_intent._query_index", side_effect=AssertionError("model called")):
            self.assertEqual(classify_query("Tell me " + "x" * 3000 + " but do not execute"), QueryIntent())

    def test_explicit_commands_do_not_load_router_or_provider(self):
        planner = planner_for_test()
        with patch("ai.llm.classify_query", side_effect=AssertionError("router loaded")), patch.object(
            planner, "_call_provider", side_effect=AssertionError("provider called")
        ):
            for text in ("files", "/cmd files"):
                self.assertEqual(planner.plan(text).command, "files")

    def test_handoff_discards_proposed_effects_and_replans_with_same_task_budget(self):
        planner = planner_for_test(orbit_mode=replace(OrbitMode(), max_steps=1))
        planner._call_provider = Mock(side_effect=[
            json.dumps({"action": "shell", "command": "delete confirm important.txt"}),
            json.dumps({"action": "shell", "command": "run python check.py", "message": "Verify project"}),
        ])
        action = planner.plan("Help me verify this project")
        self.assertEqual(action.command, "run python check.py")
        self.assertTrue(SafetyPolicy().check_shell_command(action.command).requires_approval)
        self.assertEqual(planner._planning_calls, 1)
        self.assertEqual(planner._call_provider.call_count, 2)
        prompts = [call.args[1] for call in planner._call_provider.call_args_list]
        self.assertNotIn("Available Commands & Aliases", prompts[0])
        self.assertIn("Available Commands & Aliases", prompts[1])
        self.assertNotIn("delete confirm important.txt", prompts[1])

    def test_workspace_handoff_reads_only_after_model_requests_workspace_reasoning(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            (root / "README.md").write_text("Unique project evidence.", encoding="utf-8")
            planner = planner_for_test(workspace_root=root)
            prompts = []

            def provider(_provider, prompt, **kwargs):
                prompts.append(prompt)
                if len(prompts) == 1:
                    self.assertNotIn("Unique project evidence", prompt)
                    self.assertEqual(planner._inspection_passes, 0)
                    return '{"action":"inspect","paths":[],"message":""}'
                self.assertIn("Unique project evidence", prompt)
                return '{"action":"respond","message":"Project explained."}'

            planner._call_provider = provider
            self.assertEqual(planner.plan("Explain README.md").message, "Project explained.")
            self.assertEqual(len(prompts), 2)
            self.assertEqual(planner._planning_calls, 1)

    def test_chat_response_cannot_smuggle_commands_files_or_continuation(self):
        planner = planner_for_test()
        planner._request_model_action = Mock(return_value=(
            AgentAction("respond", "Answer", command="files", files=[FileWrite("bad.py", "bad")],
                        paths=["."], continue_after_result=True), [], "gemini"))
        with patch("ai.llm.classify_query", return_value=QueryIntent("conversation", .8, .3)):
            self.assertEqual(planner.plan("A general question"), AgentAction("respond", "Answer"))

    def test_provider_error_never_retries_through_heavier_planner(self):
        planner = planner_for_test()
        planner._fallback_plan = Mock(side_effect=AssertionError("workspace routing"))
        planner._call_provider = Mock(side_effect=RuntimeError("provider unavailable"))
        with patch("ai.llm.classify_query", return_value=QueryIntent("conversation", .8, .3)):
            action = planner.plan("A general question")
        self.assertEqual(action.action, "respond")
        self.assertIn("temporarily unavailable", action.message)
        planner._call_provider.assert_called_once()

    def test_conversation_context_is_bounded_and_never_reads_terminal_or_native_state(self):
        for mode in default_modes():
            with self.subTest(mode=mode.name):
                planner = planner_for_test(orbit_mode=mode)
                planner.current_dir_provider = Mock(side_effect=AssertionError("directory read"))
                planner.native_context_provider = Mock(side_effect=AssertionError("native context"))
                planner.last_output_provider = Mock(side_effect=AssertionError("terminal read"))
                rows = [{"role": role, "content": f"turn-{i}: " + "long history " * 500}
                        for i in range(20) for role in ("user", "assistant")]
                planner.memory.load = lambda: rows
                prompt = build_conversation_prompt(planner, "Explain the next concept")
                self.assertTrue(prompt.endswith("Explain the next concept"))
                self.assertIn("turn-19", prompt)
                self.assertNotIn("turn-0:", prompt)
                self.assertNotIn("Available Commands & Aliases", prompt)
                self.assertIn(f"Hard output ceiling: {mode.output_tokens}", prompt)
                self.assertLessEqual(estimated_tokens(prompt), mode.prompt_tokens)
                self.assertEqual(len(rows), 40)


# Intentionally separate from the routing examples; new topics, technical
# explanations and Hinglish must all answer without loading the large prompt.
HELD_OUT_QUESTIONS = (
    "Who is Ada Lovelace?", "What is quantum entanglement?",
    "Why do leaves change colour?", "How do bees communicate?",
    "What is an API?", "How does DNS resolve a domain name?",
    "What is a binary search tree?", "What are environment variables?",
    "Explain the meaning of RAM usage", "How does Git track file changes?",
    "What is a command alias?", "What does a screenshot capture?",
    "Tell me the difference between RAM and ROM", "What is RAM?",
    "How does Windows memory management work?", "How do I make a website?",
    "Explain a project management methodology", "Explain project management",
    "Explain the history of operating systems", "Give advice on structuring a software project",
    "What do you know about Shakespeare?", "Who is the founder of Microsoft?",
    "Mujhe black holes samjhao", "History of Delhi batao", "Python kya hai?",
    "Give me a Python example for fibonacci", "How do I delete a folder?",
    "What does git status mean?", "How can I improve my spoken English?",
    "Tell me about environment variables", "Tell me about Git branches",
    "What's an environment variable?", "Could you tell me more about command aliases?",
    "Give me information about IP addresses", "What exactly are environment variables?",
    "Tell me about PC specifications", "Give me an overview of memory management",
)


@unittest.skipUnless(local_encoder() is not None, "Local MiniLM assets/runtime unavailable")
class RealQueryRoutingTests(unittest.TestCase):
    def test_unseen_questions_use_one_small_answer_request_and_no_inspection(self):
        examples = {text for group in QUERY_EXAMPLES.values() for text in group}
        self.assertFalse(examples.intersection(HELD_OUT_QUESTIONS))
        planner = planner_for_test()
        for question in HELD_OUT_QUESTIONS:
            with self.subTest(question=question):
                planner._call_provider = Mock(return_value='{"action":"respond","message":"Knowledge answer."}')
                with patch.object(planner, "_fallback_plan", side_effect=AssertionError("workspace routing")):
                    self.assertEqual(planner.plan(question).message, "Knowledge answer.")
                planner._call_provider.assert_called_once()
                prompt = planner._call_provider.call_args.args[1]
                self.assertNotIn("Available Commands & Aliases", prompt)
                self.assertLess(estimated_tokens(prompt), 600)
                self.assertEqual(planner._inspection_passes, 0)

    def test_semantic_conversation_bypasses_both_command_extractors(self):
        question = "Why do leaves change colour?"
        self.assertEqual(classify_query(question).kind, "conversation")
        planner = planner_for_test()
        planner._call_provider = Mock(return_value='{"action":"respond","message":"An explanation."}')
        with patch.object(planner.intent_extractor, "extract", side_effect=AssertionError("command matching")):
            self.assertEqual(planner.plan(question).message, "An explanation.")
