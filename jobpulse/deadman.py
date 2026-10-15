"""The dead-man's switch: ping an outside service after every pass.

A job can report its own failures, but not its own death. If the process is
gone, the machine is off or the network is down, there is nothing left to
send a warning. So an outside service (healthchecks.io, Cronitor, Uptime
Kuma or anything with a ping URL) expects a ping after every pass, and
raises the alarm itself when the pings stop.

A pass with problems pings `<url>/fail` with the error as the body, which
healthchecks.io treats as a failure and displays.

A ping that fails is returned, never raised: the switch must never be the
thing that breaks the job.
"""
from __future__ import annotations

import os
import urllib.request

TIMEOUT = 10
ENV_VAR = "JOBPULSE_PING_URL"


def ping(ok: bool = True, detail: str = "", url: str | None = None) -> str | None:
    """Ping the check. `url` defaults to the JOBPULSE_PING_URL env var.

    Returns an error message, or None if it worked or no URL is configured.
    """
    base = url or os.environ.get(ENV_VAR)
    if not base:
        return None
    target = base.rstrip("/") + ("" if ok else "/fail")
    body = (detail or "").encode("utf-8")[-10_000:] or None
    try:
        req = urllib.request.Request(target, data=body, method="POST" if body else "GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT):
            return None
    except Exception as e:  # never let the switch break anything
        return str(e)
