"""Patch test_query_routing.py to reflect the new intentional current_dir read."""
from pathlib import Path

src = Path("tests/test_query_routing.py")
content = src.read_text(encoding="utf-8")

old = (
    '    def test_conversation_context_is_bounded_and_never_reads_terminal_or_native_state(self):\n'
    '        for mode in default_modes():\n'
    '            with self.subTest(mode=mode.name):\n'
    '                planner = planner_for_test(orbit_mode=mode)\n'
    '                planner.current_dir_provider = Mock(side_effect=AssertionError("directory read"))\n'
    '                planner.native_context_provider = Mock(side_effect=AssertionError("native context"))\n'
    '                planner.last_output_provider = Mock(side_effect=AssertionError("terminal read"))\n'
    '                rows = [{"role": role, "content": f"turn-{i}: " + "long history " * 500}\n'
    '                        for i in range(20) for role in ("user", "assistant")]\n'
    '                planner.memory.load = lambda: rows\n'
    '                prompt = build_conversation_prompt(planner, "Explain the next concept")\n'
    '                self.assertTrue(prompt.endswith("Explain the next concept"))\n'
    '                self.assertIn("turn-19", prompt)\n'
    '                self.assertNotIn("turn-0:", prompt)\n'
    '                self.assertNotIn("Available Commands & Aliases", prompt)\n'
    '                self.assertIn(f"Hard output ceiling: {mode.output_tokens}", prompt)\n'
    '                self.assertLessEqual(estimated_tokens(prompt), mode.prompt_tokens)\n'
    '                self.assertEqual(len(rows), 40)\n'
)

new = (
    '    def test_conversation_context_is_bounded_and_never_reads_terminal_or_native_state(self):\n'
    '        for mode in default_modes():\n'
    '            with self.subTest(mode=mode.name):\n'
    '                planner = planner_for_test(orbit_mode=mode)\n'
    '                # current_dir_provider IS now called (safely, with try/except) to inject the\n'
    '                # live directory so the AI never guesses location from stale memory.\n'
    '                # native_context_provider and last_output_provider must still never be read.\n'
    '                planner.native_context_provider = Mock(side_effect=AssertionError("native context"))\n'
    '                planner.last_output_provider = Mock(side_effect=AssertionError("terminal read"))\n'
    '                rows = [{"role": role, "content": f"turn-{i}: " + "long history " * 500}\n'
    '                        for i in range(20) for role in ("user", "assistant")]\n'
    '                planner.memory.load = lambda: rows\n'
    '                prompt = build_conversation_prompt(planner, "Explain the next concept")\n'
    '                self.assertTrue(prompt.endswith("Explain the next concept"))\n'
    '                self.assertIn("turn-19", prompt)\n'
    '                self.assertNotIn("turn-0:", prompt)\n'
    '                self.assertNotIn("Available Commands & Aliases", prompt)\n'
    '                self.assertIn(f"Hard output ceiling: {mode.output_tokens}", prompt)\n'
    '                self.assertLessEqual(estimated_tokens(prompt), mode.prompt_tokens)\n'
    '                self.assertEqual(len(rows), 40)\n'
    '                # The live directory hint must be present so the AI does not\n'
    '                # fabricate location from stale conversation history.\n'
    '                self.assertIn("current directory is", prompt)\n'
)

if old in content:
    updated = content.replace(old, new)
    src.write_text(updated, encoding="utf-8")
    print("Patched test successfully.")
else:
    print("FAIL: old pattern not found")
    # debug: find the function
    idx = content.find("def test_conversation_context_is_bounded")
    print(repr(content[idx:idx+1000]))
