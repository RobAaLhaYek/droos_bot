"""Telegram Bot."""

import os

from droos_bot import application
from droos_bot.modules import ALL_MODULES
from droos_bot.utils.modules_loader import load_modules


def main() -> None:
    """Run bot."""
    application.bot_data["loaded_modules"] = load_modules(
        ALL_MODULES, "droos_bot"
    )

    port = int(os.environ.get("PORT", "10000"))
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")

    if render_external_url:
        webhook_url = f"{render_external_url.rstrip('/')}/telegram"

        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="telegram",
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
    else:
        application.run_polling()


if __name__ == "__main__":
    main()