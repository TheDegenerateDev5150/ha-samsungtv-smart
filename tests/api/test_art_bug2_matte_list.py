"""Bug 2: field matte_type_list was renamed matte_list on some firmware."""
import json


async def test_matte_list_new_field_name(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"matte_list": json.dumps(["none", "shadowbox_polar", "modernthin_black"])}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    result = await art_client.get_matte_list()
    assert result == ["none", "shadowbox_polar", "modernthin_black"]


async def test_matte_list_old_field_name(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"matte_type_list": json.dumps(["none", "flexible_polar"])}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    result = await art_client.get_matte_list()
    assert result == ["none", "flexible_polar"]
