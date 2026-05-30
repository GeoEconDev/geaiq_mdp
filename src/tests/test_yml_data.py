from geaiq_mdp.data import load_data
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML
from ruamel.yaml import YAML

reader = PersistentAnchorYAML(typ="safe", pure=True)
data = load_data(reader)

print(data)
