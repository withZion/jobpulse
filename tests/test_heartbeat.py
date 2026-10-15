from datetime import datetime, timedelta, timezone

from jobpulse import Heartbeat


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


def make(tmp_path, **kw):
    clock = Clock()
    return Heartbeat(tmp_path / "hb.json", now=clock, **kw), clock


def test_passes_are_counted(tmp_path):
    hb, _ = make(tmp_path)
    hb.record_pass(True)
    state = hb.record_pass(False, "boom")
    assert state["passes"] == 2
    assert state["failures"] == 1
    assert state["last_error"] == "boom"


def test_warning_fires_once_when_the_streak_reaches_the_limit(tmp_path):
    hb, _ = make(tmp_path, warn_after=3)
    assert [hb.record_pass(False)["warn"] for _ in range(5)] == [False, False, True, False, False]
    hb.record_pass(True)  # a good pass resets the streak
    assert [hb.record_pass(False)["warn"] for _ in range(3)] == [False, False, True]


def test_counters_reset_on_a_new_day(tmp_path):
    hb, clock = make(tmp_path)
    hb.record_pass(False)
    clock.advance(days=1)
    state = hb.record_pass(True)
    assert state["passes"] == 1 and state["failures"] == 0


def test_check_ins_are_paced(tmp_path):
    hb, clock = make(tmp_path, checkin_every=timedelta(hours=4))
    assert hb.checkin_due()
    hb.mark_checkin()
    assert not hb.checkin_due()
    clock.advance(hours=4)
    assert hb.checkin_due()


def test_status_and_warning_text(tmp_path):
    hb, _ = make(tmp_path)
    hb.record_pass(True)
    assert "ok" in hb.status(True, ["5 items checked"])
    bad = hb.status(False, error="timeout talking to upstream")
    assert "problems" in bad and "timeout talking to upstream" in bad
    assert "passes in a row" in hb.warning("disk full")


def test_state_survives_a_new_instance(tmp_path):
    hb, clock = make(tmp_path)
    hb.record_pass(True)
    again = Heartbeat(tmp_path / "hb.json", now=clock)
    assert again.record_pass(True)["passes"] == 2
