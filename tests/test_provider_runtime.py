import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ai.actions import AgentAction
from ai.llm import MemoryManager
from ai.provider_runtime import ProviderRuntime, daily_quota, duration_seconds, retry_delay
from test_ai_providers import FakeGemini, FakeGroq, FailingGroq, make_config, make_planner


class RateLimitError(Exception):
    status_code = 429

    def __init__(self, message="Rate limit reached", headers=None, details=()):
        super().__init__(message)
        self.response = SimpleNamespace(status_code=429, headers=headers or {})
        self.details = details


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.runtime = ProviderRuntime(clock=self.clock, sleep=self.clock.sleep)
        self.key = self.runtime.key("groq", "secret", "model")

    def test_retry_after_and_provider_delay_formats(self):
        self.assertEqual(duration_seconds(0), 0)
        self.assertEqual(duration_seconds("1m2.5s"), 62.5)
        self.assertEqual(duration_seconds("200ms"), .2)
        for invalid in (None, "", "nan", "inf", "-1", "broken", "2seconds"):
            self.assertIsNone(duration_seconds(invalid))
        self.assertEqual(retry_delay(RateLimitError("try again in 12.015s")), 12.015)
        self.assertEqual(retry_delay(RateLimitError("Please retry in 4.251334072s.")), 4.251334072)
        self.assertEqual(retry_delay(RateLimitError("try again in 12s", {"retry-after": "3"})), 3)
        info = SimpleNamespace(retry_delay=SimpleNamespace(seconds=4, nanos=250000000))
        self.assertEqual(retry_delay(RateLimitError(details=[info])), 4.25)
        with patch("ai.provider_runtime.time.time", return_value=0):
            self.assertEqual(retry_delay(RateLimitError(headers={
                "retry-after": "Thu, 01 Jan 1970 00:00:10 GMT"})), 10)

    def test_cooldown_expires_and_isolated_by_model_and_credential(self):
        self.runtime.record_failure(self.key, RateLimitError(headers={"retry-after": "12"}))
        self.assertEqual(self.runtime.cooldown(self.key).remaining, 12)
        self.assertIsNone(self.runtime.cooldown(self.runtime.key("groq", "other-key", "model")))
        self.assertIsNone(self.runtime.cooldown(self.runtime.key("groq", "secret", "other-model")))
        self.clock.sleep(12)
        self.assertIsNone(self.runtime.cooldown(self.key))

    def test_success_headers_preempt_only_explicit_exhaustion(self):
        self.runtime.record_headers(self.key, {"x-ratelimit-remaining-tokens": "4065",
                                              "x-ratelimit-reset-tokens": "12s"})
        self.assertIsNone(self.runtime.cooldown(self.key))
        self.runtime.record_headers(self.key, {"x-ratelimit-remaining-tokens": "0",
                                              "x-ratelimit-reset-tokens": "1m2s"})
        self.assertEqual(self.runtime.cooldown(self.key).remaining, 62)
        # Another in-flight response must not shorten an existing cooldown.
        self.runtime.record_headers(self.key, {"x-ratelimit-remaining-tokens": "0",
                                              "x-ratelimit-reset-tokens": "1s"})
        self.assertEqual(self.runtime.cooldown(self.key).remaining, 62)

    def test_daily_quota_requires_explicit_evidence_and_ignores_short_hint(self):
        self.assertFalse(daily_quota(RateLimitError("generate_content_free_tier_requests limit: 20")))
        key = self.runtime.key("gemini", "secret", "model")
        with patch("ai.provider_runtime.seconds_until_pacific_midnight", return_value=3600):
            cooldown = self.runtime.record_failure(key, RateLimitError(
                "quota_id: GenerateRequestsPerDayPerProjectPerModel-FreeTier. Please retry in 4s."))
        self.assertTrue(cooldown.daily)
        self.assertEqual(cooldown.remaining, 3600)

    def test_non_quota_failures_do_not_poison_provider(self):
        self.assertIsNone(self.runtime.record_failure(self.key, RuntimeError("connection failed")))
        self.assertIsNone(self.runtime.cooldown(self.key))

    def test_oversized_prompt_does_not_block_smaller_followup_requests(self):
        error = RateLimitError("Request too large. Limit 8,000, Used 0, Requested 9,000")
        self.assertIsNone(self.runtime.record_failure(self.key, error))
        self.assertIsNone(self.runtime.cooldown(self.key))

    def test_unknown_retry_hint_uses_cooldown_without_busy_retry(self):
        self.assertEqual(self.runtime.record_failure(self.key, RateLimitError()).remaining, 60)

    def test_diagnostics_are_bounded_and_redact_credentials(self):
        for index in range(110):
            self.runtime.record("provider", error="failed with secret", secrets=("secret",), index=index)
        records = self.runtime.diagnostics()
        self.assertEqual(len(records), 100)
        self.assertEqual(records[0]["index"], 10)
        self.assertNotIn("secret", str(records))
        records[0]["error"] = "modified"
        self.assertNotEqual(self.runtime.diagnostics()[0]["error"], "modified")


class ProviderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.runtime = ProviderRuntime(clock=self.clock, sleep=self.clock.sleep)

    def planner(self, **overrides):
        values = {"groq_api_key": "test-key", "gemini_api_key": "test-key"}
        values.update(overrides)
        planner = make_planner(make_config(**values))
        planner.provider_runtime = self.runtime
        return planner

    def test_rate_limit_falls_back_without_wait_then_next_turn_skips_groq(self):
        first = self.planner()
        first._groq = FailingGroq(RateLimitError(headers={"retry-after": "12"}))
        first._gemini = FakeGemini("fallback")
        self.assertEqual(first.plan("Explain dependency injection").message, "fallback")
        second = self.planner()
        second._groq = FakeGroq()
        second._gemini = FakeGemini("next fallback")
        self.assertEqual(second.plan("Explain dependency injection").message, "next fallback")
        self.assertEqual(second._groq.calls, 0)
        self.assertEqual(self.clock.now, 100)
        self.clock.sleep(12)
        self.assertEqual(second.plan("Explain dependency injection").message, "groq response")
        self.assertEqual(second._groq.calls, 1)

    def test_short_retry_returns_one_action_without_replaying_execution(self):
        planner = self.planner(ai_provider="groq")
        planner._call_provider = Mock(side_effect=[
            RateLimitError(headers={"retry-after": "2"}),
            json.dumps({"action": "shell", "command": "files"}),
        ])
        progress = []
        planner.progress = progress.append
        action, errors, provider = planner._request_model_action("task")
        self.assertEqual(action.command, "files")
        self.assertEqual(provider, "groq")
        self.assertEqual(planner._call_provider.call_count, 2)
        self.assertTrue(any("retrying" in message for message in progress))
        self.assertLess(self.clock.now, 103)

    def test_stop_during_wait_prevents_second_generation(self):
        planner = self.planner(ai_provider="groq")
        planner._call_provider = Mock(side_effect=RateLimitError(headers={"retry-after": "2"}))
        planner.cancelled = lambda: self.clock.now > 100.3
        action, errors, _ = planner._request_model_action("task")
        self.assertIsNone(action)
        self.assertEqual(errors, ["Task stopped."])
        self.assertEqual(planner._call_provider.call_count, 1)
        self.assertLess(self.clock.now, 101)

    def test_long_and_daily_limits_return_without_wait(self):
        for error in (RateLimitError(headers={"retry-after": "90"}),
                      RateLimitError("RequestsPerDay exhausted; retry in 4s")):
            with self.subTest(error=str(error)):
                planner = self.planner(ai_provider="groq")
                planner.provider_runtime = ProviderRuntime(clock=self.clock, sleep=self.clock.sleep)
                planner._call_provider = Mock(side_effect=error)
                action, errors, _ = planner._request_model_action("task")
                self.assertIsNone(action)
                self.assertTrue(errors)
                self.assertEqual(self.clock.now, 100)
                self.assertEqual(planner._call_provider.call_count, 1)

    def test_repeated_429_has_one_retry_and_no_unbounded_loop(self):
        planner = self.planner(ai_provider="groq")
        planner._call_provider = Mock(side_effect=RateLimitError(headers={"retry-after": "1"}))
        action, _, _ = planner._request_model_action("task")
        self.assertIsNone(action)
        self.assertEqual(planner._call_provider.call_count, 2)
        self.assertLess(self.clock.now, 102)

    def test_retry_retains_other_provider_failure_in_final_status(self):
        planner = self.planner()
        planner._call_provider = Mock(side_effect=[
            RateLimitError(headers={"retry-after": "1"}), RuntimeError("Gemini unavailable"),
            RateLimitError(headers={"retry-after": "1"}),
        ])
        action, errors, _ = planner._request_model_action("task")
        self.assertIsNone(action)
        self.assertTrue(any("Groq:" in message for message in errors))
        self.assertTrue(any("Gemini:" in message for message in errors))

    def test_reused_planner_has_new_wait_budget_for_new_user_task(self):
        planner = self.planner(ai_provider="groq")
        planner._quota_wait_remaining = 0
        planner._call_provider = Mock(side_effect=[
            RateLimitError(headers={"retry-after": "1"}),
            '{"action":"respond","message":"recovered"}',
        ])
        self.assertEqual(planner.plan("Explain dependency injection").message, "recovered")
        self.assertEqual(planner._call_provider.call_count, 2)

    def test_forced_provider_does_not_fall_back_while_cooling_down(self):
        planner = self.planner(ai_provider="groq")
        self.runtime.record_failure(planner._provider_key("groq"), RateLimitError(headers={"retry-after": "90"}))
        planner._call_provider = Mock()
        self.assertIsNone(planner._request_model_action("task")[0])
        planner._call_provider.assert_not_called()

    def test_raw_groq_headers_are_read_without_changing_generation_parameters(self):
        planner = self.planner(ai_provider="groq")
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"action":"respond","message":"complete answer"}'))])
        raw = SimpleNamespace(headers={"x-ratelimit-remaining-tokens": "0",
                                       "x-ratelimit-reset-tokens": "30s"}, parse=lambda: response)
        create = Mock(return_value=raw)
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            with_raw_response=SimpleNamespace(create=create))))
        action, _, _ = planner._request_model_action("full context")
        self.assertEqual(action.message, "complete answer")
        self.assertEqual(create.call_args.kwargs["messages"][0]["content"], "full context")
        self.assertNotIn("max_tokens", create.call_args.kwargs)
        self.assertEqual(self.runtime.cooldown(planner._provider_key("groq")).remaining, 30)

    def test_installed_groq_sdk_raw_response_and_rate_limit_with_offline_transport(self):
        import groq
        import httpx
        planner = self.planner()
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            if len(requests) == 1:
                return httpx.Response(200, headers={"x-ratelimit-remaining-tokens": "4000"}, json={
                    "id": "test", "object": "chat.completion", "created": 1, "model": "groq-test",
                    "choices": [{"index": 0, "finish_reason": "stop", "message": {
                        "role": "assistant", "content": '{"action":"respond","message":"SDK answer"}'}}],
                })
            return httpx.Response(429, headers={"retry-after": "12"}, json={
                "error": {"message": "Rate limit reached", "type": "tokens", "code": "rate_limit_exceeded"}})

        with groq.Groq(api_key="test-key", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
            planner._groq = client
            planner._gemini = FakeGemini("SDK fallback")
            self.assertEqual(planner._request_model_action("full unchanged prompt")[0].message, "SDK answer")
            self.assertEqual(planner._request_model_action("next prompt")[0].message, "SDK fallback")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["messages"][0]["content"], "full unchanged prompt")
        self.assertEqual(self.runtime.cooldown(planner._provider_key("groq")).remaining, 12)

    def test_installed_google_exception_retry_info_is_respected(self):
        from google.api_core.exceptions import ResourceExhausted
        from google.rpc.error_details_pb2 import RetryInfo
        detail = RetryInfo()
        detail.retry_delay.seconds = 4
        detail.retry_delay.nanos = 250000000
        error = ResourceExhausted("Quota exceeded", details=[detail])
        key = self.runtime.key("gemini", "test-key", "gemini-test")
        self.assertEqual(self.runtime.record_failure(key, error).remaining, 4.25)


