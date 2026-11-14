"""Desktop lifecycle for the optional Telegram control channel."""

from __future__ import annotations

import threading
from collections.abc import Callable

from ai.config import AIConfig
from ai.telegram_bot import TelegramAIBot


class TelegramControlService:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._bot: TelegramAIBot | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        config: AIConfig,
        on_error: Callable[[Exception], None] | None = None,
        on_command_completed: Callable[[str, object], None] | None = None,
    ) -> None:
        problems = config.validate_for_telegram()
        if problems:
            raise ValueError("; ".join(problems))

        with self._lock:
            if self.running:
                old_bot = self._bot
                self._bot = None
                self._thread = None
                if old_bot is not None:
                    old_bot.stop()
            bot = TelegramAIBot(config, on_command_completed=on_command_completed)
            thread = threading.Thread(
                target=self._run,
                args=(bot, on_error),
                name="riftshell-telegram",
                daemon=True,
            )
            self._bot = bot
            self._thread = thread
            thread.start()

    def _run(self, bot: TelegramAIBot, on_error: Callable[[Exception], None] | None) -> None:
        try:
            bot.run()
        except Exception as exc:
            if on_error:
                on_error(exc)

    def stop(self) -> None:
        with self._lock:
            bot, thread = self._bot, self._thread
            self._bot = None
            self._thread = None
        if bot is not None:
            bot.stop()
        if thread and thread.is_alive():
            thread.join(timeout=3)
