from geaiq_mdp.data import load_data
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML


def test_load_data_missing_dir(tmp_path):
    reader = PersistentAnchorYAML(typ="safe", pure=True)
    data = load_data(root=tmp_path, reader=reader)
    assert data == []


def test_load_data_empty_data_dir(tmp_path):
    (tmp_path / "data").mkdir()
    reader = PersistentAnchorYAML(typ="safe", pure=True)
    data = load_data(root=tmp_path, reader=reader)
    assert data == []
