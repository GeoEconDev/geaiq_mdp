from importlib.metadata import version, PackageNotFoundError

try:
    _VERSION = version("geaiq_mdp")
except PackageNotFoundError:
    _VERSION = "0.0.0+unknown"


def get_version_string():
    return _VERSION
