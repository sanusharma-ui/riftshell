import unittest
from unittest.mock import Mock, patch

from ai.orbit_bridge import OrbitBridge
from ai.risk import classify_risk


class RiskClassificationTests(unittest.TestCase):
    def test_tier_zero_observation_and_reversible_input(self):
        for action, args in (
            ("screenshot", ""),
            ("windows", "list"),
            ("mouse_click", "10 20"),
            ("browser_navigate", "https://example.com"),
        ):
            with self.subTest(action=action):
                decision = classify_risk(action, args, "local")
                self.assertEqual(decision.tier, 0)
                self.assertFalse(decision.requires_approval)

    def test_tier_one_state_change(self):
        decision = classify_risk("shell", "rename old.txt new.txt", "telegram")
        self.assertEqual(decision.tier, 1)
        self.assertTrue(decision.requires_approval)

    def test_tier_two_destructive_or_sensitive_action(self):
        for text in ("delete confirm file.txt", "keyboard type password"):
            with self.subTest(text=text):
                decision = classify_risk("shell", text, "local")
                self.assertEqual(decision.tier, 2)
                self.assertTrue(decision.requires_approval)


class OrbitBridgeTests(unittest.TestCase):
    def test_catalog_is_derived_from_registry_metadata(self):
        shell = Mock()
        shell.registry.list_metadata.return_value = [
            Mock(name="demo", usage="demo <arg>", aliases=("d",), description="Demo command")
        ]
        catalog = OrbitBridge(shell).command_catalog()
        self.assertEqual(len(catalog), 1)
        self.assertIn("demo <arg>", catalog[0])
        self.assertIn("aliases=d", catalog[0])

    def test_run_command_uses_shell_executor(self):
        shell = Mock()
        shell.execute_line.return_value = "result"
        result = OrbitBridge(shell).run_command("files", ["notes"])
        shell.execute_line.assert_called_once_with("files notes")
        self.assertEqual(result, "result")


if __name__ == "__main__":
    unittest.main()
