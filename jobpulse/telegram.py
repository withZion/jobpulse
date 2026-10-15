"""A Telegram bot client with no dependencies.

One HTTPS call per method, so there is no reason to pull in a library.
Wording lives with the caller; this module only delivers.
"""
from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 20
MAX_TEXT = 4096  # Telegram's limit per message


class TelegramError(RuntimeError):
    pass


def _call(token: str, method: str, **params) -> dict:
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=TIMEOUT) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise TelegramError(f"{method} failed: HTTP {e.code} {detail}") from None
    except urllib.error.URLError as e:
        raise TelegramError(f"{method} failed: {e.reason}") from None
    if not body.get("ok"):
        raise TelegramError(f"{method} failed: {body}")
    return body["result"]


def clip(text: str, limit: int = MAX_TEXT) -> str:
    """Trim to Telegram's limit with an ellipsis rather than let the API reject it."""
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass
class Telegram:
    token: str
    chat_id: str | int

    def me(self) -> dict:
        """The bot's own account. The cheapest way to check a token works."""
        return _call(self.token, "getMe")

    def send(self, text: str, parse_mode: str | None = "HTML", silent: bool = False,
             buttons: list[list[dict]] | None = None) -> dict:
        """Send a message.

        `silent` delivers without a sound: right for status messages that
        should be there when looked for but never interrupt. `buttons` are
        rows of inline buttons, e.g. [[{"text": "Open", "url": "https://..."}]].
        """
        return _call(
            self.token, "sendMessage", chat_id=self.chat_id, text=clip(text),
            parse_mode=parse_mode, disable_web_page_preview="true",
            disable_notification="true" if silent else None,
            reply_markup=json.dumps({"inline_keyboard": buttons}) if buttons else None,
        )

    def send_photo(self, path: str | Path, caption: str | None = None,
                   parse_mode: str | None = "HTML") -> dict:
        """Upload an image with an optional caption. Multipart, still stdlib only."""
        path = Path(path)
        photo = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        boundary = "----jobpulse-" + str(abs(hash(path.name)))
        parts: list[bytes] = []
        for key, value in (("chat_id", str(self.chat_id)), ("caption", caption),
                           ("parse_mode", parse_mode if caption else None)):
            if value is None:
                continue
            parts += [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                value.encode() + b"\r\n",
            ]
        parts += [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="photo"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            photo,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        req = urllib.request.Request(
            API.format(token=self.token, method="sendPhoto"),
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                result = json.load(r)
        except urllib.error.HTTPError as e:
            raise TelegramError(f"sendPhoto failed: HTTP {e.code} "
                                f"{e.read().decode(errors='replace')}") from None
        except urllib.error.URLError as e:
            raise TelegramError(f"sendPhoto failed: {e.reason}") from None
        if not result.get("ok"):
            raise TelegramError(f"sendPhoto failed: {result}")
        return result["result"]


def recent_chats(token: str) -> list[dict]:
    """Chats the bot has recently seen, from getUpdates.

    Telegram will not tell a bot which chats exist. It only learns a chat id
    once something happens there. Post anything in the group or channel, then
    call this to find the id to configure.
    """
    seen: dict[int, dict] = {}
    for update in _call(token, "getUpdates"):
        for key in ("message", "channel_post", "my_chat_member", "edited_channel_post"):
            chat = (update.get(key) or {}).get("chat")
            if chat:
                seen[chat["id"]] = chat
    return list(seen.values())
