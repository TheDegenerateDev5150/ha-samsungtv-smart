"""Upload sidecar: skip-unchanged bookkeeping for batch uploads."""
import json
import os


def test_list_images_sorted_and_filtered(tmp_path):
    from custom_components.samsungtv_smart.api import _upload_sidecar as sc

    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "a.PNG").write_bytes(b"x")
    (tmp_path / "note.txt").write_text("nope")
    (tmp_path / "sub").mkdir()  # directories excluded
    result = [os.path.basename(p) for p in sc.list_images(str(tmp_path))]
    assert result == ["a.PNG", "b.jpg"]


def test_needs_upload_new_and_changed():
    from custom_components.samsungtv_smart.api import _upload_sidecar as sc

    sidecar = {"a.jpg": {"content_id": "MY-F0001", "modified": 100.0}}
    assert sc.needs_upload("new.jpg", 1.0, sidecar) is True  # never seen
    assert sc.needs_upload("a.jpg", 100.0, sidecar) is False  # unchanged -> skip
    assert sc.needs_upload("a.jpg", 200.0, sidecar) is True  # mtime changed


def test_sidecar_roundtrip_and_bad_file(tmp_path):
    from custom_components.samsungtv_smart.api import _upload_sidecar as sc

    path = str(tmp_path / ".samsungtv_upload.json")
    assert sc.load_sidecar(path) == {}  # missing -> {}
    data = {"a.jpg": {"content_id": "MY-F0001", "modified": 100.0}}
    sc.save_sidecar(path, data)
    assert sc.load_sidecar(path) == data
    assert json.loads((tmp_path / ".samsungtv_upload.json").read_text()) == data

    (tmp_path / "corrupt.json").write_text("{not json")
    assert sc.load_sidecar(str(tmp_path / "corrupt.json")) == {}  # unreadable -> {}
