

import logging
from pathlib import Path
import pickle
import types
from time import time

CACHE_PATH = Path.home() / ".geoecon-cache"
CACHE_PATH.mkdir(exist_ok=True)
CACHE_TIME = None


def unlink_cache():
    CACHE_PATH.unlink()
    CACHE_PATH.mkdir()

def clean_cache(prefix, suffix):
    cache_file = CACHE_PATH / f"{prefix}-{suffix}"
    if cache_file.exists:
        logging.info("Clean cache: %s (%s)", cache_file, cache_file.exists())
        cache_file.unlink()
        return True
    else:
        return False

def invalidate_cache():
    global CACHE_TIME
    CACHE_TIME = time()

def cache(prefix, select=None):
    if select is None:
        select = lambda *args: "-".join(str(args))
    def __inner__(f):            
        def __func__(*args, **kwargs):
            cache_args = select(*args, **kwargs)
            cache_file = CACHE_PATH / f"{prefix}-{cache_args}"
            cache_mtime = cache_file.exists() and cache_file.stat().st_mtime

            if cache_file.exists() and cache_mtime >= (CACHE_TIME or cache_mtime):
                logging.info(
                    "♻️ Reading %s for %s from cache file %s",
                    prefix,
                    cache_args,
                    cache_file,
                )
                return pickle.load(cache_file.open("rb"))

            logging.info("☁️ Retrieving %s for %s", prefix, cache_args)
            r = f(*args, **kwargs)
            with cache_file.open("wb") as target:
                pickle.dump(r, target)
            logging.info(
                "📘 Stored %s for %s into cache file %s, (%s)", prefix, cache_args,
                cache_file, cache_file.exists()
            )

            return r

        return __func__

    return __inner__
