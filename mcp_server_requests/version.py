try:
    from importlib import metadata

    __version__ = metadata.version(__package__)
except Exception:
    __version__ = "unknown"
