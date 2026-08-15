import subprocess

from core.base import BaseCommand, CommandResult
from core.plugin_base import BasePlugin


class GitCommand(BaseCommand):
    """
    Generic RiftShell Git command.
    """

    def __init__(
        self,
        name,
        git_args,
        description,
        usage,
        aliases=None,
    ):
        self.name = name
        self.git_args = git_args
        self.description = description
        self.usage = usage
        self.aliases = aliases or []

    def execute(self, ctx, args):

        try:
            command = [
                "git",
                *self.git_args,
                *args,
            ]

            result = subprocess.run(
                command,
                cwd=str(ctx.cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            output = result.stdout.strip()

            if result.stderr.strip():

                if output:
                    output += "\n"

                output += result.stderr.strip()

            return CommandResult(
                output=output,
                success=result.returncode == 0,
            )

        except FileNotFoundError:

            return CommandResult(
                output=(
                    "Git is not installed or "
                    "not available in PATH."
                ),
                success=False,
            )

        except Exception as exc:

            return CommandResult(
                output=f"Git error: {exc}",
                success=False,
            )


class GitPlugin(BasePlugin):

    name = "git"
    version = "2.0.0"
    description = "Advanced Git integration for RiftShell"

    def register(self, registry):

        # -------------------------
        # Status
        # -------------------------

        registry.register(
            GitCommand(
                name="gstatus",
                aliases=["gst"],
                git_args=["status"],
                description="Show Git repository status",
                usage="gstatus",
            )
        )

        # -------------------------
        # Branch
        # -------------------------

        registry.register(
            GitCommand(
                name="gbranch",
                aliases=["gb"],
                git_args=["branch"],
                description="Show Git branches",
                usage="gbranch",
            )
        )

        # -------------------------
        # Log
        # -------------------------

        registry.register(
            GitCommand(
                name="glog",
                aliases=["gl"],
                git_args=["log"],
                description="Show Git commit history",
                usage="glog",
            )
        )

        # -------------------------
        # Diff
        # -------------------------

        registry.register(
            GitCommand(
                name="gdiff",
                aliases=["gd"],
                git_args=["diff"],
                description="Show unstaged Git changes",
                usage="gdiff",
            )
        )

        # -------------------------
        # Add
        # -------------------------

        registry.register(
            GitCommand(
                name="gadd",
                aliases=["ga"],
                git_args=["add"],
                description="Stage files for commit",
                usage="gadd <files...>",
            )
        )

        # -------------------------
        # Commit
        # -------------------------

        registry.register(
            GitCommand(
                name="gcommit",
                aliases=["gc"],
                git_args=["commit"],
                description="Create a Git commit",
                usage='gcommit -m "message"',
            )
        )

        # -------------------------
        # Pull
        # -------------------------

        registry.register(
            GitCommand(
                name="gpull",
                aliases=["gpl"],
                git_args=["pull"],
                description="Pull changes from remote",
                usage="gpull",
            )
        )

        # -------------------------
        # Push
        # -------------------------

        registry.register(
            GitCommand(
                name="gpush",
                aliases=["gps"],
                git_args=["push"],
                description="Push commits to remote",
                usage="gpush",
            )
        )

        # -------------------------
        # Checkout
        # -------------------------

        registry.register(
            GitCommand(
                name="gcheckout",
                aliases=["gco"],
                git_args=["checkout"],
                description="Switch Git branches or restore files",
                usage="gcheckout <branch>",
            )
        )

        # -------------------------
        # Remote
        # -------------------------

        registry.register(
            GitCommand(
                name="gremote",
                aliases=["gr"],
                git_args=["remote", "-v"],
                description="Show Git remote repositories",
                usage="gremote",
            )
        )


plugin = GitPlugin()