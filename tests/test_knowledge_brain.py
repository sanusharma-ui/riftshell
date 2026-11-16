from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from ai.knowledge_brain import CommandKnowledgeBrain, CommandKnowledgeProfile
from core.registry import CommandMetadata, CommandRegistry
from core.base import BaseCommand, CommandResult


class DummyPluginCommand(BaseCommand):
    name = "myplugin"
    aliases = ["mp"]
    description = "Special plugin for automated data analysis."
    usage = "myplugin <analyze|report> [args]"

    def execute(self, ctx, args):
        return CommandResult(output="Plugin executed.")


class TestCommandKnowledgeBrain(unittest.TestCase):
    def setUp(self):
        self.brain = CommandKnowledgeBrain()

    def test_core_commands_indexed(self):
        # Verify essential commands are profiled with capabilities and controls
        for cmd_name in ("open", "browser", "note", "findtext", "search", "zip", "unzip", "processes", "kill", "memory"):
            profile = self.brain.get_profile(cmd_name)
            self.assertIsNotNone(profile, f"Command {cmd_name} should be indexed")
            self.assertTrue(len(profile.capabilities) > 0, f"{cmd_name} must have capabilities")
            self.assertTrue(len(profile.controls) > 0, f"{cmd_name} must have controls")
            self.assertTrue(bool(profile.usage), f"{cmd_name} must have usage")

    def test_dynamic_registration(self):
        self.brain.register_command(
            name="docker_run",
            aliases=("drun",),
            description="Run and manage docker containers.",
            usage="docker_run <image>",
            category="containers",
            capabilities=("Manage Docker containers easily",),
            controls=("docker_run <image> -> launch container",),
            tags=("docker", "containers", "image"),
        )
        profile = self.brain.get_profile("docker_run")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.category, "containers")
        self.assertIn("drun", profile.aliases)

        # Test searching the newly registered command
        matches = self.brain.search_capabilities("how to launch docker container")
        self.assertTrue(any(p.name == "docker_run" for p, _, _ in matches))

    def test_sync_with_registry(self):
        reg = CommandRegistry()
        reg.register(DummyPluginCommand(), source="plugin", plugin="data_analyzer")

        self.brain.sync_with_registry(reg)
        profile = self.brain.get_profile("myplugin")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "myplugin")
        self.assertIn("mp", profile.aliases)
        self.assertIn("plugin", profile.category)

    def test_is_task_feasibility_query(self):
        # Feasibility / guidance queries in English and Hindi/Hinglish
        positive_queries = [
            "mujhe iss particular task ko karna hai kya kuch ho sakta hai",
            "kya mai youtube se gaana chala sakta hu?",
            "kya riftshell me file compress ho sakti hai?",
            "can I search for passwords inside files?",
            "how do I terminate a frozen process?",
            "is there a command to check my RAM usage?",
            "what command can I use to download a file from url?",
            "mujhe background music chalana hai kaise hoga",
            "which command is best for git commits?",
        ]
        for q in positive_queries:
            with self.subTest(query=q):
                self.assertTrue(self.brain.is_task_feasibility_query(q), f"Should recognize as feasibility query: {q}")

        # Direct commands should NOT be treated as feasibility inquiries
        negative_queries = [
            "open notepad",
            "files",
            "where",
            "browser search python",
            "delete confirm test.txt",
        ]
        for q in negative_queries:
            with self.subTest(query=q):
                self.assertFalse(self.brain.is_task_feasibility_query(q), f"Should NOT be feasibility query: {q}")

    def test_search_capabilities(self):
        # 1. Search text inside files
        matches = self.brain.search_capabilities("search password inside python files")
        names = [p.name for p, _, _ in matches]
        self.assertIn("findtext", names)

        # 2. Browser & Music playback
        matches = self.brain.search_capabilities("play lofi music or search youtube")
        names = [p.name for p, _, _ in matches]
        self.assertTrue("browser" in names or "open" in names)

        # 3. Hindi intent: "gaana chalao"
        matches = self.brain.search_capabilities("gaana chalao")
        names = [p.name for p, _, _ in matches]
        self.assertTrue("browser" in names or "open" in names)

        # 4. Process kill
        matches = self.brain.search_capabilities("terminate frozen program")
        names = [p.name for p, _, _ in matches]
        self.assertIn("kill", names)

        # 5. Zip / compress
        matches = self.brain.search_capabilities("compress folder into archive")
        names = [p.name for p, _, _ in matches]
        self.assertIn("zip", names)

    def test_formulate_guidance(self):
        guidance = self.brain.formulate_guidance("mujhe file ke andar password dhundhna hai kya ho sakta hai")
        self.assertIn("findtext", guidance)
        self.assertIn("Recommended Command", guidance)
        self.assertIn("What it does", guidance)

    def test_prompt_knowledge_snippet(self):
        snippet = self.brain.get_prompt_knowledge_snippet("how do I extract a zip archive?")
        self.assertIn("unzip", snippet.lower())
        self.assertIn("Usage:", snippet)
        self.assertIn("Capability:", snippet)


class TestPlannerKnowledgeIntegration(unittest.TestCase):
    def test_planner_offline_feasibility_guidance(self):
        from ai.config import AIConfig
        from ai.llm import AgentPlanner
        from core.shell import Shell

        shell = Shell()
        config = AIConfig.from_env()
        # Force offline / no keys
        config_dict = config.__dict__.copy() if hasattr(config, "__dict__") else {}
        from dataclasses import replace
        offline_config = replace(config, ai_provider="auto", gemini_api_key="", groq_api_key="", ollama_model="")

        planner = AgentPlanner(
            config=offline_config,
            command_names=shell.registry.all_names(),
            command_catalog=shell.registry.catalog_entries(),
            command_metadata=shell.registry.list_metadata(),
            current_dir_provider=lambda: shell.ctx.cwd,
        )

        # Inquire about feasibility of searching content
        action = planner.plan("mujhe file ke andar text dhundhna hai kya kuch ho sakta hai")
        self.assertEqual(action.action, "respond")
        self.assertIn("findtext", action.message)
        self.assertIn("Recommended Command", action.message)

    def test_planner_answers_how_many_commands(self):
        from ai.config import AIConfig
        from ai.llm import AgentPlanner
        from core.shell import Shell

        shell = Shell()
        config = AIConfig.from_env()

        planner = AgentPlanner(
            config=config,
            command_names=shell.registry.all_names(),
            command_catalog=shell.registry.catalog_entries(),
            command_metadata=shell.registry.list_metadata(),
            current_dir_provider=lambda: shell.ctx.cwd,
        )

        for query in ("how many commands we have", "kitne commands hai", "total commands"):
            with self.subTest(query=query):
                action = planner.plan(query)
                self.assertEqual(action.action, "respond")
                self.assertIn("commands", action.message.lower())
                self.assertIn("registered", action.message.lower())
                # Must be brief (under 200 words)
                self.assertLess(len(action.message.split()), 200)
