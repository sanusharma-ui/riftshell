import unittest
from core.shell import Shell
from ai.semantic_intent import HybridIntentExtractor


class TestNaturalLanguageCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = Shell()
        cls.extractor = HybridIntentExtractor(
            cls.shell.registry.all_names(),
            metadata=cls.shell.registry.list_metadata(),
        )

    def test_theme_natural_queries(self):
        cases = {
            "help me to find new themes": "theme",
            "find new themes": "theme",
            "themes": "theme",
            "riftshell theme": "theme",
            "show themes": "theme",
            "list themes": "theme",
            "what themes are available": "theme",
            "theme badlo": "theme",
            "theme change karo": "theme",
            "themes dikhao": "theme",
            "saare themes dikhao": "theme",
            "change theme to midnight-aurora": "theme midnight-aurora",
            "apply theme ember-grove": "theme ember-grove",
            "switch theme to github-dark": "theme github-dark",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                res = self.extractor.extract(query)
                self.assertIsNotNone(res.match, f"No match for: {query}")
                self.assertEqual(res.match.command, expected)

    def test_hardware_and_disks_queries(self):
        cases = {
            "how many disks are installed on my computer": "drives",
            "how many disks are installed on this computer": "drives",
            "how many disks are there": "drives",
            "how many drives do i have": "drives",
            "kitne disk hai": "drives",
            "kitne disks hai": "drives",
            "disks dikhao": "drives",
            "drives dikhao": "drives",
            "show drives": "drives",
            "list all drives": "drives",
            "show disks": "drives",
            "check disks": "drives",
            "system info": "system",
            "hardware details": "system",
            "pc specs": "system",
            "computer specifications": "system",
            "ram usage": "memory",
            "ram kitni hai": "memory",
            "check ram": "memory",
            "how much ram is being used": "memory",
            "what is my ip address": "ip",
            "my ip": "ip",
            "mera ip address kya hai": "ip",
            "system uptime": "uptime",
            "pc kab se chalu hai": "uptime",
            "free disk space": "disk",
            "check disk space": "disk",
            "how much disk space is left": "disk",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                res = self.extractor.extract(query)
                self.assertIsNotNone(res.match, f"No match for: {query}")
                self.assertEqual(res.match.command, expected)

    def test_general_commands_natural_language(self):
        cases = {
            "where am i": "where",
            "current folder": "where",
            "kaha hu mai": "where",
            "files dikhao": "files",
            "folders dikhao": "folders",
            "clear terminal": "clear",
            "show running processes": "processes",
            "active windows": "windows",
            "kill notepad.exe": "kill notepad.exe",
            "calculate 15 * 8": 'calc "15 * 8"',
            "take note buy groceries": 'note "buy groceries"',
            "zip src to backup.zip": "zip src backup.zip",
            "unzip backup.zip": "unzip backup.zip",
            "show env": "env",
            "show vars": "vars",
            "show path": "path",
            "what time is it": "now",
            "what is today's date": "today",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                res = self.extractor.extract(query)
                self.assertIsNotNone(res.match, f"No match for: {query}")
                self.assertEqual(res.match.command, expected)


if __name__ == "__main__":
    unittest.main()
