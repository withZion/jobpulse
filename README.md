# jobpulse

Heartbeat, dead-man's switch and Telegram alerts for unattended Python jobs:
cron scripts, GitHub Actions, scrapers, bots, anything that runs while you
sleep. Standard library only.

Unattended jobs fail in two annoying ways. They fail quietly, and nobody
notices until the output is missed. Or they report every run, and the
messages get muted. jobpulse sends one loud message when something starts
going wrong, a silent check-in every few hours, and lets an outside service
raise the alarm if the job stops altogether.

## Install

```
pip install git+https://github.com/withZion/jobpulse
```

## Use

```python
import os
from jobpulse import Heartbeat, Telegram, ping

tg = Telegram(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
hb = Heartbeat("state/heartbeat.json", warn_after=3)

def main():
    ...  # your job

try:
    main()
    ok, error = True, ""
except Exception as e:
    ok, error = False, repr(e)

state = hb.record_pass(ok, error)
if state["warn"]:                      # true once, when the streak reaches 3
    tg.send(hb.warning(error))
if hb.checkin_due():                   # at most one every 4 hours
    tg.send(hb.status(ok, ["42 items processed"], error), silent=True)
    hb.mark_checkin()
ping(ok, error)                        # uses JOBPULSE_PING_URL if set
```

## The three pieces

**`Telegram(token, chat_id)`** sends messages, silent messages, inline
buttons and photos. Long messages are clipped to Telegram's limit rather
than rejected. `recent_chats(token)` finds the chat id to configure: post
something in the chat, then call it.

**`Heartbeat(path)`** stores a small JSON file so counts survive restarts.

- `record_pass(ok, error)` counts the pass and returns state with
  `warn=True` exactly once when failures in a row reach `warn_after`.
- `checkin_due()` and `mark_checkin()` pace a "still here" message to one per
  `checkin_every`, however often the job runs.
- `status()` and `warning()` build short HTML messages. Pass `tz` to stamp
  them on your own clock.

**`ping(ok, detail)`** is the dead-man's switch. A job can report its own
failures but not its own death. Create a check on
[healthchecks.io](https://healthchecks.io) or any service with a ping URL,
set `JOBPULSE_PING_URL`, and it alerts you when the pings stop. Failed passes
ping `/fail` with the error as the body. A ping that fails is returned,
never raised, so monitoring can never break the job.

## Tests

```
pip install -e .[dev]
pytest
```

## License

MIT.
