from geoecon_metadata.data import load_data
from geoecon_metadata.persistent_anchor_yaml import PersistentAnchorYAML
from ruamel.yaml import YAML

reader = PersistentAnchorYAML(typ="safe", pure=True)
data = load_data(reader)

print(data)
