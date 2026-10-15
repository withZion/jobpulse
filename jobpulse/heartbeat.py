"""Know when an unattended job is in trouble, without being nagged when it isn't.

Two problems with scheduled jobs:

1. A job that fails quietly. Nobody notices until the output is missed.
2. A job that reports every run. The messages become noise and get muted.

`Heartbeat` answers both. Every pass is recorded in a small JSON file, so
counts survive restarts. When a failure streak reaches `warn_after`, the
returned state carries `warn=True` exactly once, so one loud message goes
out. Separately, `checkin_due()` paces a silent "still here" message to at
most one per `checkin_every`, whatever the job's own schedule.

What this cannot report is the job being dead. For that, pair it with
`jobpulse.deadman`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


class Heartbeat:
    def __init__(self, path: str | Path, warn_after: int = 3,
                 checkin_every: timedelta = timedelta(hours=4),
                 tz: timezone = timezone.utc,
                 now: Callable[[], datetime] | None = None):
        self.path = Path(path)
        self.warn_after = warn_after
        self.checkin_every = checkin_every
        self.tz = tz
        self._now = now or (lambda: datetime.now(timezone.utc))

    # -- state ---------------------------------------------------------------

    def load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def now(self) -> datetime:
        """Now, on the reader's clock."""
        return self._now().astimezone(self.tz)

    # -- passes --------------------------------------------------------------

    def record_pass(self, ok: bool, error: str = "") -> dict:
        """Count one pass. Counters reset each day on the reader's clock.

        The returned state has `warn` set when the failure streak has just
        reached `warn_after`, so a warning goes out once, not every run.
        """
        now = self.now()
        today = now.strftime("%Y-%m-%d")
        state = self.load()
        if state.get("day") != today:
            state.update(day=today, passes=0, failures=0)
        state["passes"] = state.get("passes", 0) + 1
        state["last_pass"] = now.isoformat(timespec="seconds")
        if ok:
            state["failures_in_a_row"] = 0
            state.pop("last_error", None)
        else:
            state["failures"] = state.get("failures", 0) + 1
            state["failures_in_a_row"] = state.get("failures_in_a_row", 0) + 1
            state["last_error"] = (error or "").strip()[-500:]
        state["warn"] = state.get("failures_in_a_row", 0) == self.warn_after
        self.save(state)
        return state

    # -- check-ins -----------------------------------------------------------

    def checkin_due(self) -> bool:
        """True when no check-in has gone out in the last `checkin_every`."""
        last = self.load().get("last_checkin")
        if not last:
            return True
        return self._now() - datetime.fromisoformat(last) >= self.checkin_every

    def mark_checkin(self) -> None:
        state = self.load()
        state["last_checkin"] = self._now().isoformat(timespec="seconds")
        self.save(state)

    # -- messages ------------------------------------------------------------

    def status(self, ok: bool, lines: list[str] | None = None, error: str = "",
               title: str = "Run") -> str:
        """A short HTML status, stamped on the reader's clock. Send it silently."""
        state = self.load()
        now = self.now()
        failed = state.get("failures", 0)
        head = f"✅ {title} ok" if ok else f"⚠ {title} ran with problems"
        out = [f"<b>{head}</b> · {now:%H:%M}, {now:%a %d %b}"]
        out += list(lines or [])
        out.append(f"Passes today: {state.get('passes', 0)}" + (f", {failed} failed" if failed else ""))
        if not ok and error:
            out.append(f"<code>{error.strip()[-200:]}</code>")
        return "\n".join(out)

    def warning(self, error: str = "", title: str = "Job") -> str:
        """The loud message for when the streak reaches `warn_after`."""
        tail = (error or self.load().get("last_error") or "no detail").strip()[-300:]
        return "\n".join([
            f"<b>⚠ {title} problem</b>",
            f"{self.warn_after} passes in a row have failed.",
            "",
            f"<code>{tail}</code>",
        ])
