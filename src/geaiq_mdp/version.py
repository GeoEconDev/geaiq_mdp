VERSION = {"major": 0, "minor": 1, "micro": 0, "releaselevel": "alpha", "serial": 9}


def get_version_string():
    """Prints the version of the geaiq_mdp package."""
    major = VERSION["major"]
    minor = VERSION["minor"]
    micro = VERSION["micro"]
    releaselevel = VERSION["releaselevel"]
    serial = VERSION["serial"]

    version_string = f"{major}.{minor}.{micro}"
    if releaselevel != "final":
        version_string += f"{releaselevel[0]}{serial}"

    return version_string
