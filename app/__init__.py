try:
    from .controller import Controller
except ModuleNotFoundError as exc:
    if exc.name not in {"viktor", "aps_viewer_sdk", "agents"}:
        raise
