"""Circuit breaker: consecutive request timeouts must force a reconnect.

Covers the zombie-channel case from issue #153: the TV's art APP dies while
its network stack keeps the WebSocket open and answering PINGs, so the
heartbeat never fires, the receive loop never exits, and every request just
times out until the integration is reloaded.
"""

import asyncio


class _FakeWS:
    """Minimal live-looking WebSocket that records close() calls."""

    def __init__(self):
        self.closed = False
        self.close_calls = 0

    async def close(self):
        self.closed = True
        self.close_calls += 1


async def _timeout_once(art_client):
    """Run one request that times out immediately (nobody resolves the future)."""
    await art_client._wait_for_response("k", timeout=0)


async def test_breaker_trips_after_consecutive_timeouts(art_client):
    import art

    ws = _FakeWS()
    art_client._ws = ws
    art_client._connected = True

    for _ in range(art.ART_WS_TIMEOUT_TRIP):
        await _timeout_once(art_client)
    # The force-close runs in a task — let it execute.
    await asyncio.sleep(0)

    assert ws.close_calls == 1
    assert art_client._timeout_streak == 0  # reset after tripping


async def test_success_resets_streak(art_client):
    import art

    ws = _FakeWS()
    art_client._ws = ws
    art_client._connected = True

    # Two timeouts (one below the trip threshold)...
    for _ in range(art.ART_WS_TIMEOUT_TRIP - 1):
        await _timeout_once(art_client)
    assert art_client._timeout_streak == art.ART_WS_TIMEOUT_TRIP - 1

    # ...then a real answer arrives: the streak must reset.
    fut = asyncio.get_event_loop().create_future()
    art_client._pending_requests["ok"] = fut
    fut.set_result({"event": "ok"})
    assert await art_client._wait_for_response("ok", timeout=1) == {"event": "ok"}
    assert art_client._timeout_streak == 0

    # A later single timeout starts again from 1 — no trip, no close.
    await _timeout_once(art_client)
    await asyncio.sleep(0)
    assert ws.close_calls == 0


async def test_no_trip_when_already_disconnected(art_client):
    import art

    art_client._ws = None
    art_client._connected = False

    for _ in range(art.ART_WS_TIMEOUT_TRIP + 1):
        await _timeout_once(art_client)
    await asyncio.sleep(0)

    # Nothing to close, no crash; the streak reset at the threshold (the
    # timeout right after it legitimately starts a fresh count at 1).
    assert art_client._timeout_streak < art.ART_WS_TIMEOUT_TRIP
