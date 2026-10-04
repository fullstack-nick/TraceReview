from functools import lru_cache
from importlib.metadata import version
import platform
import subprocess
from django.conf import settings


@lru_cache(maxsize=1)
def build_metadata():
    commit, dirty = None, True
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=settings.BASE_DIR, timeout=5, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=settings.BASE_DIR, timeout=5, stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {"application_version": "0.1.0", "git_commit": commit, "working_tree_dirty": dirty,
            "runtime_versions": {"python": platform.python_version(), **{name: version(name) for name in ["Django", "djangorestframework", "numpy"]}}}
