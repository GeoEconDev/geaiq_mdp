from io import StringIO
import pytest
from ruamel.yaml.composer import ComposerError
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML

first_yaml = """
- &configuracion
  texto:
  name: Nombre
"""

second_yaml = """
- caramba:
  config: *configuracion
  prueba: &prueba
  - 1
  - 2
"""

third_yaml = """
- caramba:
  config: *configuracion
  prueba: *prueba
"""


def test_persistent_anchor_across_documents():
    yaml = PersistentAnchorYAML()
    result = yaml.load(StringIO(first_yaml))
    assert result is not None

    yaml.push_anchors()
    result = yaml.load(StringIO(second_yaml))
    assert result is not None


def test_anchor_unavailable_after_pop():
    yaml = PersistentAnchorYAML()
    yaml.load(StringIO(first_yaml))
    yaml.push_anchors()
    yaml.load(StringIO(second_yaml))
    yaml.pop_anchors()

    with pytest.raises(ComposerError):
        yaml.load(StringIO(third_yaml))
