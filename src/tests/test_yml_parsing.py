from ruamel.yaml import YAML
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML
from geaiq_mdp.models import ObservableScale, ObservableGroup

yml_a = """
- !ObservableScale &aOSA
  name: A
  description: B
- !ObservableGroup &aOSB
  name: B
  description: C
"""

yml_b = """
- !ObservableScale &bOSA
  name: A
  description: BB
- !ObservableGroup &bOSB
  name: B
  description: BC
- *aOSA
"""


def _make_reader():
    reader = PersistentAnchorYAML(typ="safe", pure=True)
    reader.register_class(ObservableScale)
    reader.register_class(ObservableGroup)
    return reader


def test_read_yml_returns_correct_types():
    reader = _make_reader()
    result = reader.load(yml_a)
    assert len(result) == 2
    assert isinstance(result[0], ObservableScale)
    assert isinstance(result[1], ObservableGroup)


def test_read_yml_with_cross_document_anchor():
    reader = _make_reader()
    reader.load(yml_a)
    reader.push_anchors()
    result = reader.load(yml_b)
    assert len(result) == 3
    assert isinstance(result[2], ObservableScale)
    assert result[2].name == "A"
    assert result[2].description == "B"
