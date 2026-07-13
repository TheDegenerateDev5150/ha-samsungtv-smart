"""Bug 3: API 5.x uses 'status' instead of 'value' for art-mode state."""


async def test_get_artmode_value_field(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"value": "on"}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "on"
    assert art_client.art_mode is True


async def test_get_artmode_status_field(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"status": "on"}  # API 5.x shape, no 'value' key

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "on"
    assert art_client.art_mode is True


async def test_get_artmode_defaults_off(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "off"
    assert art_client.art_mode is False
