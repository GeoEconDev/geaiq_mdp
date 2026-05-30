import logging
from pathlib import Path
from .readers import read_data
from .persistent_anchor_yaml import PersistentAnchorYAML


def load_data(root=None, reader=None, ignore=None):
    root = root or Path("./")
    data_path = root / "data"
    if not data_path.exists():
        logging.error("Data directory not found: %s", data_path)
        return []
    data_files = (fn for fn in sorted(data_path.iterdir()) if ignore is None or fn.name not in ignore)
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    data = []
    for data_file in data_files:
        logging.info("Reading datafile %s", data_file)
        data.extend(read_data(Path(data_file), reader=reader))
    return data
