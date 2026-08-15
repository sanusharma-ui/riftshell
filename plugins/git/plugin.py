import subprocess

from core.base import BaseCommand, CommandResult
from core.plugin_base import BasePlugin


class GitCommand(BaseCommand):
    """
    Generic Git command wrapper.
    """

    def __init__(self, name, git_args, description, usage):
        self.name = name
        self.git_args = git_args
        self.description = description
        self.usage = usage

    def execute(self, ctx, args):
        try:
            result = subprocess.run(
                ["git", *self.git_args, *args],
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
                output="Git is not installed or not available in PATH.",
                success=False,
            )

        except Exception as exc:
            return CommandResult(
                output=f"Git error: {exc}",
                success=False,
            )


class GitPlugin(BasePlugin):

    name = "git"
    version = "1.0.0"
    description = "Git integration for RiftShell"

    def register(self, registry):

        registry.register(
            GitCommand(
                name="gst",
                git_args=["status"],
                description="Show Git repository status",
                usage="gst",
            )
        )

        registry.register(
            GitCommand(
                name="glog",
                git_args=["log"],
                description="Show Git commit history",
                usage="glog",
            )
        )

        registry.register(
            GitCommand(
                name="gbranch",
                git_args=["branch"],
                description="Show Git branches",
                usage="gbranch",
            )
        )

        registry.register(
            GitCommand(
                name="gdiff",
                git_args=["diff"],
                description="Show Git changes",
                usage="gdiff",
            )
        )


plugin = GitPlugin()