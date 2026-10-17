"""Provider finish-state regressions: chat content is not executable action JSON."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.actions import AgentAction
from ai.conversation import WORKSPACE_HANDOFF, conversation_action
from ai.modes import OutputBudgetError
from ai.provider_runtime import ProviderRuntime
from test_ai_providers import FakeGemini, FakeHTTPResponse, make_config, make_planner


QUESTION = "can you explain me the architecture of telephone"
ANSWER = "A telephone has a microphone, a signalling circuit, a network interface and a speaker."


def planner_for(provider="groq", **kwargs):
    planner = make_planner(make_config(ai_provider=provider, groq_api_key="test", gemini_api_key="test",
                                       groq_model="openai/gpt-oss-120b", **kwargs))
    planner.provider_runtime = ProviderRuntime()
    return planner


def groq_response(content, reason="length"):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(
        content=content, reasoning="Private model analysis must never be shown."))])


class ConversationOutputTests(unittest.TestCase):
    def test_groq_length_retains_answer_for_exact_reported_question(self):
        planner = planner_for()
        create = Mock(return_value=groq_response(ANSWER))
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with patch.object(planner, "_fallback_plan", side_effect=AssertionError("workspace route")):
            action = planner.plan(QUESTION)
        self.assertEqual(action.action, "respond")
        self.assertTrue(action.message.startswith(ANSWER))
        self.assertIn("reply stopped here", action.message)
        self.assertNotIn("output limit", action.message)
        self.assertNotIn("Private model analysis", action.message)
        self.assertEqual(action.command, "")
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["response_format"], {"type": "text"})
        self.assertEqual(create.call_args.kwargs["extra_body"], {
            "max_completion_tokens": 768, "reasoning_effort": "low", "include_reasoning": False})

    def test_complete_chat_answer_has_no_truncation_notice(self):
        planner = planner_for()
        planner._call_provider = Mock(return_value=ANSWER)
        action = planner.plan(QUESTION)
        self.assertEqual(action, AgentAction("respond", ANSWER))
        planner._call_provider.assert_called_once()
        self.assertTrue(planner._call_provider.call_args.kwargs["conversation"])

    def test_gemini_max_tokens_retains_visible_content_in_text_mode(self):
        planner = planner_for("gemini")
        planner._gemini = Mock()
        planner._gemini.generate_content.return_value = SimpleNamespace(
            text=ANSWER, candidates=[SimpleNamespace(finish_reason=2)])
        action = planner.plan(QUESTION)
        self.assertTrue(action.message.startswith(ANSWER))
        self.assertEqual(planner._gemini.generate_content.call_args.kwargs["generation_config"], {
            "response_mime_type": "text/plain", "max_output_tokens": 768})
        planner._gemini.generate_content.assert_called_once()

    def test_ollama_length_retains_visible_content_without_reasoning_or_json_mode(self):
        planner = planner_for("ollama", ollama_model="test")
        response = FakeHTTPResponse()
        response.body = json.dumps({"response": ANSWER, "thinking": "private thoughts", "done_reason": "length"}).encode()
        with patch("ai.llm.urllib.request.urlopen", return_value=response) as call:
            action = planner.plan(QUESTION)
        self.assertTrue(action.message.startswith(ANSWER))
        self.assertNotIn("private thoughts", action.message)
        payload = json.loads(call.call_args.args[0].data)
        self.assertNotIn("format", payload)
        self.assertEqual(payload["options"]["num_predict"], 768)
        call.assert_called_once()

    def test_empty_reasoning_exhaustion_uses_configured_fallback_with_same_cap(self):
        planner = planner_for("auto")
        create = Mock(return_value=groq_response(None))
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        planner._gemini = FakeGemini(ANSWER)
        self.assertEqual(planner.plan(QUESTION), AgentAction("respond", ANSWER))
        create.assert_called_once()
        self.assertEqual(planner._gemini.calls, 1)
        self.assertEqual(planner.mode.output_tokens, 768)

    def test_forced_provider_empty_answer_never_leaks_reasoning_or_loops(self):
        planner = planner_for()
        create = Mock(return_value=groq_response(None))
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        planner._gemini = FakeGemini()
        action = planner.plan(QUESTION)
        self.assertEqual(action.action, "respond")
        self.assertIn("without producing a readable answer", action.message)
        self.assertNotIn("Private model analysis", action.message)
        create.assert_called_once()
        self.assertEqual(planner._gemini.calls, 0)

    def test_truncated_effects_and_handoff_cannot_be_used_as_actions(self):
        for text in (
            '{"action":"shell","command":"delete confirm notes.txt"}',
            '{"action":"code_write","files":[{"path":"notes.txt","content":"bad"}]}',
            '{"action":"respond","message":"unfinished',
            WORKSPACE_HANDOFF, WORKSPACE_HANDOFF[:5],
        ):
            with self.subTest(text=text):
                self.assertIsNone(conversation_action(text, truncated=True))
                planner = planner_for()
                planner._call_provider = Mock(side_effect=OutputBudgetError("limit", partial_text=text))
                action = planner.plan(QUESTION)
                self.assertEqual(action.action, "respond")
                self.assertEqual(action.command, "")
                self.assertEqual(action.files, [])
                planner._call_provider.assert_called_once()

    def test_action_path_still_rejects_truncated_shell_and_writes(self):
        for payload in (
            {"action": "shell", "command": "files"},
            {"action": "code_write", "files": [{"path": "main.py", "content": "print('partial')"}]},
        ):
            planner = planner_for("auto")
            create = Mock(return_value=groq_response(json.dumps(payload)))
            planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            planner._gemini = FakeGemini()
            action, errors, _ = planner._request_model_action("Plan a workspace action")
            self.assertIsNone(action)
            self.assertIn("output limit", errors[0])
            self.assertEqual(planner._gemini.calls, 0)
            self.assertEqual(create.call_args.kwargs["response_format"], {"type": "json_object"})
            self.assertNotIn("reasoning_effort", create.call_args.kwargs["extra_body"])

    def test_existing_sdk_serializes_chat_settings_and_handles_length_response(self):
        import groq
        import httpx
        planner = planner_for()
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 1, "model": "openai/gpt-oss-120b",
                "choices": [{"index": 0, "finish_reason": "length", "message": {
                    "role": "assistant", "content": ANSWER, "reasoning": "private reasoning"}}],
                "usage": {"prompt_tokens": 460, "completion_tokens": 768, "total_tokens": 1228},
            })

        with groq.Groq(api_key="test", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
            planner._groq = client
            self.assertTrue(planner.plan(QUESTION).message.startswith(ANSWER))
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["reasoning_effort"], "low")
        self.assertFalse(requests[0]["include_reasoning"])
        self.assertEqual(requests[0]["response_format"], {"type": "text"})
        self.assertEqual(requests[0]["max_completion_tokens"], 768)

    def test_other_groq_models_do_not_receive_unsupported_reasoning_options(self):
        planner = planner_for()
        planner._groq_model = "llama-3.3-70b-versatile"
        create = Mock(return_value=groq_response(ANSWER, "stop"))
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        self.assertEqual(planner.plan(QUESTION).message, ANSWER)
        self.assertEqual(create.call_args.kwargs["extra_body"], {"max_completion_tokens": 768})