class PromptPreservationTests(unittest.TestCase):
    def test_continuation_error_does_not_erase_prior_execution_evidence(self):
        from ai.llm import _memory_content
        result = _memory_content("assistant", "Proposed next action: respond; "
                                 "I read the workspace context but could not analyze it.\nDetails: Groq: 429")
        self.assertIn("earlier execution results still apply", result)
        self.assertIn("rate limit/quota", result)
        self.assertNotIn("No action was executed", result)

    def test_legacy_errors_are_compacted_only_in_assistant_context_without_rewriting_file(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "history.json"
            error = "I could not reach the selected AI provider.\nDetails: Groq: secret-technical-error"
            user = "Why did this error happen? " + error
            raw = json.dumps([
                {"role": "user", "content": user},
                {"role": "assistant", "content": "Proposed action (execution not confirmed): respond; Command: (none); Response: " + error},
                {"role": "user", "content": "Only edit D:/app.py; preserve approvals."},
            ])
            path.write_text(raw, encoding="utf-8")
            memory = MemoryManager(str(path), 12, True)
            prompt = memory.format_for_prompt()
            self.assertIn(user, prompt)
            self.assertIn("Only edit D:/app.py; preserve approvals.", prompt)
            self.assertEqual(prompt.count("secret-technical-error"), 1)
            self.assertIn("No action was executed", prompt)
            self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_new_failure_memory_retains_user_request_but_not_provider_dump(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            planner = make_planner(make_config(ai_memory_enabled=True,
                                              ai_memory_path=str(Path(directory) / "history.json")))
            planner._remember_action("Explain this project", AgentAction(
                "respond", "AI providers are temporarily unavailable.\n429 very-long-error"))
            history = planner.memory.load()
            self.assertEqual(history[0]["content"], "Explain this project")
            self.assertNotIn("very-long-error", history[1]["content"])
            self.assertIn("No action was executed", history[1]["content"])

    def test_continuation_inspection_does_not_duplicate_system_history_and_catalog(self):
        planner = make_planner(make_config(gemini_api_key="test-key"))
        planner._request_model_action = Mock(return_value=(
            AgentAction("inspect", paths=["ai/actions.py"]), [], "gemini"))
        planner._complete_inspection = Mock(return_value=AgentAction("respond", "done"))
        planner.continue_task("Review action types", [{"success": True, "output": "unique execution evidence"}])
        context = planner._complete_inspection.call_args.kwargs["task_context"]
        self.assertIn("unique execution evidence", context)
        self.assertIn("UNTRUSTED DATA", context)
        self.assertNotIn("UNIVERSAL RULES", context)
        self.assertNotIn("Available Commands & Aliases", context)
        full_prompt = planner._request_model_action.call_args.args[0]
        self.assertIn("UNIVERSAL RULES", full_prompt)
        self.assertIn("Available Commands & Aliases", full_prompt)


if __name__ == "__main__":
    unittest.main()
