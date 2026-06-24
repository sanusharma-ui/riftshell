from ai.config import AIConfig
from ai.telegram_bot import TelegramAIBot


def main():
    config = AIConfig.from_env()
    TelegramAIBot(config).run()


if __name__ == "__main__":
    main()

