from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Callable

from ai.actions import AgentAction
from ai.code_writer import FileSnapshot, apply_file_writes, preview_file_writes
from ai.config import AIConfig
from ai.llm import AgentPlanner
from ai.safety import SafetyPolicy
from ai.screenshot import capture_screenshot
from core.shell import Shell


@dataclass
class PendingAction:
    id: str
    requester_id: int
    action: AgentAction
    reason: str
    created_at: datetime
    snapshots: tuple[FileSnapshot, ...] = ()


class TelegramAIBot:
    def __init__(
        self,
        config: AIConfig,
        on_command_completed: Callable[[str, object], None] | None = None,
    ):
        self.config = config
        self.on_command_completed = on_command_completed
        self.shell = Shell(
            start_dir=config.workspace_root,
            workspace_root=config.workspace_root,
            allow_outside_workspace=config.allow_outside_workspace,
        )
        self.safety = SafetyPolicy()
        self.planner = AgentPlanner(
            config=config,
            command_names=self.shell.registry.all_names(),
            command_catalog=self.shell.registry.catalog_entries(),
            command_metadata=self.shell.registry.list_metadata(),
            current_dir_provider=lambda: self.shell.ctx.cwd,
        )
        self.pending: dict[str, PendingAction] = {}
        self._shell_lock: asyncio.Lock | None = None
        self._application = None

    @property
    def shell_lock(self) -> asyncio.Lock:
        if self._shell_lock is None:
            self._shell_lock = asyncio.Lock()
        return self._shell_lock

    def run(self) -> None:
        problems = self.config.validate_for_telegram()
        if problems:
            raise RuntimeError("Cannot start AI bot: " + "; ".join(problems))

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

        app = Application.builder().token(self.config.telegram_bot_token).build()
        self._application = app
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.start))
        app.add_handler(CommandHandler("cmd", self.cmd))
        app.add_handler(CommandHandler("open", self.open_cmd))
        app.add_handler(CommandHandler("browser", self.browser_cmd))
        app.add_handler(CommandHandler("screenshot", self.screenshot))
        app.add_handler(CommandHandler("approve", self.approve))
        app.add_handler(CommandHandler("deny", self.deny))
        app.add_handler(CommandHandler("pending", self.pending_list))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message))
        app.run_polling(allowed_updates=["message", "callback_query"])

    def stop(self) -> None:
        if self._application is not None:
            self._application.stop_running()

    async def _reply_text(self, update, text: str, **kwargs) -> None:
        msg = getattr(update, "effective_message", None)
        if msg is not None:
            await msg.reply_text(text, **kwargs)
        elif getattr(update, "effective_chat", None) is not None and self._application is not None:
            await self._application.bot.send_message(chat_id=update.effective_chat.id, text=text, **kwargs)

    async def _reply_photo(self, update, photo, **kwargs) -> None:
        msg = getattr(update, "effective_message", None)
        if msg is not None:
            await msg.reply_photo(photo=photo, **kwargs)
        elif getattr(update, "effective_chat", None) is not None and self._application is not None:
            await self._application.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, **kwargs)

    def _is_allowed(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        if self.config.telegram_allow_unlisted_users:
            return True
        return user_id in self.config.telegram_allowed_user_ids

    async def _guard(self, update) -> bool:
        user_id = update.effective_user.id if update.effective_user else None
        if self._is_allowed(user_id):
            return True
        await self._reply_text(update, "Unauthorized. Add your Telegram user id to TELEGRAM_ALLOWED_USER_IDS.")
        return False

    async def start(self, update, context) -> None:
        if not await self._guard(update):
            return
        await self._reply_text(
            update,
            "RiftShell AI bot online.\n"
            "Commands:\n"
            "• Natural language: ask questions or describe actions\n"
            "• /open <path|url|app>: open websites, Windows apps, files\n"
            "• /browser <open|search|play|control|tabs>: control browser\n"
            "• /cmd <command>: run any RiftShell command\n"
            "• /screenshot: capture desktop screen\n"
            "• /pending, /approve <id>, /deny <id>: manage security approvals",
        )

    async def open_cmd(self, update, context) -> None:
        if not await self._guard(update):
            return
        target = " ".join(context.args).strip()
        if not target:
            await self._reply_text(update, "Usage: /open <path|url|app_name>")
            return
        await self._handle_action(update, AgentAction(action="shell", command=f"open {target}", message=f"Opening {target}"))

    async def browser_cmd(self, update, context) -> None:
        if not await self._guard(update):
            return
        subcommand = " ".join(context.args).strip()
        if not subcommand:
            await self._reply_text(update, "Usage: /browser <open|search|control|tab|play|pause|click|fill|tabs|close> [args]")
            return
        await self._handle_action(update, AgentAction(action="shell", command=f"browser {subcommand}", message="Browser action."))

    async def cmd(self, update, context) -> None:
        if not await self._guard(update):
            return
        command = " ".join(context.args).strip()
        if not command:
            await self._reply_text(update, "Usage: /cmd <riftshell command>")
            return
        await self._handle_action(update, AgentAction(action="shell", command=command, message="Direct command."))

    async def screenshot(self, update, context) -> None:
        if not await self._guard(update):
            return
        await self._handle_action(update, AgentAction(action="screenshot", message="Taking screenshot."))

    async def message(self, update, context) -> None:
        if not await self._guard(update):
            return
        msg = getattr(update, "effective_message", None)
        text = (msg.text or "").strip() if msg else ""
        if not text:
            return

        import re
        words = text.split()
        first_word = words[0].lower() if words else ""

        # 1. Direct shell command matching registered command names (e.g. open, browser, note, files, etc.)
        if first_word in {name.lower() for name in self.shell.registry.all_names()}:
            await self._handle_action(
                update,
                AgentAction(action="shell", command=text, message=f"Running `{text}`"),
            )
            return

        # 2. Natural language opening (e.g. "youtube kholo", "notepad open karo", "kholo calculator")
        kholo_match = re.match(r"^(?:please\s+)?(?:kholo|chalao|open\s+karo)\s+(.+)$", text, re.I)
        if not kholo_match:
            kholo_match = re.match(r"^(.+?)\s+(?:kholo|chalao|open\s+karo|open\s+kar\s+do)$", text, re.I)
        if kholo_match:
            target = kholo_match.group(1).strip()
            await self._handle_action(
                update,
                AgentAction(action="shell", command=f"open {target}", message=f"Opening `{target}`"),
            )
            return

        # 3. Natural language media / search ("play ... on youtube", "lofi gaana chalao")
        play_match = re.match(r"^(?:please\s+)?(?:play|chalao)\s+(.+?)(?:\s+(?:on|in|par)\s+youtube)?$", text, re.I)
        if play_match:
            target = play_match.group(1).strip()
            cmd = f"browser play {target}" if target.isdigit() else f"browser search {target} --engine youtube"
            await self._handle_action(
                update,
                AgentAction(action="shell", command=cmd, message=f"Playing `{target}`"),
            )
            return

        # 4. Natural language note ("note meeting at 5pm", "write note ...")
        note_match = re.match(r"^(?:note|write\s+note|take\s+note)\s+(?:about\s+|on\s+|that\s+)?(.+)$", text, re.I)
        if note_match:
            target = note_match.group(1).strip()
            await self._handle_action(
                update,
                AgentAction(action="shell", command=f"note {target}", message=f"Creating note: {target}"),
            )
            return

        progress_task = asyncio.create_task(
            self._delayed_progress(update, "Thinking... I will run a command only if your request needs system action.")
        )
        try:
            action = await asyncio.to_thread(self.planner.plan, text)
        except Exception as exc:
            progress_task.cancel()
            await self._reply_text(update, f"I hit an internal planning error: {exc}")
            return
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        await self._handle_action(update, action)

    async def approve(self, update, context) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await self._reply_text(update, "Usage: /approve <id>")
            return

        action_id = context.args[0].strip()
        pending = self.pending.pop(action_id, None)
        if pending is None:
            await self._reply_text(update, f"No pending action found for {action_id}.")
            return
        if pending.requester_id != update.effective_user.id:
            await self._reply_text(update, "Only the requester can approve this action.")
            self.pending[action_id] = pending
            return

        await self._reply_text(update, f"Approved {action_id}. Running now...")
        await self._execute_action(update, pending.action, pending.snapshots)

    async def deny(self, update, context) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await self._reply_text(update, "Usage: /deny <id>")
            return
        action_id = context.args[0].strip()
        if self.pending.pop(action_id, None):
            await self._reply_text(update, f"Denied {action_id}.")
        else:
            await self._reply_text(update, f"No pending action found for {action_id}.")

    async def pending_list(self, update, context) -> None:
        if not await self._guard(update):
            return
        self._expire_old_pending()
        if not self.pending:
            await self._reply_text(update, "No pending approvals.")
            return

        lines = ["Pending approvals:"]
        for item in self.pending.values():
            lines.append(f"- {item.id}: {self._describe_action(item.action)} | {item.reason}")
        await self._reply_text(update, "\n".join(lines))

    async def _handle_action(self, update, action: AgentAction) -> None:
        if action.action == "respond":
            await self._reply_text(update, action.message or "I need a clearer instruction.")
            return

        decision = self.safety.check_action(action.action, action.command)
        if decision.requires_approval:
            snapshots: tuple[FileSnapshot, ...] = ()
            preview_text = ""
            if action.action == "code_write":
                preview = preview_file_writes(
                    action.files,
                    self.config.workspace_root,
                    self.config.allow_outside_workspace,
                    self.shell.ctx.cwd,
                    max_chars=max(800, min(3_000, self.config.command_output_limit - 700)),
                )
                if not preview.success:
                    await self._reply_text(
                        update,
                        "The proposed file change cannot be safely reviewed:\n\n"
                        + self._trim(preview.output)
                    )
                    return
                snapshots = preview.snapshots
                preview_text = f"\nDiff:\n{preview.output}\n"
            action_id = uuid.uuid4().hex[:8]
            self.pending[action_id] = PendingAction(
                id=action_id,
                requester_id=update.effective_user.id,
                action=action,
                reason=decision.reason,
                created_at=datetime.now(),
                snapshots=snapshots,
            )
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve:{action_id}"),
                    InlineKeyboardButton("❌ Deny", callback_data=f"deny:{action_id}"),
                ]
            ])
            await self._reply_text(
                update,
                "⚠️ Security Approval Needed\n\n"
                f"ID: {action_id}\n"
                f"Reason: {decision.reason}\n"
                f"Action: {self._describe_action(action)}\n"
                f"{preview_text}\n"
                f"Tap a button below or type /approve {action_id} or /deny {action_id}:",
                reply_markup=keyboard,
            )
            return

        await self._execute_action(update, action)

    async def button_callback(self, update, context) -> None:
        query = update.callback_query
        user_id = update.effective_user.id if update.effective_user else None
        if not self._is_allowed(user_id):
            await query.answer("Unauthorized.", show_alert=True)
            return

        data = query.data or ""
        if ":" not in data:
            await query.answer()
            return

        action_type, action_id = data.split(":", 1)
        action_id = action_id.strip()

        if action_type == "approve":
            pending = self.pending.pop(action_id, None)
            if pending is None:
                await query.answer(f"No pending action found for {action_id}.", show_alert=True)
                return
            if pending.requester_id != user_id:
                self.pending[action_id] = pending
                await query.answer("Only the requester can approve this action.", show_alert=True)
                return

            await query.answer("Approved! Running action...", show_alert=True)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await self._reply_text(update, f"Approved {action_id}. Running now...")
            await self._execute_action(update, pending.action, pending.snapshots)

        elif action_type == "deny":
            pending = self.pending.pop(action_id, None)
            if pending:
                await query.answer(f"Denied {action_id}.", show_alert=True)
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
                await self._reply_text(update, f"Denied {action_id}.")
            else:
                await query.answer(f"No pending action found for {action_id}.", show_alert=True)

    async def _execute_action(
        self,
        update,
        action: AgentAction,
        expected_snapshots: tuple[FileSnapshot, ...] | None = None,
    ) -> None:
        if action.action == "shell":
            await self._execute_shell(update, action.command)
            return
        if action.action == "browser":
            cmd = action.command.strip()
            full_cmd = cmd if cmd.startswith("browser ") else f"browser {cmd}"
            await self._execute_shell(update, full_cmd)
            return
        if action.action == "screenshot":
            await self._reply_text(update, "Taking a screenshot...")
            await self._send_screenshot(update)
            return
        if action.action == "code_write":
            await self._reply_text(
                update,
                "Code in progress... preparing files and writing them with backups where needed."
            )
            result = await asyncio.to_thread(
                apply_file_writes,
                action.files,
                self.config.workspace_root,
                self.config.allow_outside_workspace,
                self.shell.ctx.cwd,
                expected_snapshots,
            )
            await self._reply_text(update, self._trim(result.output))
            return
        await self._reply_text(update, action.message or "Done.")

    async def _execute_shell(self, update, command: str) -> None:
        await self._reply_text(update, f"Running command: {command}")
        async with self.shell_lock:
            result = await asyncio.to_thread(self.shell.execute_line, command)

        if self.on_command_completed:
            self.on_command_completed(command, result)
        text = result.output or "(no output)"
        prefix = "OK" if result.success else "FAILED"
        await self._reply_text(update, self._trim(f"{prefix}: {command}\n\n{text}"))

    async def _send_screenshot(self, update) -> None:
        try:
            path = await asyncio.to_thread(capture_screenshot)
            with path.open("rb") as image:
                await self._reply_photo(update, photo=image, caption="Screenshot")
        except Exception as exc:
            await self._reply_text(update, f"Screenshot failed: {exc}")

    async def _delayed_progress(self, update, message: str, delay: float = 1.2) -> None:
        await asyncio.sleep(delay)
        await self._reply_text(update, message)

    def _describe_action(self, action: AgentAction) -> str:
        if action.action == "shell":
            return f"shell: {action.command}"
        if action.action == "browser":
            return f"browser: {action.command}"
        if action.action == "code_write":
            paths = ", ".join(file.path for file in action.files) or "(no files)"
            return f"code_write: {paths}"
        return action.action

    def _trim(self, text: str) -> str:
        limit = max(500, self.config.command_output_limit)
        if len(text) <= limit:
            return text
        return text[: limit - 80] + "\n\n...[trimmed; output was too long]"

    def _expire_old_pending(self) -> None:
        expires_before = datetime.now() - timedelta(minutes=self.config.approval_timeout_minutes)
        expired = [key for key, item in self.pending.items() if item.created_at < expires_before]
        for key in expired:
            self.pending.pop(key, None)
