"""jobpulse: heartbeat, dead-man's switch and Telegram alerts for unattended jobs.

Three small pieces that work alone or together:

- `Telegram`: send messages and photos from a bot. Stdlib only.
- `Heartbeat`: count passes, warn once when a failure streak starts, and pace
  silent check-ins.
- `deadman.ping`: tell an outside service you are alive, so it can raise the
  alarm when you are not.
"""
from .deadman import ping
from .heartbeat import Heartbeat
from .telegram import Telegram, TelegramError, recent_chats

__all__ = ["Telegram", "TelegramError", "recent_chats", "Heartbeat", "ping"]
__version__ = "0.1.0"
