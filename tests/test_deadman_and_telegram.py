from jobpulse import ping
from jobpulse.telegram import MAX_TEXT, clip


def test_no_url_means_no_ping(monkeypatch):
    monkeypatch.delenv("JOBPULSE_PING_URL", raising=False)
    assert ping(True) is None


def test_unreachable_service_is_reported_not_raised():
    assert ping(False, "boom", url="http://127.0.0.1:9/nope") is not None


def test_long_messages_are_clipped_to_the_limit():
    assert clip("x" * 10) == "x" * 10
    out = clip("x" * (MAX_TEXT + 50))
    assert len(out) == MAX_TEXT and out.endswith("...")
